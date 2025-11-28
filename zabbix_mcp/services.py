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
from typing import List, Tuple, Optional, Dict

from .schemas import AlertQuery, LogAssociationQuery, AlertItem, AlertResponse
from .zabbix_client import ZabbixClient


def _normalize_host_ip(host: dict) -> Optional[str]:
    try:
        interfaces = host.get("interfaces") or host.get("selectInterfaces")
        if interfaces and isinstance(interfaces, list) and interfaces:
            return interfaces[0].get("ip")
        return None
    except Exception:
        return None


async def query_alerts(client: ZabbixClient, query: AlertQuery) -> AlertResponse:
    time_from = query.time_range.start_ts if query.time_range else None
    time_till = query.time_range.end_ts if query.time_range else None
    events = await client.get_events(
        time_from=time_from,
        time_till=time_till,
        severities=query.severities,
        group_names=query.host_groups,
        host_names=query.hosts,
        limit=query.limit,
    )
    items: List[AlertItem] = []
    for e in events:
        hosts = e.get("hosts") or []
        host_name = hosts[0].get("host") if hosts else ""
        host_ip = _normalize_host_ip(hosts[0]) if hosts else None
        items.append(
            AlertItem(
                id=str(e.get("eventid")),
                name=e.get("name") or e.get("trigger_description") or "",
                host=host_name,
                host_ip=host_ip,
                severity=int(e.get("severity", 0)),
                timestamp=int(e.get("clock", 0)),
            )
        )
    # Sorting
    if query.severities:
        items = [it for it in items if it.severity in query.severities]
    if query.sort_by == "severity":
        items.sort(key=lambda x: x.severity, reverse=True)
    elif query.sort_by == "time":
        items.sort(key=lambda x: x.timestamp, reverse=True)
    elif query.sort_by == "frequency":
        # Frequency by alert name
        freq: Dict[str, int] = {}
        for it in items:
            freq[it.name] = freq.get(it.name, 0) + 1
        items.sort(key=lambda x: freq.get(x.name, 0), reverse=True)
    return AlertResponse(items=items, total=len(items))


async def today_alerts(client: ZabbixClient, limit: int = 100) -> AlertResponse:
    now = int(time.time())
    start = now - (now % 86400)
    q = AlertQuery(time_range={"start_ts": start, "end_ts": now}, limit=limit)
    return await query_alerts(client, q)


async def associate_logs(
    client: ZabbixClient, query: LogAssociationQuery
) -> Tuple[AlertResponse, List[str]]:
    # Simple fuzzy matching on event/trigger names by keywords
    alerts = await query_alerts(
        client,
        AlertQuery(
            time_range=query.time_range,
            host_groups=query.host_groups,
            hosts=query.hosts,
            limit=query.limit,
        ),
    )
    lowered = [k.lower() for k in query.keywords]
    matched = [
        it for it in alerts.items if any(k in (it.name or "").lower() for k in lowered)
    ]
    return AlertResponse(items=matched, total=len(matched)), lowered
