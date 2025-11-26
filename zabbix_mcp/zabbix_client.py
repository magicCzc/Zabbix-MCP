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
from typing import Any, Dict, List, Optional

import httpx


class ZabbixAPIError(Exception):
    pass


class ZabbixClient:
    def __init__(
        self,
        base_url: str,
        username: Optional[str],
        password: Optional[str],
        timeout: int = 30,
        max_concurrency: int = 8,
        verify_ssl: bool = True,
        token: Optional[str] = None,
    ) -> None:
        self.base_url = base_url.rstrip("/") + "/api_jsonrpc.php"
        self.username = username
        self.password = password
        self.timeout = timeout
        self._token: Optional[str] = None
        self._client = httpx.AsyncClient(timeout=timeout, verify=verify_ssl)
        self._sem = asyncio.Semaphore(max_concurrency)
        if token:
            self._token = token

    async def _rpc(self, method: str, params: Dict[str, Any]) -> Any:
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": 1,
            "auth": self._token,
        }
        async with self._sem:
            resp = await self._client.post(self.base_url, json=payload)
        if resp.status_code != 200:
            raise ZabbixAPIError(f"HTTP {resp.status_code}")
        data = resp.json()
        if "error" in data:
            err = data["error"]
            raise ZabbixAPIError(f"{err.get('message')}: {err.get('data')}")
        return data.get("result")

    async def login(self) -> None:
        if self._token:
            return
        result = await self._rpc(
            "user.login", {"user": self.username, "password": self.password}
        )
        self._token = result

    async def logout(self) -> None:
        if self._token and self.username and self.password:
            await self._rpc("user.logout", {})
        await self._client.aclose()

    async def get_hostgroups(self, names: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {"output": ["name", "groupid"]}
        if names:
            params["filter"] = {"name": names}
        return await self._rpc("hostgroup.get", params)

    async def get_hosts(
        self, groups: Optional[List[str]] = None, names: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {"output": ["host", "hostid", "name"], "selectInterfaces": ["ip"]}
        if groups:
            groups_res = await self.get_hostgroups(groups)
            params["groupids"] = [g["groupid"] for g in groups_res]
        if names:
            params.setdefault("filter", {})["host"] = names
        return await self._rpc("host.get", params)

    async def get_triggers(
        self,
        severities: Optional[List[int]] = None,
        hosts: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {
            "output": ["triggerid", "description", "priority"],
            "filter": {},
        }
        if severities is not None:
            params["filter"]["priority"] = severities
        if hosts:
            host_res = await self.get_hosts(names=hosts)
            params["hostids"] = [h["hostid"] for h in host_res]
        return await self._rpc("trigger.get", params)

    async def get_events(
        self,
        time_from: Optional[int] = None,
        time_till: Optional[int] = None,
        severities: Optional[List[int]] = None,
        group_names: Optional[List[str]] = None,
        host_names: Optional[List[str]] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {
            "output": ["eventid", "clock", "name", "objectid"],
            "selectHosts": ["host", "name"],
            "sortfield": "clock",
            "sortorder": "DESC",
            "limit": limit,
        }
        if time_from is not None:
            params["time_from"] = time_from
        if time_till is not None:
            params["time_till"] = time_till
        if group_names:
            groups = await self.get_hostgroups(group_names)
            params["groupids"] = [g["groupid"] for g in groups]
        if host_names:
            hosts = await self.get_hosts(names=host_names)
            params["hostids"] = [h["hostid"] for h in hosts]

        events = await self._rpc("event.get", params)
        trigger_ids = list({e["objectid"] for e in events if e.get("objectid")})
        triggers = await self._rpc(
            "trigger.get",
            {
                "output": ["triggerid", "priority", "description"],
                "triggerids": trigger_ids,
            },
        )
        by_id = {t["triggerid"]: t for t in triggers}
        for e in events:
            tr = by_id.get(e.get("objectid"))
            if tr:
                e["severity"] = tr.get("priority", 0)
                e["trigger_description"] = tr.get("description")
        return events

    async def api_version(self) -> str:
        res = await self._rpc("apiinfo.version", {})
        return str(res)


class MockZabbixClient:
    def __init__(self) -> None:
        self._token = "mock"

    async def login(self) -> None:
        return None

    async def logout(self) -> None:
        return None

    async def get_events(
        self,
        time_from: Optional[int] = None,
        time_till: Optional[int] = None,
        severities: Optional[List[int]] = None,
        group_names: Optional[List[str]] = None,
        host_names: Optional[List[str]] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        base = [
            {
                "eventid": 10001,
                "clock": time_till or 1732680000,
                "name": "CPU usage high",
                "objectid": 20001,
                "hosts": [{"host": "web-01", "name": "web-01", "interfaces": [{"ip": "10.0.0.11"}]}],
                "severity": 4,
                "trigger_description": "High CPU on web-01",
            },
            {
                "eventid": 10002,
                "clock": (time_till or 1732680000) - 120,
                "name": "Disk space low",
                "objectid": 20002,
                "hosts": [{"host": "db-01", "name": "db-01", "interfaces": [{"ip": "10.0.0.21"}]}],
                "severity": 5,
                "trigger_description": "Critical disk usage on db-01",
            },
            {
                "eventid": 10003,
                "clock": (time_till or 1732680000) - 360,
                "name": "Service timeout",
                "objectid": 20003,
                "hosts": [{"host": "api-01", "name": "api-01", "interfaces": [{"ip": "10.0.0.31"}]}],
                "severity": 3,
                "trigger_description": "Service timeout detected",
            },
        ]
        data = base[:limit]
        if severities:
            data = [e for e in data if int(e.get("severity", 0)) in severities]
        if host_names:
            data = [e for e in data if any(h.get("host") in host_names for h in e.get("hosts", []))]
        if group_names:
            data = data  # Mock does not filter by groups
        return data
