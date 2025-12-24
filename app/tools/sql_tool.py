# app/tools/sql_tool.py
# 结构化数据查询工具
from langchain.tools import tool
from sqlalchemy import text
# 数据库连接单独放到了 app/utils/database.py
from app.utils.database import AsyncSessionLocal 
import json
from langfuse import Langfuse
from langfuse.openai import openai
import os
from dotenv import load_dotenv
load_dotenv()

# 👈 初始化实例 (Langfuse 会自动读取环境变量中的 Key)
langfuse = Langfuse()

@tool
async def query_business_data(sql_query: str) -> str:
    """
    【查数据库工具】
    当用户询问统计数据、数量、图表分析、反馈数量、满意度评分等结构化数据时，使用此工具。
    ⚠️ 注意：输入必须是可执行的 MySQL SQL 语句。
    表结构：feedbacks(id, rating, tags, comment, created_at)。
    """
    return await execute_sql_query(sql_query)

async def execute_sql_query(sql_query: str):
    """
    [工具函数] 执行 SQL 查询并返回结果
    """
    # 🛡️ 安全防御：简单的关键词拦截，防止删库
    if "DROP" in sql_query.upper() or "DELETE" in sql_query.upper() or "UPDATE" in sql_query.upper():
        return "❌ 安全警告：禁止执行修改/删除操作，仅允许查询。"

    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(text(sql_query))
            keys = result.keys()
            all_rows = result.fetchall()
            
            # 截断逻辑
            MAX_PREVIEW = 10
            total_real_count = len(all_rows)
            
            if total_real_count > MAX_PREVIEW:
                display_rows = all_rows[:MAX_PREVIEW]
                # 生成提示语
                note_text = f"⚠️ 数据量较大(共{total_real_count}条)，已截取前 {MAX_PREVIEW} 条预览。"
            else:
                display_rows = all_rows
                # 如果是全量数据，就不需要 note，或者设为 None
                note_text = None 

            data = [dict(zip(keys, row)) for row in display_rows]
            
            if not data:
                return "查询执行成功，但结果集为空。"

            # 🟢 修正点：不要在这里定死 type="table"
            # 我们返回一个纯净的数据包，让 LLM 自己决定怎么展示
            tool_output = {
                "raw_data": data,
                "system_note": note_text
            }
            
            # 序列化
            json_str = json.dumps(tool_output, ensure_ascii=False, default=str)
            
            # 🟢 核心修改：从 Langfuse 获取指令模板
            # SDK 默认有 60秒 缓存，不会影响性能
            try:
               instruction_prompt = langfuse.get_prompt("tool-sql-result-instruction")
               return instruction_prompt.compile(tool_output=json_str)
            except Exception:
            # 兜底：万一 Langfuse 挂了，使用硬编码的旧逻辑
               return f"""
            查询成功。请根据数据特征选择图表类型(bar/line/pie/table)。
            数据: {json_str}
            """

    except Exception as e:
        return f"❌ SQL 执行失败: {str(e)}"
 
