# app/services/file_service.py
import os
import shutil
import uuid
from fastapi import UploadFile, BackgroundTasks
from llama_index.core import SimpleDirectoryReader, VectorStoreIndex
from llama_index.core.node_parser import SentenceSplitter

from app.core.redis import redis_manager
from app.services.rag_engine import get_index
from app.core.config import get_settings

# 获取 Redis 客户端
r = redis_manager.get_client()
settings = get_settings()

def process_file_task(task_id: str, file_path: str, original_filename: str,file_url: str):
    """后台任务：处理文件并构建索引"""
    try:
        # 1. 更新状态：处理中
        r.hset(f"task:{task_id}", mapping={
            "status": "processing", 
            "message": "正在解析文档..."
        })
        
       # 读取文件 (从持久化路径读取)
        new_documents = SimpleDirectoryReader(input_files=[file_path]).load_data()
        for doc in new_documents:
            doc.metadata["file_name"] = original_filename
            # 存入下载链接和类型
            doc.metadata["source_url"] = file_url
            doc.metadata["source_type"] = "file_download" # 标记这是可下载文件
            # 也可以存页码 (LlamaIndex 默认会有 page_label，但为了保险可以手动检查)
            # if "page_label" not in doc.metadata: doc.metadata["page_label"] = "1"
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
        print(f"✅ 任务 {task_id} 完成，文件已归档: {file_path}")

    except Exception as e:
        r.hset(f"task:{task_id}", mapping={
            "status": "failed", 
            "message": str(e)
        })
        print(f"❌ 任务 {task_id} 失败: {e}")
    finally:
        
        pass 
        r.expire(f"task:{task_id}", 3600)

async def handle_file_upload(file: UploadFile, background_tasks: BackgroundTasks):
    """Service 层入口"""
    task_id = str(uuid.uuid4())

    # 🟢 1. 生成唯一文件名 (防止同名覆盖)
    # 例如：uuid-original_name.pdf
    safe_filename = f"{uuid.uuid4()}-{file.filename}"
    file_path = os.path.join(settings.UPLOAD_DIR, safe_filename)

    # 🟢 2. 保存到持久化目录
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # 🟢 3. 生成访问 URL
    # 结果类似: http://localhost:8000/static/bed7...-contract.pdf
    file_url = f"{settings.API_BASE_URL}/static/{safe_filename}"
   
    # 初始化 Redis 状态
    r.hset(f"task:{task_id}", mapping={
        "status": "pending", 
        "message": "已加入队列",
        "filename": file.filename
    })

    # 🟢 4. 传递 file_path 和 file_url 给后台任务
    background_tasks.add_task(process_file_task, task_id, file_path, file.filename, file_url)
    
    return task_id