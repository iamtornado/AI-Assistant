from fastapi import FastAPI, Request, HTTPException
import uvicorn
import json
import os
import chainlit as cl
from chainlit.utils import mount_chainlit

# import session_utils
# from chainlit_ragflow_streaming import message_queues, message_queues_lock

from message_queue import RedisQueue
from pydantic import BaseModel

class MessageRequest(BaseModel):
    session_id: str
    message: str

# 配置日志
# Replace current logging setup with:
from logger_config import setup_logger
logger = setup_logger(__name__)

app = FastAPI()
redis_queue = RedisQueue()
# 存储会话映射: Rocket.Chat用户ID -> Chainlit会话ID
session_mapping = {}

@app.post("/rocketchat-webhook")
async def rocketchat_webhook(request: Request):
    """
    处理Rocket.Chat发送过来的webhook消息。

    :param request: 包含Rocket.Chat消息的请求对象
    :type request: Request
    :return: 处理结果
    :rtype: dict
    """
    try:
        data = await request.json()
    except JSONDecodeError:
        logger.error("Invalid JSON format in request")
        raise HTTPException(status_code=400, detail="Invalid JSON format")
    except KeyError as e:
        logger.error(f"Missing required field: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Missing required field: {str(e)}")
    except redis.ConnectionError:
        logger.error("Redis connection failed")
        raise HTTPException(status_code=503, detail="Service temporarily unavailable")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="An unexpected error occurred")
        
    logger.info(f"【debug】收到Rocket.Chat webhook: {json.dumps(data, ensure_ascii=False)}")

    # 验证webhook令牌（从body中获取token）
    token = data.get("token")
    expected_token = os.getenv("ROCKETCHAT_WEBHOOK_TOKEN")
    if not token:
        logger.warning("【debug】Webhook请求中未找到token")
        raise HTTPException(status_code=400, detail="Token not found in request body")
    if token != expected_token:
        logger.warning(f"【debug】Webhook令牌验证失败: 收到{token}, 预期{expected_token}")
        raise HTTPException(status_code=403, detail="Invalid token")

    # 提取消息内容和发送者（根据实际JSON结构调整）
    content = data.get("text", "")
    sender_username = data.get("user_name", "")
    room_id = data.get("channel_id", "")
    message_id = data.get("message_id", "")
    timestamp = data.get("timestamp", "")
    # 添加调试日志
    logger.info(f"【debug】提取消息: sender（Support agent）={sender_username}, content={content[:50]}, room_id={room_id}, message_id={message_id}, timestamp={timestamp}")

    # 验证Redis连接并检查队列
    try:
        # 检查Redis连接
        redis_queue.client.ping()
        logger.info("【debug】Redis连接正常")
        # 打印Redis实例基本信息
        logger.debug(f"【debug】Redis连接信息 - IP: {redis_queue.host}, 端口: {redis_queue.port}, 数据库索引: {redis_queue.db}")

    except Exception as e:
        logger.error(f"【debug】Redis连接失败: {str(e)}")
        raise HTTPException(status_code=500, detail="Redis connection failed")
        
    # 过滤掉系统消息和自动转发的消息
    if "[CHAINLIT_USER_ID:" in content or "[HUMAN_SESSION]" in content:
        logger.info(f"【debug】过滤掉自动转发的消息: {content}")
        return {"status": "ignored"}

    agent_reply = f"**人工客服 {sender_username}:\n {content}"
    # 消息队列名称
    queue_name = f"{os.getenv("IT_ENVIRONMENT")}:rocket.chat_session:{sender_username}:{room_id}:messages_queue"
    # 入队前检查队列是否存在
    # queue_type = redis_queue.client.type(queue_name)
    # if queue_type != 'list':
    #     logger.warning(f"【debug】队列 {queue_name} 不是列表类型，实际类型: {queue_type}")
    #     raise HTTPException(status_code=500, detail=f"Queue {queue_name} is not a list type")
    if redis_queue.qsize(queue_name) == 0 and queue_name not in redis_queue.get_all_queues(): 
        logger.warning(f"【debug】队列 {queue_name} 不存在，将创建新队列")
    # 消息入队，同时设置队列仅保留最近1000条消息，避免内存溢出
    redis_queue.enqueue_stream(queue_name, agent_reply)
    # 入队后验证
    new_size = redis_queue.qsize(queue_name)
    logger.info(f"【debug】消息入队成功，队列 {queue_name} 当前大小: {new_size}, 消息内容: {agent_reply}")
    return {"status": "success"}
    # logger.info(f"【debug】消息入队成功，队列名称： {queue_name} 当前大小: {redis_queue.qsize(queue_name)}")

    """
    # 查询会话映射前添加详细日志
    logger.info(f"【debug】准备查询会话映射: sender_username={sender_username}")
    # chainlit_session_id = session_utils.get_chainlit_session_id(sender_username)
    # all_mappings = session_utils.get_all_session_mappings()
    # 从Redis的session_mapping哈希表中获取会话ID
    chainlit_session_id = redis_queue.client.hget("session_mapping", sender_username)
    # 获取所有会话映射
    all_mappings = redis_queue.client.hgetall("session_mapping")
    logger.info(f"【debug】查询会话映射结果: username={sender_username}, session_id={chainlit_session_id}, 当前映射={all_mappings}")
    # 获取并记录当前所有会话映射状态
    
    logger.info(f"【debug】当前会话映射: {all_mappings}")
    """
    """
    if not chainlit_session_id:
        # 打印当前所有消息队列状态以辅助调试
        # queue_status = {k: v.qsize() for k, v in message_queues.items()}
        queue_status = {q: redis_queue.qsize(q) for q in redis_queue.get_all_queues()}
        logger.info(f"【debug】未找到会话，当前消息队列状态: {queue_status}")
        logger.warning(f"【debug】未找到对应的Chainlit会话: {sender_username}")
        return {"status": "session_not_found"}
    """

    """
    queue_name = f"session:{chainlit_session_id}"
    logger.info(f"【debug】准备入队消息到队列 {queue_name}, 会话ID: {chainlit_session_id}")
    """

# 挂载Chainlit应用
mount_chainlit(app=app, target="chainlit_ragflow_streaming.py", path="/")

"""
@app.post("/send-message")
async def send_message(data: MessageRequest):

    # 接收Rocket.Chat的webhook消息，处理并入队。

    # :param data: 包含会话ID和消息内容的请求体
    # :type data: MessageRequest
    # :return: 入队状态
    # :rtype: dict

    try:
        session_id = data.session_id
        message = data.message
        
        # 打印当前所有消息队列状态（调试用）
        all_queues = redis_queue.get_all_queues()
        # queue_status = {q: redis_queue.qsize(q) for q in all_queues}
        queue_status = {q: redis_queue.qsize(q) for q in redis_queue.get_all_queues()}
        logger.info(f"【debug】当前消息队列状态: {queue_status}")
        logger.info(f"【debug】RedisQueue实例ID: {id(redis_queue)}")
        
        # 检查会话队列(消息队列：真正存放消息的队列)是否存在
        queue_name = f"session:{session_id}"
        if redis_queue.qsize(queue_name) == 0 and queue_name not in all_queues:
            logger.warning(f"会话 {session_id} 的消息队列不存在")
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
        
        # 将消息放入对应会话的队列
        redis_queue.enqueue(queue_name, message)
        logger.info(f"【debug】消息已放入会话 {session_id} 的队列，当前队列大小: {redis_queue.qsize(queue_name)}")
        
        return {"status": "success", "message": "Message added to queue"}
    except Exception as e:
        logger.error(f"处理消息时出错: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing message: {str(e)}")
"""

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
