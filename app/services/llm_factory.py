# app/services/llm_factory.py
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.postprocessor.flag_embedding_reranker import FlagEmbeddingReranker
from langchain_openai import ChatOpenAI
from app.core.config import get_settings
import torch

# 使用 单例模式 (Singleton) 或 lru_cache 来确保模型只加载一次，而不是每次请求都加载。

settings = get_settings()

class ModelFactory:
    _embed_model = None
    _reranker = None
    _llm = None

    @classmethod
    def get_embed_model(cls):
        if cls._embed_model is None:
            print(f"🔄 正在加载 Embedding: {settings.EMBEDDING_MODEL_PATH} ...")
            cls._embed_model = HuggingFaceEmbedding(
                model_name=settings.EMBEDDING_MODEL_PATH,
                device="cuda" if torch.cuda.is_available() else "cpu", # 有显卡用显卡，没显卡用 CPU
                trust_remote_code=True # 允许执行模型里的自定义 Python 代码
            )
        return cls._embed_model

    @classmethod
    def get_reranker(cls):
        if cls._reranker is None:
            print("🔄 正在加载 Reranker ...")
            cls._reranker = FlagEmbeddingReranker(
                top_n=3, # 最终只选出 3 个最好的给大模型看，这能极大减少大模型的幻觉，并节省 Token 费用。
                model=settings.RERANK_MODEL_PATH,
                use_fp16=False # 是否开启半精度加速（CPU 必须关，GPU 可以开以省显存）
            )
        return cls._reranker

    @classmethod
    def get_llm(cls):
        if cls._llm is None:
            cls._llm = ChatOpenAI(
                openai_api_base=settings.DASHSCOPE_BASE_URL,
                openai_api_key=settings.DASHSCOPE_API_KEY,
                model="qwen-max", # 通义千问 Max（阿里的最强模型）
                temperature=0, # 必须为 0，保证工具调用稳定
                streaming=True # 流式输出（像打字机一样一个字一个字蹦）
            )
        return cls._llm