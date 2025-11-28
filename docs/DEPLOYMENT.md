<!--
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
-->

# 部署使用文档

## 环境要求
- Python: `>=3.8`（推荐 3.12）
- Node.js: 非必需（本项目不依赖 Node.js）
- 操作系统：Windows/Linux/macOS 均可

## 配置与环境变量
- 使用 `.env` 文件或系统环境变量进行配置；服务在启动时自动加载 `.env`（`zabbix_mcp/config.py:34`）。
- 必填：
  - `ZABBIX_URL`（例如 `http://your-zabbix.example.com/zabbix`）
  - `ZABBIX_USERNAME` + `ZABBIX_PASSWORD`，或 `ZABBIX_TOKEN`
- 可选：`REQUEST_TIMEOUT_SECONDS`、`MAX_CONCURRENCY`、`VERIFY_SSL`、`MOCK_MODE`
- 鉴权令牌（RBAC）：`MCP_AUTH_TOKEN_READ`、`MCP_AUTH_TOKEN_ADMIN`

## 安装依赖
```bash
python -m pip install -U pip
python -m pip install -r requirements.txt
```

## 启动与停止
- 启动（真实模式）：
```bash
uvicorn zabbix_mcp.api:app --host 0.0.0.0 --port 5656
```
- 健康检查：`GET /health`
- 停止：Ctrl+C（或进程管理工具）

### 脚本启动（推荐）
- Windows（Python 3.8）：
```powershell
powershell -File scripts\start_win38.ps1 -EnvFile ".env" -Port 5656 -Host "0.0.0.0"
```
- Linux/macOS（Python 3.8/3.x）：
```bash
ENV_FILE=.env PORT=5656 HOST=0.0.0.0 bash scripts/start_unix38.sh
```

## 多环境部署流程
### Python 3.8 兼容说明
- 项目已兼容 Python 3.8（移除 `|` 联合类型与新泛型语法）。
- 若系统 Python 固定为 3.8：
  - Windows：使用已安装的 3.8 创建虚拟环境并安装依赖：
    ```powershell
    py -3.8 -m venv .venv
    .venv\Scripts\Activate.ps1
    python -m pip install -r requirements.txt
    uvicorn zabbix_mcp.api:app --host 0.0.0.0 --port 8000
    ```
  - Linux/macOS：
    ```bash
    python3.8 -m venv .venv
    source .venv/bin/activate
    python -m pip install -r requirements.txt
    uvicorn zabbix_mcp.api:app --host 0.0.0.0 --port 8000
    ```
  - 若无法改动宿主环境，建议使用容器运行（示例）：
    ```bash
    docker run -e ZABBIX_URL=... -e ZABBIX_TOKEN=... -p 8000:8000 your-image
    ```
### 开发环境
- 创建 `.env` 并填入测试 Zabbix 地址与只读账户
- 启动服务并验证 `/alerts/today`、`/alerts/top`、`/logs/associate`、`/alerts/nl`
- 使用 `POST /config/reload` 热更新配置

### 验证脚本
- Windows：
```powershell
powershell -File scripts\smoke_test.ps1 -EnvFile ".env" -BaseUrl "http://127.0.0.1:5656"
```
- Linux/macOS：
```bash
ENV_FILE=.env BASE_URL=http://127.0.0.1:5656 bash scripts/smoke_test.sh
```

### 测试环境
- 通过 CI/CD 注入环境变量（不提交 `.env` 到仓库）
- 使用 `pip install -r requirements.txt` 安装依赖
- 开启 `VERIFY_SSL=1`；RBAC 令牌由秘密管理系统下发
- 采集 `GET /metrics` 指标，设置 p95 延迟与失败率阈值告警

### 生产环境
- 使用只读或受限权限账号；优先使用 `ZABBIX_TOKEN`
- RBAC：区分 `read` 与 `admin` 令牌，限制管理接口访问
- 配置监控与日志采集；定期轮换凭证

## 常见问题排查
- PowerShell URL 含 `&`：需用双引号包裹，如 `"http://.../alerts/top?by=severity&limit=100"`
- 返回 `error.config_missing`：检查 `.env` 中必填项是否正确，或调用 `/config/reload`
- SSL 错误：设 `VERIFY_SSL=0` 或正确安装受信证书链
- RBAC 403：检查 `Authorization: Bearer <token>` 是否正确
- Zabbix 响应慢：观察 `request_latency_seconds`、提升并发、靠近 Zabbix 部署网络位置
