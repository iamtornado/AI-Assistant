import os
import requests
import aiohttp
import json
from typing import Optional
import chainlit as cl

from logger_config import setup_logger
logger = setup_logger(__name__)

CHAT_ASSISTANT_NAME = os.getenv('RAGFLOW_ASSISTANT_NAME', 'AI-assist')

class RAGFlowClient:
    """RAGFlow API客户端，处理与后端的交互"""
    def __init__(self, api_key: str, base_url: str):
        self.api_key = api_key
        self.base_url = base_url
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        self.chat_id: Optional[str] = None

    def get_chat_id(self, assistant_name: str) -> str:
        """根据助手名称获取聊天ID"""
        url = f"{self.base_url}/api/v1/chats?name={assistant_name}"
        response = requests.get(url, headers=self.headers)
        response_data = response.json()

        if response_data['code'] != 0:
            raise ValueError(f"获取助手ID失败: {response_data['message']}")
        if not response_data['data']:
            raise ValueError(f"未找到名称为'{assistant_name}'的AI助手")

        return response_data['data'][0]['id']

    def create_chat_session(self) -> str:
        """创建新的聊天会话"""
        if not self.chat_id:
            self.chat_id = self.get_chat_id(CHAT_ASSISTANT_NAME)

        url = f"{self.base_url}/api/v1/chats/{self.chat_id}/sessions"
        session_name = cl.user_session.get("user").identifier
        response = requests.post(
            url, headers=self.headers, json={'name': f"chaint_session:{session_name}"}
        )
        response_data = response.json()

        if response_data['code'] != 0:
            raise ValueError(f"创建会话失败: {response_data['message']}")

        return response_data['data']['id']

    async def stream_chat_completion(self, question: str, msg: cl.Message):
        """流式获取聊天完成结果并直接发送到Chainlit前端"""
        session_id = self.create_chat_session()
        url = f"{self.base_url}/api/v1/chats/{self.chat_id}/completions"

        payload = {
            "question": question,
            "stream": True,
            "session_id": session_id,
            "user_id": cl.user_session.get("user").identifier
        }

        # 用于跟踪已发送的内容，避免重复
        sent_content = ""
        # 存储引用的文档
        referenced_docs = []

        with requests.post(
            url, headers=self.headers, json=payload, stream=True
        ) as response:
            for line in response.iter_lines():
                if line:
                    try:
                        # 处理SSE格式数据
                        line = line.decode('utf-8').lstrip('data: ').strip()
                        if not line:
                            continue
                        json_data = json.loads(line)

                        # 检查是否为结束标志
                        if json_data.get('code') == 0 and json_data.get('data') is True:
                            break

                        if (
                            isinstance(json_data, dict) and 
                            json_data.get('code') == 0 and 
                            isinstance(json_data.get('data'), dict)
                        ):
                            answer_chunk = json_data['data'].get('answer', '')

                            # 提取引用文档信息（使用doc_aggs聚合数据避免重复）
                            if 'reference' in json_data['data']:
                                reference_data = json_data['data']['reference']
                                # 优先使用doc_aggs获取聚合的引用文档信息
                                if 'doc_aggs' in reference_data and isinstance(reference_data['doc_aggs'], list):
                                    # 遍历聚合文档列表
                                    for doc_info in reference_data['doc_aggs']:
                                        doc_id = doc_info.get('doc_id')
                                        doc_name = doc_info.get('doc_name')
                                        # 检查文档ID和名称是否存在
                                        if doc_id and doc_name:
                                            referenced_docs.append((doc_id, doc_name))
                                # 兼容处理：如果没有doc_aggs则使用chunks（旧版API兼容）
                                elif 'chunks' in reference_data:
                                    seen_document_ids = set()
                                    for chunk in reference_data['chunks']:
                                        doc_id = chunk.get('document_id')
                                        doc_name = chunk.get('document_name')
                                        if doc_id and doc_name and doc_id not in seen_document_ids:
                                            referenced_docs.append((doc_id, doc_name))
                                            seen_document_ids.add(doc_id)

                            if answer_chunk and answer_chunk != sent_content:
                                # 计算新增内容
                                new_content = answer_chunk[len(sent_content):]
                                if new_content:
                                    await msg.stream_token(new_content)
                                    sent_content = answer_chunk
                    except json.JSONDecodeError:
                        continue

            # 使用Chainlit File元素展示引用文档
            if referenced_docs:
                # 调试：打印引用文档列表所有内容
                # Replace print statements with logger.debug
                # Original: print("【debug】referenced_docs内容: ", json.dumps(referenced_docs, indent=2, ensure_ascii=False))
                # logger.debug(f"referenced_docs内容: {json.dumps(referenced_docs, indent=2, ensure_ascii=False)}")
                logger.debug(f"referenced_docs内容: {referenced_docs}")
                elements = []
                for doc_id, doc_name in referenced_docs:
                    doc_url = f"{self.base_url}/document/{doc_id}?ext={doc_name.split('.')[-1]}&prefix=document"
                    logger.debug(f"变量doc_url的值为: {doc_url}")
                    elements.append(cl.File(name=doc_name, url=doc_url))
                # 打印elements变量的值到终端，方便诊断
                logger.debug(f"elements变量的值为: {elements}")
                actions = [
                cl.Action(
                name="转人工",
                icon="mouse-pointer-click",
                payload={"value": "example_value"},
                label="点我立即转人工"
            )
        ]
                # 发送包含文件元素的消息
                await cl.Message(content="\n\n### 引用文档", elements=elements, actions=actions).send()

            # 明确标记消息完成状态
            await msg.update()