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

from prometheus_client import Counter, Gauge, Histogram

REQUEST_COUNT = Counter("zabbix_mcp_requests_total", "Total requests", ["route"])
REQUEST_LATENCY = Histogram("zabbix_mcp_request_latency_seconds", "Request latency", ["route"])
QUEUE_SIZE = Gauge("zabbix_mcp_queue_size", "In-memory queue size")
ACTIVE_CLIENTS = Gauge("zabbix_mcp_active_clients", "Active websocket clients")

