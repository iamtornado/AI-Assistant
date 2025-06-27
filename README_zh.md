# AI 助手

一个集成了 Chainlit 和 RAGFlow 并使用 Redis 消息队列的流式 AI 助手应用程序。

# 完整报告
- Email: 请点击查看完整项目报告：[https://alidocs.dingtalk.com/i/nodes/1DKw2zgV2PAo2rA7uLr72orN8B5r9YAn?utm_scene=team_space]

## 概述
本项目提供了一个具有流式响应、文档引用和人工代理升级功能的交互式 AI 助手。该应用程序使用 Chainlit 作为前端界面，RAGFlow 用于后端知识检索和响应生成。

## 功能特点
- 实时流式响应
- 文档引用集成
- 人工代理升级
- 基于 Redis 的消息队列
- OAuth 身份验证
- 结构化日志
- 基于环境的配置

## 环境要求
- Python 3.12+ 
- Redis 服务器
- RAGFlow API 访问权限
- Rocket.Chat 服务器（用于人工升级）

## 安装步骤
1. 克隆此仓库
2. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```
3. 创建包含所需环境变量的 `.env` 文件（参见配置部分）

## 配置
所需环境变量：
- `RAGFLOW_API_KEY`：用于 RAGFlow 访问的 API 密钥
- `RAGFLOW_BASE_URL`：RAGFlow API 的基础 URL
- `RAGFLOW_ASSISTANT_NAME`：RAGFlow 助手的名称
- `REDIS_HOST`：Redis 服务器主机名
- `REDIS_PORT`：Redis 服务器端口
- `REDIS_PASSWORD`：Redis 身份验证密码
- `ROCKETCHAT_SERVER_URL`：Rocket.Chat 服务器 URL
- `ROCKETCHAT_WEBHOOK_TOKEN`：Rocket.Chat Webhook 身份验证令牌
- `LDAP_PASSWORD`：LDAP 身份验证密码
- `WEEKDAY_USERS`：用于人工升级的 Rocket.Chat 用户逗号分隔列表
- `OAUTH_KEYCLOAK_BASE_URL`：Keycloak OAuth 服务器的基础 URL
- `OAUTH_KEYCLOAK_REALM`：Keycloak 领域名称
- `OAUTH_KEYCLOAK_CLIENT_ID`：Keycloak 客户端 ID
- `OAUTH_KEYCLOAK_CLIENT_SECRET`：Keycloak 客户端密钥
- `OAUTH_KEYCLOAK_NAME`：Keycloak OAuth 提供程序名称
- `CHAINLIT_AUTH_SECRET`：Chainlit 身份验证密钥
- `IT_ENVIRONMENT`：环境类型（dev 或 test）
- `REDIS_DB_INDEX_DEV`：开发环境的 Redis 数据库索引
- `REDIS_DB_INDEX_TEST`：测试环境的 Redis 数据库索引
- `LOG_LEVEL`：日志级别（DEBUG、INFO、WARNING、ERROR、CRITICAL）
- `PROPAGATE_LOGS`：是否将日志传播到父记录器（True/False）

## 使用方法
启动应用程序：
```bash
    uvicorn webhook_server:app --host 0.0.0.0 --port 8000
```

## 项目结构
- `chainlit_ragflow_streaming.py`：应用程序主入口点
- `ragflow_client.py`：RAGFlow API 客户端
- `message_queue.py`：Redis 队列实现
- `logger_config.py`：日志配置
- `webhook_server.py`：Webhook 处理服务器
- `requirements.txt`：项目依赖

## 作者信息

- 邮箱：[1426693102@qq.com]
- GitHub：[https://github.com/iamtornado]
- 网站：[https://alidocs.dingtalk.com/i/nodes/Amq4vjg890AlRbA6Td9ZvlpDJ3kdP0wQ?utm_scene=team_space]

## 许可证
本项目采用 MIT 许可证。有关更多信息，请参见本仓库中包含的 `License` 文件。