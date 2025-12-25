# app/services/query_rewriter.py
import re
import dashscope
from http import HTTPStatus
from typing import List
from app.core.config import get_settings
from app.core.prompts import QUERY_REWRITE_TEMPLATE
from langfuse import Langfuse

settings = get_settings()
# 确保 API KEY 已设置
dashscope.api_key = settings.DASHSCOPE_API_KEY

langfuse = Langfuse()

def condense_question(history: List[dict], latest_question: str) -> str:
    """
    结合历史记录，强制将用户的后续提问改写为包含上下文的完整问题。
    使用 qwen-turbo 模型以保证速度。
    """
    
    # 1. ⚡️ [Smart Skip] 智能跳过逻辑
    # 逻辑：长度小于 20 且包含字母和数字的组合，通常是订单号、工号、型号
    # 直接返回，不让 LLM 干扰精确搜索
    if len(latest_question) < 20 and re.search(r'[a-zA-Z]', latest_question) and re.search(r'\d', latest_question):
        print(f"⚡️ [Rewriter] 检测到查询码/ID '{latest_question}'，保持原样。")
        return latest_question.strip()

    # 2. 没有任何历史，无需改写
    if not history:
        return latest_question

    # 3. 提取并格式化最近的历史记录 (适配 Redis 存储的 dict 格式)
    # 只取最后 2 轮 (4条消息)，避免上下文过长
    recent_history = history[-4:] 
    history_str = ""
    for msg in recent_history:
        role = msg.get("role", "")
        content = msg.get("content", "")
        
        # 映射 role 名称，辅助模型理解
        role_label = "用户" if role == "user" else "AI助手"
        
        # 截断过长的历史回复
        clean_content = content[:200] + "..." if len(content) > 200 else content
        history_str += f"{role_label}: {clean_content}\n"
    
    # 4. 构造 Prompt(Langfuse 优先)
    try:
        # 尝试从 Langfuse 拉取名为 "query-rewrite" 的 Prompt
        # cache_ttl_seconds=600 (10分钟缓存)，既能热更新，又不会拖慢每个请求
        langfuse_prompt = langfuse.get_prompt("query-rewrite", cache_ttl_seconds=600)
        
        # 编译 Prompt (填入变量)
        prompt_content = langfuse_prompt.compile(
            history_str=history_str,
            latest_question=latest_question
        )
        print("✅ [Rewriter] Langfuse Prompt 加载成功")
        
    except Exception as e:
        # 🚨 兜底逻辑：如果 Langfuse 挂了或网络超时，使用本地硬编码模板
        print(f"⚠️ [Rewriter] Langfuse Prompt 拉取失败，使用本地兜底: {e}")
        prompt_content = QUERY_REWRITE_TEMPLATE.format(
            history_str=history_str,
            latest_question=latest_question
        )

    try:
        # 5. 调用 DashScope API (使用 Turbo 模型)
        response = dashscope.Generation.call(
            model='qwen-turbo', 
            messages=[{'role': 'user', 'content': prompt_content}],
            result_format='message'
        )
        
        if response.status_code == HTTPStatus.OK:
            new_question = response.output.choices[0]['message']['content'].strip()
            # 清理可能产生的标点符号
            new_question = new_question.replace('"', '').replace("'", "").replace("。", "")
            
            # 如果改写结果和原问题差异过大，打印日志
            if new_question != latest_question:
                print(f"🔄 [Rewriter] 原问题: '{latest_question}' -> 新问题: '{new_question}'")
            return new_question
        else:
            print(f"⚠️ [Rewriter] API报错: {response.message}")
            return latest_question
            
    except Exception as e:
        print(f"⚠️ [Rewriter] 执行异常: {e}")
        return latest_question