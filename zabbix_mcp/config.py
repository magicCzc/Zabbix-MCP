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

from pydantic import BaseModel, Field, AnyHttpUrl, SecretStr
from typing import Optional
import os
from dotenv import load_dotenv


class Settings(BaseModel):
    zabbix_url: AnyHttpUrl = Field(..., alias="ZABBIX_URL")
    zabbix_username: Optional[str] = Field(None, alias="ZABBIX_USERNAME")
    zabbix_password: Optional[SecretStr] = Field(None, alias="ZABBIX_PASSWORD")
    zabbix_token: Optional[SecretStr] = Field(None, alias="ZABBIX_TOKEN")
    request_timeout_seconds: int = Field(30, alias="REQUEST_TIMEOUT_SECONDS")
    max_concurrency: int = Field(8, alias="MAX_CONCURRENCY")
    mock_mode: bool = Field(False, alias="MOCK_MODE")
    verify_ssl: bool = Field(True, alias="VERIFY_SSL")
    read_only: bool = Field(True, alias="READ_ONLY")
    max_results_limit: int = Field(100, alias="MAX_RESULTS_LIMIT")


def load_settings() -> Settings:
    load_dotenv(dotenv_path=os.getenv("ENV_FILE", ".env"))
    env = {
        "ZABBIX_URL": os.getenv("ZABBIX_URL"),
        "ZABBIX_USERNAME": os.getenv("ZABBIX_USERNAME"),
        "ZABBIX_PASSWORD": os.getenv("ZABBIX_PASSWORD"),
        "ZABBIX_TOKEN": os.getenv("ZABBIX_TOKEN"),
        "REQUEST_TIMEOUT_SECONDS": os.getenv("REQUEST_TIMEOUT_SECONDS", "30"),
        "MAX_CONCURRENCY": os.getenv("MAX_CONCURRENCY", "8"),
        "MOCK_MODE": os.getenv("MOCK_MODE", "0"),
        "VERIFY_SSL": os.getenv("VERIFY_SSL", "1"),
        "READ_ONLY": os.getenv("READ_ONLY", "1"),
        "MAX_RESULTS_LIMIT": os.getenv("MAX_RESULTS_LIMIT", "100"),
    }
    return Settings.model_validate(env)
