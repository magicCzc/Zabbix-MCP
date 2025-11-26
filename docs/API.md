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

# 接口文档（OpenAPI/Swagger）

> 认证机制：所有非公开接口需携带 `Authorization: Bearer <token>`；`read` 令牌访问查询接口，`admin` 令牌访问管理与队列接口。

## OpenAPI 3.0 规范

```yaml
openapi: 3.0.3
info:
  title: Zabbix-MCP API
  version: 0.1.0
servers:
  - url: http://localhost:5656
components:
  securitySchemes:
    bearerAuth:
      type: http
      scheme: bearer
  schemas:
    AlertItem:
      type: object
      properties:
        id: { type: string }
        name: { type: string }
        host: { type: string }
        host_ip: { type: string, nullable: true }
        severity: { type: integer }
        timestamp: { type: integer }
        group: { type: string, nullable: true }
    AlertsList:
      type: object
      properties:
        items:
          type: array
          items: { $ref: '#/components/schemas/AlertItem' }
        total: { type: integer }
    QueryPayload:
      type: object
      properties:
        severities:
          type: array
          items: { type: integer }
        host_group: { type: string }
        host: { type: string }
        limit: { type: integer }
        from_ts: { type: integer }
        to_ts: { type: integer }
    NLQuery:
      type: object
      properties:
        text: { type: string }
    LogAssociate:
      type: object
      properties:
        keywords:
          type: array
          items: { type: string }
        limit: { type: integer }
    Error:
      type: object
      properties:
        i18n_key: { type: string }
        message: { type: string }
security:
  - bearerAuth: []
paths:
  /health:
    get:
      summary: 健康检查
      responses:
        '200': { description: OK }
  /version:
    get:
      summary: Zabbix API 版本
      security: [ { bearerAuth: [] } ]
      responses:
        '200': { description: OK }
        '403': { description: Forbidden }
  /alerts/query:
    post:
      summary: 组合过滤获取告警
      security: [ { bearerAuth: [] } ]
      requestBody:
        required: true
        content:
          application/json:
            schema: { $ref: '#/components/schemas/QueryPayload' }
      responses:
        '200':
          description: OK
          content:
            application/json:
              schema: { $ref: '#/components/schemas/AlertsList' }
        '400': { description: Bad Request }
        '502': { description: Zabbix API Error }
  /alerts/today:
    get:
      summary: 今日告警
      security: [ { bearerAuth: [] } ]
      parameters:
        - in: query
          name: limit
          schema: { type: integer, default: 100 }
      responses:
        '200': { description: OK }
  /alerts/top:
    get:
      summary: TOP 告警
      security: [ { bearerAuth: [] } ]
      parameters:
        - in: query
          name: by
          schema: { type: string, enum: [severity, frequency] }
        - in: query
          name: limit
          schema: { type: integer, default: 100 }
      responses:
        '200': { description: OK }
  /alerts/nl:
    post:
      summary: 自然语言查询告警
      security: [ { bearerAuth: [] } ]
      requestBody:
        required: true
        content:
          application/json:
            schema: { $ref: '#/components/schemas/NLQuery' }
      responses:
        '200': { description: OK }
  /logs/associate:
    post:
      summary: 日志关联
      security: [ { bearerAuth: [] } ]
      requestBody:
        required: true
        content:
          application/json:
            schema: { $ref: '#/components/schemas/LogAssociate' }
      responses:
        '200': { description: OK }
  /queue/enqueue:
    post:
      summary: 入队任务（Admin）
      security: [ { bearerAuth: [] } ]
      responses:
        '200': { description: OK }
        '403': { description: Forbidden }
  /queue/stats:
    get:
      summary: 队列统计（Admin）
      security: [ { bearerAuth: [] } ]
      responses:
        '200': { description: OK }
        '403': { description: Forbidden }
  /config/reload:
    post:
      summary: 配置热更新（Admin）
      security: [ { bearerAuth: [] } ]
      responses:
        '200': { description: OK }
        '403': { description: Forbidden }
  /metrics:
    get:
      summary: Prometheus 指标（公开）
      responses:
        '200': { description: OK }
```

## 示例
- 今日告警：
```bash
curl -H "Authorization: Bearer read" "http://localhost:5656/alerts/today?limit=5"
```
- 组合过滤：
```bash
curl -H "Authorization: Bearer read" -H "Content-Type: application/json" \
  -d '{"severities":[4],"limit":5}' http://localhost:5656/alerts/query
```

## 错误代码
- `403 Forbidden`：令牌不足或缺失
- `400 Bad Request`：参数校验失败（Pydantic）
- `502 Zabbix API Error`：后端 Zabbix API 返回错误

## 调用限制
- 建议 `limit <= 100`；高并发由服务端信号量控制（`zabbix_mcp/zabbix_client.py:18`）
- 生产环境可在反向代理层设置速率限制

## WebSocket
- `GET /mcp/ws`：用于 C/S 客户端管理（不在 OpenAPI 覆盖范围），需要 `Authorization: Bearer admin`

