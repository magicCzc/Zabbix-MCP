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

from typing import Set
from fastapi import WebSocket
from .metrics import ACTIVE_CLIENTS


class ClientRegistry:
    def __init__(self) -> None:
        self.clients: Set[WebSocket] = set()

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self.clients.add(ws)
        ACTIVE_CLIENTS.set(len(self.clients))

    async def disconnect(self, ws: WebSocket) -> None:
        try:
            self.clients.remove(ws)
        except KeyError:
            pass
        ACTIVE_CLIENTS.set(len(self.clients))

    async def broadcast(self, message: str) -> None:
        for ws in list(self.clients):
            try:
                await ws.send_text(message)
            except Exception:
                await self.disconnect(ws)

