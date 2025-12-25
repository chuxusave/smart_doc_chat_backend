# app/api/routers.py
from fastapi import APIRouter, Depends, Header, UploadFile, File, BackgroundTasks, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from pydantic import BaseModel
import json
import qdrant_client
from app.core.config import get_settings

# --- Imports from App Structure ---
from app.utils.database import get_db
from app.core.redis import redis_manager
from app.services.llm_factory import ModelFactory
from app.services.file_service import handle_file_upload
from app.services.query_rewriter import condense_question
from app.core.models import Feedback  # 👈 假设你移动了 models.py
from app.core.prompts import DB_SCHEMA_TEXT, CORE_SYSTEM_PROMPT # 👈 假设你移动了 prompts.py

# --- LangChain & Langfuse ---
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langfuse import Langfuse
from langfuse.langchain import CallbackHandler

# --- Tools ---
from app.tools.policy_tool import lookup_policy_doc
from app.tools.sql_tool import query_business_data

import os
from dotenv import load_dotenv
load_dotenv()


router = APIRouter()
# langfuse = Langfuse()


# --- DTOs ---
class ChatRequest(BaseModel):
    message: str

class FeedbackRequest(BaseModel):
    session_id: str
    question: str
    answer: str
    rating: int
    tags: List[str] = []
    comment: Optional[str] = ""

# --- Helper: Get History ---
def get_chat_history_dep(x_session_id: str = Header(..., alias="X-Session-ID")):
    return redis_manager.get_chat_history(x_session_id)

settings = get_settings()
# ==========================
# 1. 💬 Chat 接口
# ==========================
@router.post("/chat")
async def chat_endpoint(
    request: ChatRequest,
    x_session_id: str = Header(..., alias="X-Session-ID"),
    history_dicts: List[dict] = Depends(get_chat_history_dep)
):
    print(f"🔔 新请求 Session ID: {x_session_id}, 历史消息数: {len(history_dicts)}")

  
    # 0. 查询改写 
    # 将改写后的问题用于 Agent 推理，但历史记录中仍保存用户原话
    final_query = condense_question(history_dicts, request.message)
    # 1. 准备工具和模型
    tools = [lookup_policy_doc, query_business_data]
    llm = ModelFactory.get_llm()

    # 2. 转换历史记录 (Dict -> LangChain Objects)
    lc_history = []
    for msg in history_dicts:
        if msg.get("role") == "user":
            lc_history.append(HumanMessage(content=msg.get("content")))
        elif msg.get("role") == "assistant":
            lc_history.append(AIMessage(content=msg.get("content")))

    langfuse = Langfuse()
    # 3. 动态获取 Prompt (CMS 模式)
    try:
        # cache_ttl_seconds=0 方便调试，生产环境可去掉
        langfuse_prompt = langfuse.get_prompt("rag-core-system", cache_ttl_seconds=0)
        final_system_prompt_str = langfuse_prompt.compile(schema=DB_SCHEMA_TEXT)
        print(f"✅ Prompt 拉取成功: {final_system_prompt_str}")
    except Exception as e:
        print(f"⚠️ Prompt 拉取失败: {e}")
        # 兜底逻辑
        final_system_prompt_str = CORE_SYSTEM_PROMPT.format()

    # 4. 构建 Agent
    prompt = ChatPromptTemplate.from_messages([
        SystemMessage(content=final_system_prompt_str),
        ("placeholder", "{chat_history}"),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}"),
    ])
    
    agent = create_tool_calling_agent(llm, tools, prompt)
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
    
    # 5. 定义流式生成器
    async def event_generator():
        full_response = ""
        captured_sources = [] # 🟢  初始化容器，用于暂存来源信息
        langfuse_handler = CallbackHandler()
        
        try:
            async for event in agent_executor.astream_events(
                {"input": final_query, "chat_history": lc_history},
                version="v1",
                config={
                    "callbacks": [langfuse_handler],
                    "metadata": {
                        "langfuse_session_id": x_session_id,
                        "langfuse_user_id": "user_default"
                    }
                }
            ):
                kind = event["event"]
                # 🟢 2. 监听工具执行结束事件
                if kind == "on_tool_end":
                    # 打印日志方便调试
                    print(f"🔧 Tool End: {event['name']}")
                    
                    # 仅处理文档检索工具的 Source
                    if event["name"] == "lookup_policy_doc":
                        try:
                            tool_output_str = event["data"].get("output")
                            # 🛡️ 防御性编程：判断是否为字符串且像 JSON
                            if tool_output_str and isinstance(tool_output_str, str):
                                # 尝试清洗可能存在的 Markdown 代码块标记 (```json ... ```)
                                clean_str = tool_output_str.strip()
                                if clean_str.startswith("```"):
                                    clean_str = clean_str.strip("`").replace("json", "").strip()
                                
                                # 解析 JSON
                                output_json = json.loads(clean_str)
                                
                                if isinstance(output_json, dict) and "sources" in output_json:
                                    captured_sources = output_json["sources"]
                                    print(f"✅ 捕获到 Sources: {len(captured_sources)} 个")
                            else:
                                print(f"⚠️ 工具输出格式异常: {type(tool_output_str)}")
                                
                        except json.JSONDecodeError:
                            print(f"⚠️ 工具输出不是有效的 JSON (可能是报错信息): {tool_output_str}")
                        except Exception as e:
                            print(f"⚠️ 解析 Sources 未知错误: {e}")
                # 3. 正常的 LLM 流式输出        
                if kind == "on_chat_model_stream":
                    chunk = event["data"]["chunk"]
                    if chunk.content:
                        yield chunk.content
                        full_response += chunk.content
            # 🟢 4. 在流结束后，追加 Sources 协议数据
            # 只有当确实检索到了来源时才发送
            if captured_sources:
                # 按照前端协议：换行 + __SOURCES__ + 换行 + JSON
                sources_payload = json.dumps(captured_sources, ensure_ascii=False)
                yield f"\n\n__SOURCES__\n{sources_payload}"

            # 6. 保存历史到 Redis
            if full_response:
                new_history = history_dicts + [
                    {"role": "user", "content": request.message},
                    {"role": "assistant", "content": full_response}
                ]
                redis_manager.save_chat_history(x_session_id, new_history)
                
        except Exception as e:
            yield f"系统错误: {str(e)}"

    return StreamingResponse(event_generator(), media_type="text/plain")

