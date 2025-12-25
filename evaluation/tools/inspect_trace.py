# evaluation/debug_trace.py
import json
from evaluation.config import langfuse

def debug_latest_trace():
    print("🔍 正在拉取最近的一条 Trace 详情...")
    
    # 1. 获取列表
    try:
        traces = langfuse.api.trace.list(limit=1).data
        if not traces:
            print("❌ Langfuse 里没有任何数据！")
            return
        
        latest_trace = traces[0]
        t_id = latest_trace.id
        print(f"🆔 Trace ID: {t_id}")
        print(f"⏱️ 时间: {latest_trace.timestamp}")
    except Exception as e:
        print(f"❌ 获取列表失败: {e}")
        return

    # 2. 获取该 Trace 的完整详情 (包含 Observations)
    try:
        # 这一步很关键，我们需要看看 API 到底把 steps 藏在哪里
        full_trace = langfuse.api.trace.get(t_id)
        
        # 3. 打印所有的 Observation (步骤)
        print("\n🕵️‍♀️ 正在通过 API 检查内部步骤 (Observations):")
        
        # 尝试获取 observations
        observations = getattr(full_trace, 'observations', [])
        
        if not observations:
            print("⚠️ 警告: 该 Trace 下没有发现任何 observations 列表！")
            # 可能是 SDK 版本差异，尝试打印一下所有属性
            print("   Trace 对象的所有属性:", dir(full_trace))
        else:
            found_tool = False
            for i, obs in enumerate(observations):
                print(f"\n--- 步骤 {i+1} ---")
                print(f"   Name: {obs.name}")
                print(f"   Type: {obs.type}")
                
                # 检查输出
                output = obs.output
                print(f"   Output (前100字符): {str(output)[:100]}...")
                
                if obs.name == "lookup_policy_doc":
                    found_tool = True
                    print("   ✅ 找到工具调用！正在尝试解析内容...")
                    try:
                        if isinstance(output, str):
                            clean = output.strip().strip("`").replace("json", "")
                            data = json.loads(clean)
                            if "content" in data:
                                print(f"   🎉 成功！找到 content 字段，长度: {len(data['content'])}")
                            else:
                                print(f"   ❌ JSON 解析成功，但没有 'content' 字段。Keys: {data.keys()}")
                        else:
                            print(f"   ⚠️ Output 不是字符串，类型是: {type(output)}")
                    except Exception as e:
                        print(f"   ❌ 解析 JSON 失败: {e}")

            if not found_tool:
                print("\n❌ 结论: 遍历了所有步骤，没有找到名为 'lookup_policy_doc' 的工具调用。")
                print("   可能原因: 1. 工具名称变了? 2. 刚才那次对话没触发工具?")

    except Exception as e:
        print(f"❌ 获取详情失败: {e}")

if __name__ == "__main__":
    debug_latest_trace()