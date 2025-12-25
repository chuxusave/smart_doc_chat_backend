# evaluation/pipelines/test_dataset.py
from langfuse import Langfuse, observe
from evaluation.judges.deepseek_judge import DeepSeekJudge
from evaluation.services.rag_client import RagApiClient

# 🟢 1. 实例化：为了避免冲突，我们将实例命名为 'langfuse_client'
# 之前的报错是因为你可能用 'langfuse' 变量覆盖了 'langfuse' 模块，导致找不到 .trace() 方法
langfuse_client = Langfuse()
judge = DeepSeekJudge()
rag_client = RagApiClient()

DATASET_NAME = "hr-policy-golden-v1"

# 🟢 2. 测试函数：接收 root_span 参数
# 我们不需要 context，直接在传进来的 span 上打分

def test_single_item(item, root_span):
    user_query = item.input.get("input") 
    ground_truth = item.expected_output

    print(f"\n📝 [测试] 问题: {user_query}")
    
    # RAG 调用
    current_answer = rag_client.chat(user_query, session_id="test-manual-link")
    
    if not current_answer:
        current_answer = "Error: 接口调用失败"
    else:
        print(f"   🤖 回答: {current_answer[:50]}...")

    # 更新 trace 的输入输出
    root_span.update(input={"question": user_query}, output={"answer": current_answer})    

    # 评分
    eval_res = judge.evaluate_groundedness(
        question=user_query, 
        answer=current_answer, 
        raw_context=ground_truth 
    )
    
    print(f"   📊 评分: {eval_res['score']}")

    # 在同一个 trace 上打分
    langfuse_client.create_score(
        trace_id=root_span.trace_id,
        name="correctness",
        value=eval_res["score"],
        data_type="NUMERIC",
        comment=eval_res["reasoning"]
    )
    
    print(f"   ✅ 分数已提交到 trace: {root_span.trace_id}")
    
    return current_answer

def run_experiment():
    print(f"⬇️ 正在从 Langfuse 下载数据集: {DATASET_NAME} ...")
    dataset = langfuse_client.get_dataset(DATASET_NAME)
    print(f"✅ 获取成功，共 {len(dataset.items)} 条测试用例。")

    for item in dataset.items:
        try:
            # 使用 item.run() 自动创建并链接 trace
            with item.run(
                run_name="experiment_v3_manual",
                run_description="Manual experiment run",
                run_metadata={"mode": "manual_linking_v3"}
            ) as root_span:
                # 执行测试
                test_single_item(item, root_span)
                
        except Exception as e:
            print(f"⚠️ 运行出错: {e}")
            import traceback
            traceback.print_exc()

    langfuse_client.flush()
    print("\n✅ 实验结束！请前往 Langfuse -> Datasets 查看结果。")



if __name__ == "__main__":
    run_experiment()