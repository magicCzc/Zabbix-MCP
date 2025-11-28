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
    t = text.strip()
    tl = t.lower()
    limit = 100
    sort_by: Optional[str] = None
    severities = None
    groups = None
    hosts = None
    tr: Optional[TimeRange] = None

    if "今日" in tl or "today" in tl:
        now = int(time.time())
        start = now - (now % 86400)
        tr = TimeRange(start_ts=start, end_ts=now)

    mr = re.search(r"最近\s*(\d+)\s*(分钟|分|小时|h|天|day|d)", t)
    if mr:
        now = int(time.time())
        n = int(mr.group(1))
        unit = mr.group(2).lower()
        if unit in {"分钟", "分"}:
            dur = n * 60
        elif unit in {"小时", "h"}:
            dur = n * 3600
        else:
            dur = n * 86400
        tr = TimeRange(start_ts=now - dur, end_ts=now)

    m = re.search(r"top\s*(\d+)", tl)
    if m:
        limit = int(m.group(1))
        sort_by = "severity"
    if "按严重" in tl or "by severity" in tl:
        sort_by = "severity"
    if "按频率" in tl or "by frequency" in tl:
        sort_by = "frequency"
    if "按时间" in tl or "by time" in tl:
        sort_by = "time"

    sev_map = {"disaster": 5, "critical": 5, "high": 4, "error": 4, "average": 3, "warning": 3, "information": 1, "not classified": 0, "严重": 4, "灾难": 5}
    nums = re.findall(r"\((\d)\)", t)
    if nums:
        try:
            severities = [int(x) for x in nums]
        except Exception:
            pass
    if severities is None:
        picks = []
        for k, v in sev_map.items():
            if k in tl:
                picks.append(v)
        if picks:
            severities = sorted(set(picks))

    mg = re.search(r"主机组[:：]?([\w-]+)", t)
    if mg:
        groups = [mg.group(1)]

    mh = re.search(r"主机[:：]?([\w.-]+)", t)
    if mh:
        hosts = [mh.group(1)]

    lm = re.search(r"限制条数[:：]?\s*(\d+)", t)
    if lm:
        try:
            limit = int(lm.group(1))
        except Exception:
            pass

    return AlertQuery(
        time_range=tr,
        host_groups=groups,
        hosts=hosts,
        severities=severities,
        limit=limit,
        sort_by=sort_by,  # type: ignore[arg-type]
    )

