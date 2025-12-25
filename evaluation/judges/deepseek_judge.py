# evaluation/judges/deepseek_judge.py
import json
from evaluation.config import deepseek_client, MODEL_DEEPSEEK_CHAT

class DeepSeekJudge:
    def __init__(self):
        self.client = deepseek_client
        self.model = MODEL_DEEPSEEK_CHAT

    def _call_llm(self, system_prompt, user_content):
        """通用 LLM 调用方法，处理 JSON 返回"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ],
                # 强制要求 JSON 格式返回，DeepSeek 支持此参数
                response_format={"type": "json_object"}, 
                temperature=0.1 # 评测任务需要低随机性
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            print(f"❌ 评测 LLM 调用失败: {e}")
            # 兜底返回，防止程序崩溃
            return {"score": 0, "reasoning": f"System Error: {str(e)}"}

    def evaluate(self, question, answer):
        """普通评分：只看回答是否流畅、相关"""
        system_prompt = """你是一个严格的 AI 质量评分员。
请根据用户问题和 AI 的回答，从以下维度进行打分（0-10分）：
1. 相关性：是否回答了用户的问题？
2. 准确性：逻辑是否通顺？
3. 清晰度：表达是否清晰？

请返回 JSON 格式：
{
    "score": <int>,
    "reasoning": "<简短的评分理由>"
}
"""
        user_content = f"【用户问题】: {question}\n【AI回答】: {answer}"
        return self._call_llm(system_prompt, user_content)

    def evaluate_groundedness(self, question, answer, raw_context):
        """
        🟢 [新增] 幻觉审计：核心是对比“参考文档”和“回答”
        只有当回答完全基于参考文档时，才能得高分。
        """
        system_prompt = """你是一个极其严苛的 RAG（检索增强生成）审计员。
你的任务是验证 AI 的回答是否**严格忠实于**参考文档。

【评分标准】
- **10分**：回答的所有事实都在参考文档中有据可查，且没有遗漏关键信息。
- **6-8分**：回答基本正确，但包含了一些文档中未提及的“常识性”废话，或者遗漏了部分细节。
- **0-5分**：【严重幻觉】回答中包含了文档中完全没有的数字、日期、条款，或者回答与文档事实冲突。

【注意】
即使 AI 回答的是现实世界中的真理（例如“太阳从东边升起”），只要参考文档里没写，就必须视为“幻觉”，并扣分！因为我们测试的是检索能力。

请返回 JSON 格式：
{
    "score": <int>,
    "reasoning": "<详细指出哪句话在文档里找到了，哪句话没找到>"
}
"""
        # 截断过长的上下文，防止 Token 溢出
        truncated_context = raw_context[:8000] if len(raw_context) > 8000 else raw_context
        
        user_content = f"""
【参考文档片段】:
{truncated_context}

【用户问题】: {question}

【AI回答】: {answer}
"""
        return self._call_llm(system_prompt, user_content)