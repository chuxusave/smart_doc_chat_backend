# models.py
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON
from sqlalchemy.sql import func
from app.utils.database import Base

class Feedback(Base):
    __tablename__ = "feedbacks" # 数据库里的表名

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    session_id = Column(String(100), index=True) # 加索引，方便按用户查询
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    rating = Column(Integer, default=0) # 1=赞, 0=踩
    tags = Column(String(255), nullable=True) # 存成 "冗长,错误" 这样的字符串
    comment = Column(Text, nullable=True)
    
    # 自动记录创建时间
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# 未来你可以加 User 表
# class User(Base):
#     __tablename__ = "users"
#     ...