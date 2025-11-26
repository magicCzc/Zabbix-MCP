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

# Zabbix-MCP（Zabbix只读查询中台）

- Author: Chenzc
- Release Date: 2025-11-16
- Contact: 910445306@qq.com

## 概述
Zabbix-MCP 是一个面向 Zabbix 的只读查询中台，提供 REST/CLI 的统一查询、筛选、日志关联能力，并具备 RBAC、审计日志、资源限制、Prometheus 指标、配置热更新等运维友好特性。项目严格遵循只读原则，不包含任何可能修改系统状态的功能。

## 主要特性
- 只读安全：`READ_ONLY=1` 强制只读，中间件拦截非查询写法；管理端点在只读模式下返回 403
- 查询能力：
  - 告警今日/Top/组合过滤 `GET/POST`
  - 自然语言近似查询（规则驱动）
  - 日志关键词关联
- 运维能力：
  - RBAC（`read/admin`）与审计日志（路由/方法/角色/状态/耗时）
  - Prometheus `/metrics`、资源限制（超时/并发/结果上限）
  - 配置热更新与 `.env` 自动加载
- 跨平台与低成本：Python `>=3.8`，提供 Windows/Linux/macOS 一键启动与烟测脚本；无需数据库与消息队列即可运行

## 架构简述
- 接入层：FastAPI（REST）、WebSocket 客户端管理
- 业务层：查询组合与排序、日志关联规则
- 数据源：Zabbix HTTP API（只读调用：`event.get`、`trigger.get`、`host.get`、`hostgroup.get`、`apiinfo.version`）
- 监控：Prometheus 指标；审计中间件记录每次调用

## 环境要求
- Python: `>=3.8`（推荐 3.12）
- 操作系统：Windows/Linux/macOS

## 安装与启动
```bash
python -m pip install -U pip
python -m pip install -e .
uvicorn zabbix_mcp.api:app --host 0.0.0.0 --port 5656
```

或使用脚本（推荐）：
- Windows：
```powershell
powershell -File scripts\start_win38.ps1 -EnvFile ".env" -Port 5656 -Host "0.0.0.0"
```
- Linux/macOS：
```bash
ENV_FILE=.env PORT=5656 HOST=0.0.0.0 bash scripts/start_unix38.sh
```

## 配置（.env）
参考 `.env.example`，建议使用只读 `ZABBIX_TOKEN`：
```env
ZABBIX_URL=http://your-zabbix.example.com/zabbix
ZABBIX_TOKEN=your_readonly_token
REQUEST_TIMEOUT_SECONDS=30
MAX_CONCURRENCY=8
VERIFY_SSL=1
READ_ONLY=1
MAX_RESULTS_LIMIT=100
MCP_AUTH_TOKEN_ADMIN=strong_admin_token
MCP_AUTH_TOKEN_READ=strong_read_token
```
- 修改后可调用 `POST /config/reload` 热更新（只读模式下将被拒绝）。
- 生产环境建议通过秘密管理系统注入，不提交 `.env` 至仓库。

## 接口速览
- `GET /health`：健康检查
- `GET /version`：Zabbix API 版本（需 Zabbix 端权限）
- `GET /alerts/today`：今日告警（`limit` 参数受上限约束）
- `GET /alerts/top`：按严重/频次排序的告警
- `POST /alerts/query`：组合过滤（严重度、主机组、主机、时间窗口）
- `POST /alerts/nl`：自然语言近似查询（规则解析）
- `POST /logs/associate`：关键词匹配的日志关联
- `GET /metrics`：Prometheus 指标（公开）
- `POST /config/reload`、`POST /queue/enqueue`、`GET /queue/stats`：只读模式下返回 403

更多细节请见 `docs/API.md`。

## 只读与安全
- 强制只读：`READ_ONLY=1`，中间件拦截所有非查询写法
- RBAC：查询接口需 `read` 令牌；管理接口需 `admin` 令牌
- 资源限制：统一超时、并发控制、结果上限；防止高负载消耗
- 审计日志：记录路由、方法、角色、状态码与耗时；不记录敏感信息
- 传输安全：建议 `VERIFY_SSL=1` 并配置受信证书；反向代理启用速率限制与 IP 白名单
更多安全建议见 `docs/SECURITY.md`。

## 快速烟雾测试
- Windows：
```powershell
powershell -File scripts\smoke_test.ps1 -EnvFile ".env" -BaseUrl "http://127.0.0.1:5656"
```
- Linux/macOS：
```bash
ENV_FILE=.env BASE_URL=http://127.0.0.1:5656 bash scripts/smoke_test.sh
```
脚本会输出状态码与耗时，并将报告写入 `logs/smoke_*.log`。

## 开发者模式
- 代码风格：Python PEP8 & black（行宽 88）
- 依赖策略：禁止引入 GPL/LGPL；新增库需说明理由与包大小估算
- 性能目标：冷启动 ≤ 2s；查询 p95 ≤ 800ms（视 Zabbix 与网络）

## 许可证
Apache-2.0。请勿将敏感信息（如 `.env`）提交到仓库。

## 联系方式
- Author: Chenzc
- Release Date: 2025-11-16
- Contact: 910445306@qq.com

