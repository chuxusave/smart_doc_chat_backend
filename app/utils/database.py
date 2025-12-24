# app/core/database.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import get_settings # 👈 引入配置中心

# 1. 获取配置实例
settings = get_settings()

# 2. 创建异步引擎
# ✅ 现在 settings.SQLALCHEMY_DATABASE_URL 是通过 @property 动态计算出来的安全链接
engine = create_async_engine(
    settings.SQLALCHEMY_DATABASE_URL,
    echo=True,  # 开发环境 True，生产环境改为 False
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True # 💡 建议加上：自动检测断连并重连（解决 MySQL 8小时断开问题）
)

# 3. 创建会话工厂
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# 4. 定义模型基类
Base = declarative_base()

# 5. 依赖注入函数
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()