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

# 安全注意事项

## .env 管理规范
- `.env` 已加入 `.gitignore`，严禁提交到仓库。
- 本地开发允许使用 `.env`；测试/生产优先使用系统环境变量或秘密管理服务（如 Vault/KeyVault）。
- 修改 `.env` 后请调用 `POST /config/reload` 热更新，避免重启泄露日志。

## 敏感信息存储建议
- 推荐使用秘密管理系统：
  - HashiCorp Vault / Azure Key Vault / AWS Secrets Manager / GCP Secret Manager
- 最低要求：
  - 使用操作系统级凭据存储（Windows Credential Manager/macOS Keychain/Linux KWallet）
  - 环境变量仅在进程上下文中注入，不写入日志

## 凭证轮换流程
- 建立轮换频率（例如每 90 天），并在 Zabbix 与本服务同步更新：
  1. 在 Zabbix 侧创建新令牌或更新密码（保留旧值一段时间）
  2. 在秘密管理系统中更新条目，推送到服务节点
  3. 调用 `POST /config/reload` 生效
  4. 验证 `/health` 与关键查询接口正常
  5. 回收旧令牌/密码

## 传输与访问控制
- 尽量启用 `VERIFY_SSL=1` 并配置受信证书；内网自签证书需正确分发根证。
- 所有查询接口要求 `Authorization: Bearer read`；管理/队列接口要求 `Authorization: Bearer admin`。
- 反向代理层建议开启速率限制与 IP 访问控制。

## 日志与合规
- 不在日志输出中打印凭证、令牌或完整 URL 查询参数。
- 审计可记录接口调用时间、来源、结果码、耗时与请求ID；避免记录 Body 中敏感字段。

