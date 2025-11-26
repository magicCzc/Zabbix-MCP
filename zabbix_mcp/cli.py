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
import time
from typing import Optional, List

import typer
from rich.console import Console
from rich.table import Table

from .config import load_settings
from .zabbix_client import ZabbixClient
from .schemas import AlertQuery, LogAssociationQuery, TimeRange
from .services import query_alerts, today_alerts, associate_logs
from .nlp import parse_alert_query


app = typer.Typer(help="Zabbix MCP CLI")
console = Console()


def _client() -> ZabbixClient:
    try:
        s = load_settings()
    except Exception as e:
        console.print({"i18n_key": "error.config_missing", "message": str(e)})
        raise SystemExit(1)
    if s.mock_mode:
        from .zabbix_client import MockZabbixClient
        return MockZabbixClient()  # type: ignore[return-value]
    return ZabbixClient(
        base_url=str(s.zabbix_url),
        username=s.zabbix_username,
        password=s.zabbix_password.get_secret_value(),
        timeout=s.request_timeout_seconds,
        max_concurrency=s.max_concurrency,
    )


def _print_table(items):
    table = Table(title="alerts.table.title")
    table.add_column("alerts.col.id")
    table.add_column("alerts.col.name")
    table.add_column("alerts.col.host")
    table.add_column("alerts.col.ip")
    table.add_column("alerts.col.severity")
    table.add_column("alerts.col.time")
    for it in items:
        table.add_row(
            it.id,
            it.name,
            it.host,
            it.host_ip or "",
            str(it.severity),
            time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(it.timestamp)),
        )
    console.print(table)


@app.command()
def today(limit: int = 100, json_output: bool = False):
    cli = _client()
    async def run():
        await cli.login()
        res = await today_alerts(cli, limit=limit)
        await cli.logout()
        return res
    res = asyncio.run(run())
    if json_output:
        console.print(res.model_dump())
    else:
        _print_table(res.items)


@app.command()
def top(by: str = "severity", limit: int = 100, json_output: bool = False):
    cli = _client()
    async def run():
        await cli.login()
        res = await query_alerts(cli, AlertQuery(limit=limit, sort_by=by))
        await cli.logout()
        return res
    res = asyncio.run(run())
    if json_output:
        console.print(res.model_dump())
    else:
        _print_table(res.items)


@app.command()
def query(
    start_ts: Optional[int] = None,
    end_ts: Optional[int] = None,
    group: Optional[List[str]] = typer.Option(None),
    host: Optional[List[str]] = typer.Option(None),
    severity: Optional[List[int]] = typer.Option(None),
    limit: int = 100,
    json_output: bool = False,
):
    cli = _client()
    tr = None
    if start_ts or end_ts:
        tr = TimeRange(start_ts=start_ts or 0, end_ts=end_ts or int(time.time()))
    q = AlertQuery(
        time_range=tr,
        host_groups=group,
        hosts=host,
        severities=severity,
        limit=limit,
    )
    async def run():
        await cli.login()
        res = await query_alerts(cli, q)
        await cli.logout()
        return res
    res = asyncio.run(run())
    if json_output:
        console.print(res.model_dump())
    else:
        _print_table(res.items)


@app.command()
def associate(
    keywords: List[str],
    start_ts: Optional[int] = None,
    end_ts: Optional[int] = None,
    group: Optional[List[str]] = typer.Option(None),
    host: Optional[List[str]] = typer.Option(None),
    limit: int = 100,
    json_output: bool = False,
):
    cli = _client()
    tr = None
    if start_ts or end_ts:
        tr = TimeRange(start_ts=start_ts or 0, end_ts=end_ts or int(time.time()))
    q = LogAssociationQuery(
        keywords=keywords,
        time_range=tr,
        host_groups=group,
        hosts=host,
        limit=limit,
    )
    async def run():
        await cli.login()
        res, _ = await associate_logs(cli, q)
        await cli.logout()
        return res
    res = asyncio.run(run())
    if json_output:
        console.print(res.model_dump())
    else:
        _print_table(res.items)


@app.command()
def nl(text: str, json_output: bool = False):
    cli = _client()
    async def run():
        await cli.login()
        q = parse_alert_query(text)
        res = await query_alerts(cli, q)
        await cli.logout()
        return res
    res = asyncio.run(run())
    if json_output:
        console.print(res.model_dump())
    else:
        _print_table(res.items)
