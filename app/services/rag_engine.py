# app/services/rag_engine.py
import qdrant_client
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.core import VectorStoreIndex, StorageContext
from app.core.config import get_settings
from app.services.llm_factory import ModelFactory
from functools import lru_cache # 👈 导入缓存装饰器

settings = get_settings()
@lru_cache() # 👈 加上这个装饰器，确保全局只初始化一次 Index 和 连接
def get_index():
    """获取全局唯一的 Index 对象"""
    # 1. 连接客户端
    # 建立双客户端：同步用于普通操作，异步用于高并发检索
    print("🔌 连接 Qdrant ...")
    client = qdrant_client.QdrantClient(url=settings.QDRANT_URL)
    aclient = qdrant_client.AsyncQdrantClient(url=settings.QDRANT_URL)

    # 2. 定义存储后端
    vector_store = QdrantVectorStore(
        client=client,
        aclient=aclient,
        collection_name=settings.COLLECTION_NAME,
        enable_hybrid=True, # 开启混合检索 (关键词+向量)
        # batch_size=20,    # 如果报错内存不足，可以调小这个
    )
    
    # 3. 组装上下文
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    print("✅ Qdrant 连接成功")
    
    # 4. 返回 Index (注意：这里必须传入 embed_model，否则它会去下 OpenAI 的)
    return VectorStoreIndex.from_vector_store(
        vector_store=vector_store,
        embed_model=ModelFactory.get_embed_model() # 调用上面的工厂
    )
