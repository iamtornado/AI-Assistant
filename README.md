# AI Assistant

[![Chinese Version（简体中文）](https://img.shields.io/badge/-Chinese%20Version-blue)](README_zh.md)

A streaming AI assistant application integrating Chainlit and RAGFlow with Redis message queuing.

# Complete Report
- Email: Please read：[https://alidocs.dingtalk.com/i/nodes/1DKw2zgV2PAo2rA7uLr72orN8B5r9YAn?utm_scene=team_space]

## For detailed deployment instructions, please refer to the following document:
 - [Deployment Guide](https://alidocs.dingtalk.com/i/nodes/0eMKjyp813AopzA7sdjrlg7AVxAZB1Gv)
    
## Overview
This project provides an interactive AI assistant with streaming responses, document references, and human agent escalation capabilities. The application uses Chainlit for the frontend interface and RAGFlow for backend knowledge retrieval and response generation.

## Features
- Real-time streaming responses
- Document reference integration
- Human agent escalation
- Redis-based message queuing
- OAuth authentication
- Structured logging
- Environment-based configuration

## Requirements
- Python 3.12+
- Redis server
- RAGFlow API access
- Rocket.Chat server (for human escalation)


  
## Installation
1. Clone this repository
   ```bash
   git clone https://github.com/iamtornado/AI-Assistant.git
   ```
2. Create and activate a virtual environment:
   Linux:
   ```bash
   python -m venv .venv
   ```
   Windows:
   ```bash
   python -m venv .venv
   ```
   Activate the virtual environment:
   Linux:
   ```bash
   source .venv/bin/activate
   ```
   Windows:
   ```bash
   .venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -U fastapi uvicorn chainlit redis rocketchat_API
   ```
4. Create a `.env` file with required environment variables (see Configuration section)

## Configuration
Required environment variables:
- `RAGFLOW_API_KEY`: API key for RAGFlow access
- `RAGFLOW_BASE_URL`: Base URL for RAGFlow API
- `RAGFLOW_ASSISTANT_NAME`: Name of the RAGFlow assistant
- `REDIS_HOST`: Redis server hostname
- `REDIS_PORT`: Redis server port
- `REDIS_PASSWORD`: Redis authentication password
- `ROCKETCHAT_SERVER_URL`: URL for Rocket.Chat server
- `ROCKETCHAT_WEBHOOK_TOKEN`: Token for Rocket.Chat webhook authentication
- `LDAP_PASSWORD`: Password for LDAP authentication
- `WEEKDAY_USERS`: Comma-separated list of Rocket.Chat users for human escalation
- `OAUTH_KEYCLOAK_BASE_URL`: Base URL for Keycloak OAuth server
- `OAUTH_KEYCLOAK_REALM`: Keycloak realm name
- `OAUTH_KEYCLOAK_CLIENT_ID`: Keycloak client ID
- `OAUTH_KEYCLOAK_CLIENT_SECRET`: Keycloak client secret
- `OAUTH_KEYCLOAK_NAME`: Keycloak OAuth provider name
- `CHAINLIT_AUTH_SECRET`: Secret for Chainlit authentication
- `IT_ENVIRONMENT`: Environment type (dev or test)
- `REDIS_DB_INDEX_DEV`: Redis database index for development environment
- `REDIS_DB_INDEX_TEST`: Redis database index for test environment
- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `PROPAGATE_LOGS`: Whether to propagate logs to parent loggers (True/False)

## Usage
Start the application with:
```bash
    uvicorn webhook_server:app --host 0.0.0.0 --port 8000
```

## Project Structure
- `chainlit_ragflow_streaming.py`: Main application entry point
- `ragflow_client.py`: RAGFlow API client
- `message_queue.py`: Redis queue implementation
- `logger_config.py`: Logging configuration
- `webhook_server.py`: Webhook handling server
- `requirements.txt`: Project dependencies

## Author

- Email: [1426693102@qq.com]
- GitHub: [https://github.com/iamtornado]
- website: [https://alidocs.dingtalk.com/i/nodes/Amq4vjg890AlRbA6Td9ZvlpDJ3kdP0wQ?utm_scene=team_space]

## License
This project is licensed under the MIT License. For more information, please see the `License` file included in this repository.
