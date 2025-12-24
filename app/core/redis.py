# app/core/redis.py
# Redis 连接 (用于任务队列 & 会话历史)
import redis
import json
from typing import List, Dict
import os
from llama_index.core.llms import ChatMessage

# 简单封装，生产环境建议把 host/port 放入 config.py
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_PASSWORD = "langfuse"

class RedisManager:
    def __init__(self):
        self.client = redis.Redis(
            host=REDIS_HOST, 
            port=REDIS_PORT,
            password=REDIS_PASSWORD,
            db=0, 
            decode_responses=True # decode_responses=True，自动解码响应结果。不用每次取数据都手动 decode 一下
        )
        self.ttl = 3600  # 1小时过期

    def get_client(self):
        return self.client

    def get_chat_history(self, session_id: str) -> List[Dict]:
        key = f"chat_session:{session_id}"
        raw = self.client.get(key)
        if raw:
            try:
                return json.loads(raw)
            except:
                return []
        return []
    def save_chat_history(self, session_id: str, history: List[Dict]):
        key = f"chat_session:{session_id}"
        self.client.setex(
            name=key,
            time=self.ttl,
            value=json.dumps(history, ensure_ascii=False)
        )

# 单例模式
redis_manager = RedisManager()



# # 初始化 Redis (建议放在全局或单独的 config 文件)
# def get_chat_history(x_session_id: str = Header(..., alias="X-Session-ID")) -> List[ChatMessage]:
#     """
#     依赖注入函数：根据 Header 中的 Session ID 从 Redis 获取历史记录
#     """
#     redis_key = f"chat_session:{x_session_id}"
#     raw_data = redis_client.get(redis_key)
    
#     if raw_data:
#         try:
#             # 反序列化 JSON -> List[Dict] -> List[ChatMessage]
#             history_data = json.loads(raw_data)
#             return [ChatMessage(**msg) for msg in history_data]
#         except Exception as e:
#             print(f"⚠️ Redis 数据解析失败: {e}")
#             return []
#     return [] # 如果没有记录，返回空列表
# def save_chat_history(session_id: str, history: List[ChatMessage]):
#     """
#     辅助函数：将更新后的历史存回 Redis
#     """
#     redis_key = f"chat_session:{session_id}"
#     # 序列化 List[ChatMessage] -> List[Dict]
#     # 注意：LlamaIndex 的 ChatMessage 对象通常有 .dict() 或 .model_dump() 方法
#     history_data = [msg.dict() for msg in history]
    
#     redis_client.setex(
#         name=redis_key,
#         time=SESSION_EXPIRE_TIME,
#         value=json.dumps(history_data, ensure_ascii=False)
#     )
