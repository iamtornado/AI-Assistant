import os
import redis
import time

from typing import Optional, Any
# Initialize logger for RedisQueue
from logger_config import setup_logger
logger = setup_logger(__name__)


class RedisQueue:
    def __init__(self, host: str = None, port: int = None, db: int = None, password: str = None):
        self.host = host or os.getenv("REDIS_HOST", "localhost")
        self.port = port or int(os.getenv("REDIS_PORT", 6379))
        # Get environment and set appropriate Redis DB index
        environment = os.getenv("IT_ENVIRONMENT", "dev")
        if environment == "dev":
            self.db = int(os.getenv("REDIS_DB_INDEX_DEV", 0))
        elif environment == "test":
            self.db = int(os.getenv("REDIS_DB_INDEX_TEST", 1))
        else:
            self.db = 0  # Default to dev DB if environment not specified
            logger.warning(f"Unknown environment {environment}, defaulting to development database (index 0)")
        self.password = password or os.getenv("REDIS_PASSWORD")
        # Load database index from environment configuration
        self.client = redis.Redis(
            host=self.host,
            port=self.port,
            db=self.db,
            password=self.password,
            decode_responses=True
        )
        try:
            self.client.ping()
        except redis.ConnectionError:
            raise Exception("Could not connect to Redis server. Please ensure Redis is running.")
    # async def __aenter__(self):
    #     self.client = await aioredis.from_url(self.connection_string)
    #     return self
    
    # async def __aexit__(self, exc_type, exc, tb):
    #     await self.client.close()
        
    def enqueue(self, queue_name: str, item: Any) -> int:
        """Add an item to the end of the queue"""
        return self.client.rpush(queue_name, item)

    def dequeue(self, queue_name: str, block: bool = True, timeout: int = 0) -> Optional[Any]:
        """Remove and return an item from the front of the queue"""
        if block:
            # Blocking mode: waits for item with timeout
            item = self.client.blpop(queue_name, timeout=timeout)
            logger.debug(f"Blocking dequeue from {queue_name}: {item}")
            return item[1] if item else None
        else:
            # Non-blocking mode: returns immediately
            logger.debug(f"Non-blocking dequeue from {queue_name}: {item}")
            return self.client.lpop(queue_name)

    def enqueue_stream(self, stream_name: str, item: any, maxlen: int = 1000) -> str:
        """
        Add an item to a Redis Stream with automatic trimming to avoid memory overuse.

        Args:
            stream_name: Name of the stream (queue name).
            item: A dictionary representing the fields of the message.
            maxlen: Maximum number of messages to retain in the stream.

        Returns:
            The ID of the added message.
        """
        try:
            return self.client.xadd(
                stream_name,
                fields={"data": str(item)},
                maxlen=maxlen,
                approximate=True
            )
        except redis.RedisError as e:
            logger.error(f"Failed to enqueue to stream '{stream_name}': {e}")
            return ""

    def stream_peek_latest(self, stream_name: str, block: bool = True, timeout: int = 0) -> Optional[dict]:
        """
        Blocking or non-blocking peek of the latest item from a Redis Stream without deleting it.
        Mimics the behavior of dequeue but doesn't remove the item.
        
        Args:
            stream_name: Name of the Redis stream (acts like a queue).
            block: Whether to block until a new item is available.
            timeout: Maximum blocking time in seconds (only if block=True).

        Returns:
            A dict with 'id' and 'data' keys if message exists, else None.
        """
        try:
            # Always read from the latest known ID to avoid re-reading
            last_id = "$"  # "$" = last inserted ID, means "only read new items after now"
            block_ms = int(timeout * 1000) if block else 0

            response = self.client.xread({stream_name: last_id}, count=1, block=block_ms)

            if not response:
                return None

            _, messages = response[0]
            message_id, message_data = messages[0]
            return {"id": message_id, "data": message_data}
        except redis.RedisError as e:
            logger.error(f"Failed to peek latest from stream '{stream_name}': {e}")
            return None

    def qsize(self, queue_name: str) -> int:
        """
        Return the size of the queue, supporting both List and Stream types"
        """
        try:
            # Get the type of the Redis key
            key_type = self.client.type(queue_name)
            
            if key_type == 'list':
                return self.client.llen(queue_name)
            elif key_type == 'stream':
                return self.client.xlen(queue_name)
            else:
                logger.warning(f"Unsupported queue type: {key_type} for queue {queue_name}")
                return 0
        except redis.RedisError as e:
            logger.error(f"Failed to get queue size for {queue_name}: {e}")
            return 0

    def clear(self, queue_name: str) -> int:
        """Clear all items from the queue"""
        return self.client.delete(queue_name)

    def get_all_queues(self, prefix: str = "session:") -> list:
        """Get all queue names with the given prefix that are lists"""
        keys = self.client.keys(f"{prefix}*")
        list_keys = []
        for key in keys:
            # 只返回列表类型的键
            if self.client.type(key) == 'list':
                list_keys.append(key)
        return list_keys

