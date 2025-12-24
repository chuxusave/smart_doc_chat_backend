# app/core/config.py
import os
from dotenv import load_dotenv
from functools import lru_cache
from urllib.parse import quote_plus  # 👈 必须导入这个，用于处理密码里的特殊字符
from pydantic_settings import BaseSettings
load_dotenv()
class Settings(BaseSettings):
    # --- 1. 基础配置 ---
    DASHSCOPE_API_KEY: str = os.getenv("DASHSCOPE_API_KEY")
    DASHSCOPE_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    HF_ENDPOINT: str = "https://hf-mirror.com"
    
    # --- 2. 模型路径 ---
    EMBEDDING_MODEL_PATH: str = "./models/bge-large-zh-v1.5/BAAI/bge-large-zh-v1___5"
    RERANK_MODEL_PATH: str = "./models/bge-reranker-base/BAAI/bge-reranker-base"
    
    # --- 3. Qdrant 配置 ---
    QDRANT_URL: str = "http://localhost:6333"
    COLLECTION_NAME: str = "enterprise_knowledge_base_hybrid_v1"

    # --- 4. 数据库原子配置 (从 .env 读取) ---
    # 这里我们把连接串拆开，这样更安全，也更容易处理转义
    MYSQL_USER: str = "root"
    MYSQL_PASSWORD: str       # 必填，对应 .env 里的 MYSQL_PASSWORD
    MYSQL_HOST: str = "localhost"
    MYSQL_PORT: int = 3306
    MYSQL_DB: str = "rag_db"

    # --- 5. 动态生成数据库 URL (核心逻辑) ---
    @property
    def SQLALCHEMY_DATABASE_URL(self) -> str:
        """
        自动将上面的原子配置拼装成 SQLAlchemy 需要的连接串。
        同时自动对密码进行 URL 编码，防止特殊字符报错。
        """
        if not self.MYSQL_PASSWORD:
            raise ValueError("❌ 错误: 环境变量 MYSQL_PASSWORD 未设置！")
            
        encoded_password = quote_plus(self.MYSQL_PASSWORD)
        
        return (
            f"mysql+aiomysql://"
            f"{self.MYSQL_USER}:{encoded_password}@"
            f"{self.MYSQL_HOST}:{self.MYSQL_PORT}/"
            f"{self.MYSQL_DB}"
        )
    
    

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        # 忽略 .env 中多余的变量，防止报错
        extra = "ignore"

@lru_cache()
def get_settings():
    return Settings()