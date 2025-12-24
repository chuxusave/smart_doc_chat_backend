# app/services/file_service.py
import os
import shutil
import uuid
from fastapi import UploadFile, BackgroundTasks
from llama_index.core import SimpleDirectoryReader, VectorStoreIndex
from llama_index.core.node_parser import SentenceSplitter

from app.core.redis import redis_manager
from app.services.rag_engine import get_index

# 获取 Redis 客户端
r = redis_manager.get_client()

def process_file_task(task_id: str, temp_filename: str, original_filename: str):
    """后台任务：处理文件并构建索引"""
    try:
        # 1. 更新状态：处理中
        r.hset(f"task:{task_id}", mapping={
            "status": "processing", 
            "message": "正在解析文档..."
        })
        
        # 2. 读取文件
        new_documents = SimpleDirectoryReader(input_files=[temp_filename]).load_data()
        for doc in new_documents:
            doc.metadata["file_name"] = original_filename
            
        r.hset(f"task:{task_id}", mapping={"message": "正在向量化..."})
        
        # 3. 获取全局 Index 并插入数据
        # 注意：这里我们调用 get_index() 获取已初始化的 Qdrant 连接
        index = get_index() 
        
        # 4. 插入文档 (LlamaIndex 会自动处理 Embedding 和存储)
        # 注意：VectorStoreIndex.from_documents 默认会创建新 index，
        # 如果要增量更新，应该使用 index.insert_nodes 或类似的 API。
        # 这里为了兼容旧逻辑，我们使用 insert 逻辑：
        pipeline = SentenceSplitter(chunk_size=512, chunk_overlap=50)
        nodes = pipeline.get_nodes_from_documents(new_documents)
        index.insert_nodes(nodes)

        # 5. 更新状态：完成
        r.hset(f"task:{task_id}", mapping={
            "status": "completed", 
            "message": "索引构建完成"
        })
        print(f"✅ 任务 {task_id} 完成")

    except Exception as e:
        r.hset(f"task:{task_id}", mapping={
            "status": "failed", 
            "message": str(e)
        })
        print(f"❌ 任务 {task_id} 失败: {e}")
    finally:
        # 清理临时文件
        if os.path.exists(temp_filename):
            os.remove(temp_filename)
        r.expire(f"task:{task_id}", 3600)

async def handle_file_upload(file: UploadFile, background_tasks: BackgroundTasks):
    """Service 层入口"""
    task_id = str(uuid.uuid4())
    temp_filename = f"temp_{file.filename}"
    
    # 保存临时文件
    with open(temp_filename, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # 初始化 Redis 状态
    r.hset(f"task:{task_id}", mapping={
        "status": "pending", 
        "message": "已加入队列",
        "filename": file.filename
    })

    # 添加后台任务
    background_tasks.add_task(process_file_task, task_id, temp_filename, file.filename)
    
    return task_id