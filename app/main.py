# app/main.py
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from app.api.routers import router as api_router
from app.utils.database import engine, Base
from app.core.config import get_settings




# 设置环境变量 (放在最前)
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 服务正在启动...")
    try:
        # 1. 自动创建 MySQL 表结构 (如果不需要迁移工具的话)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("✅ MySQL 表结构已同步")
        
        # 2. 这里可以预加载模型 (可选，因为 Factory 是懒加载的)
        # ModelFactory.get_embed_model()
        
    except Exception as e:
        print(f"❌ 启动初始化失败: {e}")
    
    yield
    
    print("🛑 服务正在关闭...")

app = FastAPI(title="RAG Intelligent Assistant", lifespan=lifespan)

# CORS 设置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 异常处理
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    return JSONResponse(status_code=422, content={"detail": exc.errors()})

# 注册路由
app.include_router(api_router, prefix="/api")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)