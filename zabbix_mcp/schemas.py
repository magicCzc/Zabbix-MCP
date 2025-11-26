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

from typing import List, Optional, Literal
from pydantic import BaseModel, Field


class TimeRange(BaseModel):
    start_ts: int = Field(..., description="Unix timestamp seconds start")
    end_ts: int = Field(..., description="Unix timestamp seconds end")


class AlertQuery(BaseModel):
    time_range: Optional[TimeRange] = None
    host_groups: Optional[List[str]] = None
    hosts: Optional[List[str]] = None
    severities: Optional[List[int]] = Field(
        default=None, description="Zabbix trigger priority 0-5"
    )
    limit: int = 100
    sort_by: Optional[Literal["severity", "frequency", "time"]] = None


class LogAssociationQuery(BaseModel):
    keywords: List[str]
    time_range: Optional[TimeRange] = None
    host_groups: Optional[List[str]] = None
    hosts: Optional[List[str]] = None
    limit: int = 100


class AlertItem(BaseModel):
    id: str
    name: str
    host: str
    host_ip: Optional[str] = None
    severity: int
    timestamp: int
    group: Optional[str] = None


class AlertResponse(BaseModel):
    items: List[AlertItem]
    total: int


class ErrorResponse(BaseModel):
    i18n_key: str
    message: str


class NLQuery(BaseModel):
    text: str
