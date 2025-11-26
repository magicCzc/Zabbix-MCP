"""
Copyright (c) 2025 Zabbix-MCP

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import asyncio
from fastapi import FastAPI, HTTPException, Depends, WebSocket, Request
from fastapi.responses import JSONResponse, Response

from .config import load_settings
from .schemas import AlertQuery, LogAssociationQuery, AlertResponse, ErrorResponse, NLQuery
from .zabbix_client import ZabbixClient, ZabbixAPIError, MockZabbixClient
from .services import query_alerts, today_alerts, associate_logs
from .nlp import parse_alert_query
from .logging import setup as setup_logging
from .metrics import REQUEST_COUNT, REQUEST_LATENCY
from .auth import require_role
from .queue import TaskQueue
from .ws import ClientRegistry


setup_logging()
app = FastAPI(title="Zabbix MCP", version="0.1.0")
client_registry = ClientRegistry()
task_queue = TaskQueue(workers=4)
settings_cache = None


async def get_client():
    try:
        global settings_cache
        s = settings_cache or load_settings()
        settings_cache = s
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=ErrorResponse(i18n_key="error.config_missing", message=str(e)).model_dump(),
        )
    if s.mock_mode:
        cli = MockZabbixClient()
    else:
        cli = ZabbixClient(
            base_url=str(s.zabbix_url),
            username=s.zabbix_username,
            password=s.zabbix_password.get_secret_value() if s.zabbix_password else None,
            timeout=s.request_timeout_seconds,
            max_concurrency=s.max_concurrency,
            verify_ssl=s.verify_ssl,
            token=s.zabbix_token.get_secret_value() if s.zabbix_token else None,
        )
    await cli.login()
    return cli


@app.on_event("startup")
async def startup_events():
    async def handler(job: dict):
        # minimal demo: run alerts.query jobs
        kind = job.get("type")
        if kind == "alerts.query":
            payload = job.get("payload") or {}
            cli = await get_client()
            try:
                await query_alerts(cli, AlertQuery.model_validate(payload))
            finally:
                await cli.logout()
    await task_queue.start(handler)


@app.middleware("http")
async def audit_middleware(request: Request, call_next):
    start = asyncio.get_event_loop().time()
    path = request.url.path
    method = request.method
    role = None
    try:
        auth = request.headers.get("Authorization")
        token = auth.split(" ")[-1] if auth else None
        import os
        admin = os.getenv("MCP_AUTH_TOKEN_ADMIN")
        read = os.getenv("MCP_AUTH_TOKEN_READ")
        if token and admin and token == admin:
            role = "admin"
        elif token and read and token == read:
            role = "read"
        s = settings_cache or load_settings()
        if s.read_only and method in {"POST", "PUT", "DELETE", "PATCH"}:
            allowed = {"/alerts/query", "/alerts/nl", "/logs/associate"}
            if path not in allowed:
                return JSONResponse(
                    status_code=403,
                    content=ErrorResponse(i18n_key="error.read_only", message="read-only mode").model_dump(),
                )
        resp = await call_next(request)
        dur = (asyncio.get_event_loop().time() - start) * 1000
        import logging
        logging.getLogger("audit").info(
            f"route={path} method={method} role={role} status={resp.status_code} dur_ms={int(dur)}"
        )
        return resp
    except Exception:
        return await call_next(request)


@app.post("/alerts/query", response_model=AlertResponse)
async def api_alerts_query(payload: AlertQuery, role: str = Depends(require_role("read"))):
    cli = await get_client()
    try:
        with REQUEST_LATENCY.labels("alerts_query").time():
            REQUEST_COUNT.labels("alerts_query").inc()
            s = settings_cache or load_settings()
            eff_limit = min(max(1, payload.limit), s.max_results_limit)
            payload = AlertQuery(
                time_range=payload.time_range,
                host_groups=payload.host_groups,
                hosts=payload.hosts,
                severities=payload.severities,
                limit=eff_limit,
                sort_by=payload.sort_by,
            )
            resp = await query_alerts(cli, payload)
        return JSONResponse(resp.model_dump())
    except ZabbixAPIError as e:
        raise HTTPException(
            status_code=502,
            detail=ErrorResponse(
                i18n_key="error.zabbix_api",
                message=str(e),
            ).model_dump(),
        )
    finally:
        await cli.logout()


@app.get("/alerts/today", response_model=AlertResponse)
async def api_alerts_today(limit: int = 100, role: str = Depends(require_role("read"))):
    cli = await get_client()
    try:
        with REQUEST_LATENCY.labels("alerts_today").time():
            REQUEST_COUNT.labels("alerts_today").inc()
            s = settings_cache or load_settings()
            eff_limit = min(max(1, limit), s.max_results_limit)
            resp = await today_alerts(cli, limit=eff_limit)
        return JSONResponse(resp.model_dump())
    except ZabbixAPIError as e:
        raise HTTPException(
            status_code=502,
            detail=ErrorResponse(
                i18n_key="error.zabbix_api",
                message=str(e),
            ).model_dump(),
        )
    finally:
        await cli.logout()


@app.get("/alerts/top", response_model=AlertResponse)
async def api_alerts_top(by: str = "severity", limit: int = 100, role: str = Depends(require_role("read"))):
    cli = await get_client()
    try:
        REQUEST_COUNT.labels("alerts_top").inc()
        s = settings_cache or load_settings()
        eff_limit = min(max(1, limit), s.max_results_limit)
        resp = await query_alerts(
            cli,
            AlertQuery(limit=eff_limit, sort_by=by if by in {"severity", "frequency", "time"} else "severity"),
        )
        return JSONResponse(resp.model_dump())
    except ZabbixAPIError as e:
        raise HTTPException(
            status_code=502,
            detail=ErrorResponse(
                i18n_key="error.zabbix_api",
                message=str(e),
            ).model_dump(),
        )
    finally:
        await cli.logout()


@app.post("/logs/associate", response_model=AlertResponse)
async def api_logs_associate(payload: LogAssociationQuery, role: str = Depends(require_role("read"))):
    cli = await get_client()
    try:
        with REQUEST_LATENCY.labels("logs_associate").time():
            REQUEST_COUNT.labels("logs_associate").inc()
            s = settings_cache or load_settings()
            eff_limit = min(max(1, payload.limit), s.max_results_limit)
            payload = LogAssociationQuery(
                keywords=payload.keywords,
                time_range=payload.time_range,
                host_groups=payload.host_groups,
                hosts=payload.hosts,
                limit=eff_limit,
            )
            resp, _ = await associate_logs(cli, payload)
        return JSONResponse(resp.model_dump())
    except ZabbixAPIError as e:
        raise HTTPException(
            status_code=502,
            detail=ErrorResponse(
                i18n_key="error.zabbix_api",
                message=str(e),
            ).model_dump(),
        )
    finally:
        await cli.logout()


@app.post("/alerts/nl", response_model=AlertResponse)
async def api_alerts_nl(payload: NLQuery, role: str = Depends(require_role("read"))):
    cli = await get_client()
    try:
        REQUEST_COUNT.labels("alerts_nl").inc()
        q = parse_alert_query(payload.text)
        resp = await query_alerts(cli, q)
        return JSONResponse(resp.model_dump())
    except ZabbixAPIError as e:
        raise HTTPException(
            status_code=502,
            detail=ErrorResponse(
                i18n_key="error.zabbix_api",
                message=str(e),
            ).model_dump(),
        )
    finally:
        await cli.logout()


@app.get("/health")
async def health():
    try:
        s = load_settings()
        return {"status": "ok", "mock_mode": s.mock_mode}
    except Exception:
        return {"status": "config_missing"}


@app.get("/version")
async def version(role: str = Depends(require_role("read"))):
    cli = await get_client()
    try:
        v = await cli.api_version()
        return {"zabbix_api_version": v}
    finally:
        await cli.logout()
@app.get("/metrics")
async def metrics():
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
    data = generate_latest()  
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)


@app.websocket("/mcp/ws")
async def mcp_ws(ws: WebSocket):
    await client_registry.connect(ws)
    try:
        while True:
            msg = await ws.receive_text()
            await ws.send_text("ok:" + msg)
    except Exception:
        await client_registry.disconnect(ws)


@app.post("/queue/enqueue")
async def enqueue(job: dict, role: str = Depends(require_role("admin"))):
    s = settings_cache or load_settings()
    if s.read_only:
        raise HTTPException(status_code=403, detail=ErrorResponse(i18n_key="error.read_only", message="read-only mode").model_dump())
    await task_queue.enqueue(job)
    return {"status": "queued"}


@app.get("/queue/stats")
async def queue_stats(role: str = Depends(require_role("admin"))):
    s = settings_cache or load_settings()
    if s.read_only:
        raise HTTPException(status_code=403, detail=ErrorResponse(i18n_key="error.read_only", message="read-only mode").model_dump())
    return {"size": task_queue.queue.qsize(), "workers": task_queue.workers}


@app.post("/config/reload")
async def config_reload(role: str = Depends(require_role("admin"))):
    global settings_cache
    s = settings_cache or load_settings()
    if s.read_only:
        raise HTTPException(status_code=403, detail=ErrorResponse(i18n_key="error.read_only", message="read-only mode").model_dump())
    settings_cache = load_settings()
    return {"status": "reloaded"}
