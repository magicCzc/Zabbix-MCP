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

import os
from fastapi import Header, HTTPException


def require_role(required: str):
    async def checker(authorization: str | None = Header(default=None)):
        token = authorization.split(" ")[-1] if authorization else None
        admin = os.getenv("MCP_AUTH_TOKEN_ADMIN")
        read = os.getenv("MCP_AUTH_TOKEN_READ")
        role = None
        if token and admin and token == admin:
            role = "admin"
        elif token and read and token == read:
            role = "read"
        if required == "admin" and role != "admin":
            raise HTTPException(status_code=403, detail={"i18n_key": "error.forbidden", "message": "admin required"})
        if required == "read" and role not in {"admin", "read"}:
            raise HTTPException(status_code=403, detail={"i18n_key": "error.forbidden", "message": "read required"})
        return role
    return checker

