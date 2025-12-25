# evaluation/config.py
# ⚙️ [配置] 统一管理 API Key、阈值、模型名称
import os
from openai import OpenAI
from langfuse import Langfuse
from dotenv import load_dotenv

# 加载 .env 文件中的环境变量
load_dotenv()

# --- Langfuse 配置 ---
langfuse = Langfuse()

# --- DeepSeek 配置 ---
# DeepSeek 完美兼容 OpenAI SDK 格式
deepseek_client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url=os.getenv("DEEPSEEK_BASE_URL") # 注意：SDK 通常会自动补全 /v1
)

# 定义模型名称常量，方便后续统一修改
MODEL_DEEPSEEK_CHAT = "deepseek-chat"
MODEL_DEEPSEEK_R1 = "deepseek-reasoner"