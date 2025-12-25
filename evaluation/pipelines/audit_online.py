# evaluation/run_eval.py
# 跑定时任务，审计历史 Trace
import time
import json
from ..config import langfuse
from ..judges import DeepSeekJudge

judge = DeepSeekJudge()

def run_auto_evaluation(batch_size=5):
    print(f"🔍 正在从 Langfuse API 获取最近的 {batch_size} 条 Trace...")

    try:
        # 1. 获取 Trace 列表
        traces_response = langfuse.api.trace.list(limit=batch_size)
        traces = traces_response.data
    except Exception as e:
        print(f"❌ 获取 Trace 列表失败: {e}")
        return

    success_count = 0
    for trace in traces:
        t_id = trace.id
        u_input = getattr(trace, 'input', None)
        a_output = getattr(trace, 'output', None)

        if not u_input or not a_output:
            continue

        print(f"📝 正在分析 Trace: {t_id[:8]}...")
        
        raw_context = None
        
        # 🟢 [关键修改] 挖掘上下文
        try:
            # 获取完整详情
            try:
                full_trace = langfuse.api.trace.get(t_id)
            except AttributeError:
                full_trace = langfuse.api.traces.get(t_id)
            
            if hasattr(full_trace, 'observations'):
                for obs in full_trace.observations:
                    # 1. 锁定工具
                    if obs.name == "lookup_policy_doc" and obs.output:
                        output_data = obs.output
                        
                        # 🟢 [兼容性修复] 既支持字典，也支持字符串
                        try:
                            # 情况 A: SDK 已经自动转成了字典 (你日志里显示的情况)
                            if isinstance(output_data, dict):
                                if "content" in output_data:
                                    raw_context = output_data["content"]
                                    print(f"   ✅ [Dict] 成功提取参考文档: {len(raw_context)} 字符")
                                    break
                            
                            # 情况 B: 依然是 JSON 字符串 (旧数据或特定环境)
                            elif isinstance(output_data, str):
                                clean_str = output_data.strip().strip("`").replace("json", "")
                                temp_json = json.loads(clean_str)
                                if isinstance(temp_json, dict) and "content" in temp_json:
                                    raw_context = temp_json["content"]
                                    print(f"   ✅ [Str] 成功提取参考文档: {len(raw_context)} 字符")
                                    break
                        except Exception as e:
                            print(f"   ⚠️ 解析工具输出异常: {e}")
                            
        except Exception as e:
            print(f"   ⚠️ 获取 Trace 详情失败: {e}")

        # 🟢 [分支评分]
        if raw_context:
            # 有上下文：查幻觉
            try:
                # 确保你的 DeepSeekJudge 类里有这个方法，没有的话会自动跳到 except
                eval_res = judge.evaluate_groundedness(str(u_input), str(a_output), str(raw_context))
                score_name = "faithfulness" # 忠实度
                print(f"   🤖 正在进行幻觉审计 (Faithfulness)...")
            except AttributeError:
                print("   ⚠️ Judge 缺少 evaluate_groundedness 方法，降级为普通评分")
                eval_res = judge.evaluate(str(u_input), str(a_output))
                score_name = "deepseek_quality"
        else:
            # 无上下文：查质量
            print("   ⚠️ 未找到上下文，进行普通评分 (Quality)...")
            eval_res = judge.evaluate(str(u_input), str(a_output))
            score_name = "deepseek_quality"

        # 回传分数
        langfuse.create_score(
            trace_id=t_id,
            name=score_name,
            value=eval_res["score"],
            comment=eval_res["reasoning"]
        )
        
        success_count += 1
        time.sleep(0.5)

    langfuse.flush()
    print(f"✅ 评测结束！成功处理 {success_count} 条数据。")

if __name__ == "__main__":
    run_auto_evaluation()