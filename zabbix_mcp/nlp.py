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

import re
import time
from typing import Optional

from .schemas import AlertQuery, TimeRange


def parse_alert_query(text: str) -> AlertQuery:
    t = text.strip().lower()
    limit = 100
    sort_by: Optional[str] = None
    severities = None
    groups = None
    hosts = None
    tr: Optional[TimeRange] = None

    if "今日" in t or "today" in t:
        now = int(time.time())
        start = now - (now % 86400)
        tr = TimeRange(start_ts=start, end_ts=now)

    m = re.search(r"top\s*(\d+)", t)
    if m:
        limit = int(m.group(1))
        sort_by = "severity"
    if "按严重" in t or "by severity" in t:
        sort_by = "severity"
    if "按频率" in t or "by frequency" in t:
        sort_by = "frequency"
    if "按时间" in t or "by time" in t:
        sort_by = "time"

    sev_map = {"disaster": 5, "high": 4, "average": 3, "warning": 2, "information": 1, "not classified": 0, "严重": 4, "灾难": 5}
    for k, v in sev_map.items():
        if k in t:
            severities = [v]
            break

    mg = re.search(r"主机组[:：]?([\w-]+)", t)
    if mg:
        groups = [mg.group(1)]

    mh = re.search(r"主机[:：]?([\w.-]+)", t)
    if mh:
        hosts = [mh.group(1)]

    return AlertQuery(
        time_range=tr,
        host_groups=groups,
        hosts=hosts,
        severities=severities,
        limit=limit,
        sort_by=sort_by,  # type: ignore[arg-type]
    )

