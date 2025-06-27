#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Chainlit与RAGFlow集成的流式交互应用
功能：接收用户输入，通过RAGFlow API获取流式回答并实时展示
"""
import json
import os
import requests
import datetime
from typing import Dict, Optional
from pprint import pprint
from rocketchat_API.rocketchat import RocketChat
# from rocketchat_API import RocketChatException  # 新增异常处理
import chainlit as cl
from chainlit import run_sync
import asyncio
import chainlit as cl
from typing import Optional
import logging
import uuid
from message_queue import RedisQueue
from ragflow_client import RAGFlowClient
# import session_utils
# 配置日志
from logger_config import setup_logger
logger = setup_logger(__name__)

# 初始化Redis队列
redis_queue = RedisQueue()

# 全局消息队列: Chainlit会话ID -> 消息队列
message_queues = {}
message_queues_lock = asyncio.Lock()
# 下面部分的代码很重要，这部分代码的含义是允许所有经过身份验证的用户登录到chainlit
@cl.oauth_callback
def oauth_callback(
  provider_id: str,
  token: str,
  raw_user_data: Dict[str, str],
  default_user: cl.User,
) -> Optional[cl.User]:
  return default_user

# ==============================================
# 配置参数区域 - 根据实际环境修改以下参数
# ==============================================
# API密钥，从RAGFlow平台获取
API_KEY = os.getenv('RAGFLOW_API_KEY')
# RAGFlow服务基础URL（通常格式为http://ip:port）
BASE_URL = os.getenv('RAGFLOW_BASE_URL')
# 目标AI助手名称（需在RAGFlow平台提前创建）
CHAT_ASSISTANT_NAME = os.getenv('RAGFLOW_ASSISTANT_NAME', 'AI-assist')


# Log OAUTH Keycloak environment variables
logger.debug("【debug】OAUTH_KEYCLOAK_BASE_URL的值为: %s", os.getenv("OAUTH_KEYCLOAK_BASE_URL"))
logger.debug("【debug】OAUTH_KEYCLOAK_REALM的值为: %s", os.getenv("OAUTH_KEYCLOAK_REALM"))
logger.debug("【debug】OAUTH_KEYCLOAK_CLIENT_ID的值为: %s", os.getenv("OAUTH_KEYCLOAK_CLIENT_ID"))
logger.debug("【debug】OAUTH_KEYCLOAK_CLIENT_SECRET的值为: %s", os.getenv("OAUTH_KEYCLOAK_CLIENT_SECRET"))
logger.debug("【debug】OAUTH_KEYCLOAK_NAME的值为: %s", os.getenv("OAUTH_KEYCLOAK_NAME"))
logger.debug("【debug】CHAINLIT_AUTH_SECRET的值为: %s", os.getenv("CHAINLIT_AUTH_SECRET"))
# Log RAGFlow environment variables
logger.debug("【debug】RAGFLOW_API_KEY的值为: %s", os.getenv("RAGFLOW_API_KEY"))
logger.debug("【debug】RAGFLOW_BASE_URL的值为: %s", os.getenv("RAGFLOW_BASE_URL"))
logger.debug("【debug】RAGFLOW_ASSISTANT_NAME的值为: %s", os.getenv("RAGFLOW_ASSISTANT_NAME"))

logger.debug("【debug】IT_ENVIRONMENT的值为: %s", os.getenv("IT_ENVIRONMENT"))

""" @cl.action_callback("转人工")
async def on_action(action: cl.Action):
    # print(action.payload)
    app_user = cl.user_session.get("user")

    # pprint(rocket.me().json())
    # pprint(rocket.chat_post_message('good news everyone!', channel='GENERAL', alias='Farnsworth').json())
    # Get all the messages in the conversation in the OpenAI format
    # print(cl.chat_context.to_openai())
    # 将聊天历史格式化为人类易读的文本
    # 获取当前星期几（0=周一，6=周日）
    current_weekday = datetime.datetime.today().weekday()
    # 定义星期几对应的接收者
    weekday_users = ['bob', 'david', 'alice', 'tom', 'john', 'jerry', 'jerry']
    recipient = weekday_users[current_weekday]
    # 将聊天历史格式化为人类易读的文本
    formatted_history = '\n\n'.join([f'**{msg["role"].capitalize()}: **{msg["content"]}' for msg in cl.chat_context.to_openai()])
    # 在消息前添加用户标识，格式：[USER_ID:xxx]
    post_message_response = rocket.chat_post_message(
        f"[USER_ID:{app_user.identifier}]{formatted_history}",
        room_id=f'@{recipient}',
        alias=app_user.identifier
    )
    print("【debug】post_message_response的值为:", post_message_response.json()) """

@cl.action_callback("转人工")
async def on_action(action: cl.Action):
    # 获取当前用户信息
    app_user = cl.user_session.get("user")
    logger.info(f"【debug】chainlit用户名（邮箱）为: {app_user}")
    if not app_user:
        logger.error("【debug】未获取到当前用户信息")
        await cl.Message(content="无法获取用户信息，转人工失败").send()
        return

    # 从邮箱提取用户名（与Rocket.Chat用户名匹配）
    # username = app_user.identifier.split('@')[0]
    username = app_user.identifier
    # 将硬编码的Rocket.Chat服务器URL替换为环境变量
    server_url = os.getenv("ROCKETCHAT_SERVER_URL")
    
    # 将硬编码的LDAP密码替换为环境变量
    password = os.getenv("LDAP_PASSWORD")
    chainlit_session_id = cl.user_session.get("id")

    try:
        # 动态初始化Rocket.Chat客户端
        logger.info(f"【debug】用户 {username} 尝试登录Rocket.Chat")
        rocket = RocketChat(user=username, password=password, server_url=server_url)

        # 验证登录状态
        me = rocket.me().json()
        if "error" in me:
            logger.error(f"【debug】Rocket.Chat登录失败: {me['error']}")
            await cl.Message(content="转人工失败：身份验证错误").send()
            return

        # 获取星期几对应的客服接收者
        current_weekday = datetime.datetime.today().weekday()
        # Replace hardcoded list
        weekday_users = os.getenv("WEEKDAY_USERS", "bob,david,alice,tom,john,jerry,jerry").split(",")
        recipient = weekday_users[current_weekday]
        logger.info(f"【debug】当前客服接收者: {recipient}")
        """
        # 创建或获取与客服的直接聊天频道
        logger.info(f"【debug】尝试创建/获取与 {recipient} 的聊天频道")
        room_response = rocket.im_create(recipient).json()

        # 处理已有频道情况
        if "error" in room_response and room_response["error"] == "duplicate-channel":
            logger.info(f"【debug】聊天频道已存在，获取现有频道")
            rooms = rocket.im_list().json()
            room = next((r for r in rooms if recipient in [u['username'] for u in r.get('usernames', []) if u['username'] != username]), None)
            if not room:
                raise Exception("未找到现有聊天频道")
            room_id = room['_id']
        elif "error" in room_response:
            raise Exception(f"创建频道失败: {room_response['error']}")
        else:
            room_id = room_response['_id']

        logger.info(f"【debug】成功获取聊天频道ID: {room_id}")
        """


        # 格式化并发送聊天历史
        formatted_history = '\n\n'.join([f'**{msg["role"].capitalize()}: **{msg["content"]}' for msg in cl.chat_context.to_openai()])
        message_content = f"[CHAINLIT_USER_ID:{app_user.identifier}]\n{formatted_history}"

        # 发送消息到Rocket.Chat
        # pprint(rocket.chat_post_message(message_content, channel=f'@{recipient}').json())
        post_response = rocket.chat_post_message(
            message_content,
            channel=f'@{recipient}'
        ).json()
        # logger.info(f"【debug】post_response的值为:, {post_response}")
        post_data = post_response
        # logger.info(f"【debug】post_data的值为:, {post_data}")
        channel_id = post_data.get("message").get("rid")
        room_id = channel_id
        logger.info(f"【debug】channel_id的值为:, {channel_id}")
        logger.info(f"【debug】room_id的值为:, {room_id}")
        if post_data.get("success"):
            logger.info(f"【debug】聊天历史发送成功，消息ID: {post_data.get('message').get('_id')}, 频道ID: {channel_id}")
            await cl.Message(content="已成功转接至人工客服，请等待回复...，若要重新让AI回答，您可以直接新建对话").send()
        else:
            logger.error(f"【debug】消息发送失败: {post_data}")
            await cl.Message(content="转人工失败：消息发送失败").send()

        # 保存会话状态
        cl.user_session.set("is_human_session", True)
        cl.user_session.set("rocket_chat_recipient", recipient)
        cl.user_session.set("rocket_chat_room_id", room_id)
        cl.user_session.set("rocket_chat_client", rocket)

        # 更新Redis会话元数据（存储room_id用于消息路由）
        redis_queue.client.hset(
            f"chainlit_session:{username}:{chainlit_session_id}:metadata",
            mapping={
                "room_id": room_id,
                "status": "human_chat", 
                "support_agent": recipient, 
                "chainlit_session_id": chainlit_session_id, 
                "用户点击转人工的时间": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
        )
        # 打印当前所有消息队列状态（调试用）
        all_queues = redis_queue.get_all_queues()
        # queue_status = {q: redis_queue.qsize(q) for q in all_queues}
        queue_status = {q: redis_queue.qsize(q) for q in all_queues}
        logger.info(f"【debug】当前消息队列状态: {queue_status}")
        logger.info(f"【debug】RedisQueue实例ID: {id(redis_queue)}")
        """
    except RocketChatException as e:
        logger.error(f"【debug】Rocket.Chat API错误: {str(e)}", exc_info=True)
        await cl.Message(content=f"转人工失败: Rocket.Chat通信错误").send()
        """
    except Exception as e:
        logger.error(f"【debug】转人工处理异常: {str(e)}", exc_info=True)
        await cl.Message(content=f"转人工失败: {str(e)}").send()

@cl.on_chat_start
async def on_chat_start():    
    """
    The on_chat_start decorator is used to define a hook that is called when a new chat session is created.
    """
    try:
        # 创建并存储RAGFlow客户端实例
        logger.info(f"【debug】CHAT_ASSISTANT_NAME的值为: {CHAT_ASSISTANT_NAME}")
        rag_client = RAGFlowClient(API_KEY, BASE_URL)
        rag_client.get_chat_id(CHAT_ASSISTANT_NAME)  # 验证助手是否存在
        cl.user_session.set("rag_client", rag_client)
        # 初始化会话状态变量
        cl.user_session.set("is_human_session", False)
        cl.user_session.set("rocket_chat_recipient", None)
        app_user = cl.user_session.get("user")
        # Replace print statements with logger.debug
        # Original: print("【debug】app_user变量的值为:", app_user)
        logger.debug(f"app_user变量的值为: {app_user}")
        """
        # Original: print("【debug】referenced_docs内容: ", json.dumps(referenced_docs, indent=2, ensure_ascii=False))
        logger.debug(f"referenced_docs内容: {json.dumps(referenced_docs, indent=2, ensure_ascii=False)}")
        
        # Original: print("【debug】变量doc_url的值为:", doc_url)
        logger.debug(f"变量doc_url的值为: {doc_url}")
        
        # Original: print("【debug】elements变量的值为:", elements)
        logger.debug(f"elements变量的值为: {elements}")
        """
        """
        # 设置会话映射关系
        session_id = cl.user_session.get("id")
        # 提取邮箱中的用户名部分作为会话映射键，与Rocket.Chat用户名匹配
        rocket_username = app_user.identifier
        # logger.info(f"【debug】提取邮箱用户名作为会话键: {rocket_username} (原始邮箱: {app_user.identifier})，会话ID: {session_id}")
        session_utils.set_chainlit_session_id(rocket_username, session_id)
        logger.info(f"【debug】已设置会话映射: {rocket_username} -> {session_id}")
        
        session_id = cl.user_session.get("id")
        async with message_queues_lock:
            message_queues[session_id] = asyncio.Queue()
            # 打印当前所有消息队列状态
            queue_status = {k: v.qsize() for k, v in message_queues.items()}
            logger.info(f"【debug】消息队列初始化状态: {queue_status}")
        logger.info(f"【debug】为会话 {session_id} 创建消息队列")
        """
        # 将会话ID与用户信息存入Redis，便于追踪管理
        session_id = cl.user_session.get("id")
        user_info = cl.user_session.get("user")
        user_id = user_info.identifier if user_info else "anonymous"
        redis_queue.client.hset(
            f"chainlit_session:{app_user.identifier}:{session_id}:metadata",
            mapping={
                "user_id": user_id,
                "mail": app_user.identifier,
                "chainlit_session_id": session_id,
                "created_at": datetime.datetime.now().isoformat(),
                "status": "active"
            }
        )
        # 设置会话过期时间（24小时）
        redis_queue.client.expire(f"chainlit_session:{user_id}:{session_id}:metadata", 86400)

        
        # 启动消息处理任务并保存引用
        message_task = asyncio.create_task(process_messages(session_id))
        cl.user_session.set("message_task", message_task)

    except Exception as e:
        await cl.Message(content=f"初始化失败: {str(e)}").send()

""" async def process_messages(session_id: str):
    queue_name = f"session:{session_id}"
    while True:
        try:
            # 使用线程池执行同步Redis操作，避免阻塞事件循环
            # 增加调试日志并调整超时时间
            logger.info(f"【debug】尝试从Redis队列 {queue_name} 读取消息")
            message = await asyncio.to_thread(
                redis_queue.dequeue,
                queue_name,
                block=True,
                timeout=30  # 延长超时时间以确保能接收到消息
            )
            if message is not None:
                logger.info(f"【debug】从队列 {queue_name} 读取到消息: {message[:50]}")
            else:
                logger.info(f"【debug】队列 {queue_name} 超时未读取到消息")
            if message is None:
                continue
            
            # 处理消息并发送到Chainlit
            await cl.Message(content=message).send()
        except asyncio.CancelledError:
            logger.info(f"【debug】会话 {session_id} 消息处理任务已取消")
            break
        except Exception as e:
            logger.error(f"Error processing message for session {session_id}: {str(e)}", exc_info=True)
            break
    """

async def process_messages(session_id: str):
    """
    这个函数主要负责从Redis队列中读取消息并发送到Chainlit。
    参数session_id指的是chainlit中的会话ID。
    它会根据会话ID动态获取对应的消息队列名称，并在队列中读取消息。
    如果读取到消息，会将其发送到Chainlit进行展示；如果读取超时或队列空，会进行适当的日志记录。
    这个函数被on_chat_start调用。
    """

    while True:
        try:
            # 动态获取当前room_id（支持转人工后更新）
            # current_room_id = redis_queue.client.hget(metadata_key, "room_id") or room_id
            # if current_room_id != room_id:
            #     logger.info(f"【debug】房间ID变更: {room_id} -> {current_room_id}")
            #     room_id = current_room_id
            #     queue_name = f"session:{room_id}:metadata"
            # if not room_id:
            #     # 未进入人工会话，使用默认队列
                
            #     queue_name = f"session:{session_id}"
            #     logger.info(f"【debug】未进入人工会话，使用默认队列: {queue_name}")
            #     await asyncio.sleep(5)  # 降低空轮询频率
            #     continue
               # 从Redis获取room_id
            metadata_queue_name = f"chainlit_session:{cl.user_session.get("user").identifier}:{session_id}:metadata"
            # logger.info(f"【debug】尝试从Redis获取会话元数据: {metadata_queue_name}")
            metadata = redis_queue.client.hgetall(metadata_queue_name)
            # logger.info(f"【debug】获取到的会话元数据: {metadata}")


            # Get room_id with proper error handling
            # room_id = metadata.get("room_id")
            # logger.info(f"【debug】从会话元数据中获取room_id: {room_id}")
            room_id = cl.user_session.get("rocket_chat_room_id")
            logger.info(f"【debug】从用户会话中获取rocket_chat_room_id: {room_id}")
            if room_id is None:
                logger.warning(f"【警告】会话 {session_id} 的元数据中未找到 room_id这个key，说明此用户没有选择人工客服。使用默认值")
                room_id = "不存在room_id，此用户没有选择人工客服"
            logger.info(f"【debug】消息处理初始化 - 会话ID: {session_id}, 房间ID: {room_id}")

            if room_id == "不存在room_id，此用户没有选择人工客服":
                # 未进入人工会话，使用默认队列
                logger.info(f"【debug】此用户 {cl.user_session.get("user").identifier}---{session_id} 没有选择人工客服，未进入人工会话，不读取消息")
                await asyncio.sleep(5)  # 降低空轮询频率
                continue
            else:
                queue_name = f"{os.getenv("IT_ENVIRONMENT")}:rocket.chat_session:{cl.user_session.get("rocket_chat_recipient")}:{room_id}:messages_queue"
                logging.info(f"【debug】此用户{cl.user_session.get("user").identifier}--- {session_id} 选择了人工客服，使用队列: {queue_name}")

            logger.info(f"【debug】尝试从Redis队列 {queue_name} 读取消息")

            # message = await asyncio.to_thread(
            #     redis_queue.dequeue,
            #     queue_name,
            #     block=True,
            #     timeout=30
            # )

            data = await asyncio.to_thread(
                redis_queue.stream_peek_latest,
                queue_name,
                block=True,
                timeout=30
            )
            message = data['data']['data']

            if message is not None:
                logger.info(f"【debug】从队列 {queue_name} 读取到消息: {message}")
                await cl.Message(content=message).send()
                logger.info(f"【debug】消息已发送到Chainlit用户：{cl.user_session.get("user").identifier}，人工客服：{cl.user_session.get("rocket_chat_recipient")} 房间ID为：{room_id}，消息内容为：{message}")

            else:
                logger.info(f"【debug】队列 {queue_name} 超时未读取到消息")

        except asyncio.CancelledError:
            logger.info(f"【debug】会话 {session_id} 消息处理任务已取消")
            break
        except Exception as e:
            logger.error(f"Error processing message for session {session_id}: {str(e)}", exc_info=True)
            break

@cl.set_starters
async def set_starters():
    return [
        cl.Starter(
            label="AI助手使用手册",
            message="AI助手使用手册.",
            icon="http://10.64.160.146/arrow-right-circle-line.svg",
        ),
        cl.Starter(
            label="如何重置密码",
            message="如何重置密码.",
            icon="http://10.64.160.146/arrow-right-circle-line.svg",
        ),
        cl.Starter(
            label="公司食堂开餐时间",
            message="公司食堂开餐时间.",
            icon="http://10.64.160.146/arrow-right-circle-line.svg",
        ),
        cl.Starter(
            label="怎么查打卡时间",
            message="怎么查打卡时间.",
            icon="http://10.64.160.146/arrow-right-circle-line.svg",
        )
    ]

@cl.on_message
async def on_message(message: cl.Message):
    """
    The on_message decorator is used to define a hook that is called when a new message is received from the user.
    这个decorator主要是用来决定chainlit用户发送的消息是要发送给rocke.chat人工客服还是后端的ragflow
    """
    rag_client: RAGFlowClient = cl.user_session.get("rag_client")
    is_human_session = cl.user_session.get("is_human_session", False)
    rocket_chat_recipient = cl.user_session.get("rocket_chat_recipient")

    if not rag_client:
        await cl.Message(content="客户端未初始化，请刷新页面重试").send()
        return

    try:
        if is_human_session and rocket_chat_recipient:
            # 人工会话，直接发送到Rocket.Chat
            app_user = cl.user_session.get("user")
            # 添加用户标识和人工会话标记
            formatted_message = f"[CHAINLIT_USER_ID:{app_user.identifier}][HUMAN_SESSION]\n{message.content}"
            # Retrieve Rocket.Chat client from user session
            current_rocket = cl.user_session.get("rocket_chat_client")
            logger.info(f"【debug】当前Rocket.Chat客户端: {current_rocket}")
            if not current_rocket:
                logger.error("【debug】Rocket.Chat client not found in user session")
                await cl.Message(content="转人工会话已过期，请重新发起转人工请求").send()
                return
            logger.info(f"【debug】发送消息到Rocket.Chat房间（客服名称）: {rocket_chat_recipient}")
            current_rocket.chat_post_message(
                formatted_message,
                room_id=f'@{rocket_chat_recipient}',
            )
            # 向用户确认消息已发送给人工代理
            await cl.Message(content=f"已发送给人工客服：{rocket_chat_recipient}\n消息内容为： {message.content}").send()
            logger.info(f"【debug】人工会话消息发送: {formatted_message}")
        else:
            # AI会话，使用RAGFlow处理
            msg = await cl.Message(content="").send()
            user_identifier = cl.user_session.get("user").identifier
            await rag_client.stream_chat_completion(message.content, msg)

    except Exception as e:
        error_msg = f"处理请求时出错: {str(e)}"
        await cl.Message(content=error_msg).send()
        logger.error(f"【debug】消息处理错误: {error_msg}", exc_info=True)

@cl.on_chat_end
async def on_chat_end():
    chainlit_session_id = cl.user_session.get("id")
    if not chainlit_session_id:
        return
    
    # 获取消息处理任务并取消
    message_task = cl.user_session.get("message_task")
    if message_task:
        message_task.cancel()
        try:
            await message_task
        except asyncio.CancelledError:
            pass
    
        # 清理Redis队列
        queue_name = f"chainlit_session:{cl.user_session.get("user").identifier}:{chainlit_session_id}:metadata"
        redis_queue.clear(queue_name)
        logger.info(f"chainlit Session {chainlit_session_id} ended. Redis queue {queue_name} cleared.")
    else:
        logger.info(f"【debug】会话 {chainlit_session_id} 结束，消息队列不存在")