# ==========================
# 2. 📤 上传接口
# ==========================
@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...), 
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    task_id = await handle_file_upload(file, background_tasks)
    return {"status": "success", "task_id": task_id, "message": "开始后台处理"}

@router.get("/upload/{task_id}")
async def get_upload_status(task_id: str):
    task_info = redis_manager.get_client().hgetall(f"task:{task_id}")
    if not task_info:
        return JSONResponse(status_code=404, content={"status": "not_found"})
    return task_info

# ==========================
# 3. ⭐ 反馈接口
# ==========================
@router.post("/feedback")
async def submit_feedback(
    request: FeedbackRequest,
    db: AsyncSession = Depends(get_db)
):
    try:
        tags_str = ",".join(request.tags)
        new_feedback = Feedback(
            session_id=request.session_id,
            question=request.question,
            answer=request.answer,
            rating=request.rating,
            tags=tags_str,
            comment=request.comment
        )
        db.add(new_feedback)
        await db.commit()
        await db.refresh(new_feedback)
        return {"status": "success", "id": new_feedback.id}
    except Exception as e:
        await db.rollback()
        return JSONResponse(status_code=500, content={"detail": str(e)})
    

# ==========================
# 4. 📂 文件列表接口 (补全这个)
# ==========================
@router.get("/files")
async def get_indexed_files():
    """获取知识库中已索引的文件列表"""
    try:
        # 连接 Qdrant
        client = qdrant_client.QdrantClient(url=settings.QDRANT_URL)
        
        # 1. 检查集合是否存在
        if not client.collection_exists(settings.COLLECTION_NAME):
            return {"count": 0, "files": []}

        # 2. 遍历数据 (这里简单取前100个用于展示)
        # 生产环境如果文件很多，可以使用 Scroll 分页
        scroll_result = client.scroll(
            collection_name=settings.COLLECTION_NAME,
            limit=100,
            with_payload=True,
            with_vectors=False
        )
        
        points, _ = scroll_result
        files = set()
        for point in points:
            # 提取 payload 里的 file_name
            if point.payload and "file_name" in point.payload:
                files.add(point.payload["file_name"])
        
        return {"count": len(files), "files": list(files)}
        
    except Exception as e:
        print(f"❌ 查询文件列表失败: {e}")
        # 出错不返回 500，返回空列表防止前端崩
        return {"count": 0, "files": []}    