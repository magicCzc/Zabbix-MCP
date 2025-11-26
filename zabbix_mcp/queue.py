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
from typing import Any, Callable, Dict, Optional, List

from .metrics import QUEUE_SIZE


class TaskQueue:
    def __init__(self, workers: int = 4) -> None:
        self.queue: asyncio.Queue = asyncio.Queue()
        self.workers = workers
        self._tasks: List[asyncio.Task] = []
        self._handler: Optional[Callable[[Dict[str, Any]], asyncio.Future]] = None

    async def start(self, handler: Callable[[Dict[str, Any]], asyncio.Future]) -> None:
        self._handler = handler
        for _ in range(self.workers):
            self._tasks.append(asyncio.create_task(self._run()))

    async def stop(self) -> None:
        for t in self._tasks:
            t.cancel()
        self._tasks.clear()

    async def enqueue(self, job: Dict[str, Any]) -> None:
        await self.queue.put(job)
        QUEUE_SIZE.set(self.queue.qsize())

    async def _run(self) -> None:
        while True:
            job = await self.queue.get()
            QUEUE_SIZE.set(self.queue.qsize())
            try:
                if self._handler:
                    await self._handler(job)
            finally:
                self.queue.task_done()
