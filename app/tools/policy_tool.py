# app/tools/policy_tool.py
# 文档检索工具
from langchain.tools import tool
from llama_index.core.vector_stores.types import VectorStoreQueryMode
from app.services.rag_engine import get_index
from app.services.llm_factory import ModelFactory
# 封装 Tools (工具):LangChain 的 @tool 装饰器非常关键，它会自动把函数的 docstring（注释）变成 Prompt 发给大模型，所以注释必须写得很清楚！
@tool
async def lookup_policy_doc(query: str) -> str:
    """
    【查文档工具】
     当用户询问公司的规章制度、合同细节、项目内容、请假流程等非结构化文本信息时，必须使用此工具。
     输入：具体的查询问题（例如："CG2023合同的金额是多少"）。
    """
    try:
        # 1. 获取资源 (按需获取，不再是全局变量)
        index = get_index()  # 初始化索引
        reranker = ModelFactory.get_reranker()


        # 2. 混合检索逻辑
        retriever = index.as_retriever(
            similarity_top_k=10, # 先多取一点
            vector_store_query_mode=VectorStoreQueryMode.HYBRID, # 混合检索
            alpha=0.5
        )
        nodes = await retriever.aretrieve(query)
        print(f"   检索到 {len(nodes)} 个文档。")
        
        # 3. Rerank 逻辑
        filtered_nodes = reranker.postprocess_nodes(nodes, query_str=query)

        # 分数截断逻辑
        # 阈值设定建议：
        # BGE-Reranker 的分数不是 0-1，而是 logit 值（可能是负数）。
        # > 0 通常表示相关。
        # < -2 通常表示完全不相关。
        # 建议先设为 -1.0 或 0.0 进行测试。如果你希望它更严谨，设高一点（如 0.5）。
        SCORE_THRESHOLD = 0.0
        valid_nodes = []
        for n in filtered_nodes:
            # 打印分数方便调试
            print(f"   Ref doc: {n.metadata.get('file_name')} | Score: {n.score}")
            if n.score is not None and n.score > SCORE_THRESHOLD:
                valid_nodes.append(n)
        if not valid_nodes:
            print(f"🛑 [RAG Tool] 所有文档得分均低于 {SCORE_THRESHOLD}，返回未找到。")
            return "系统提示：知识库中【没有找到】包含该问题答案的文档。请直接告诉用户未找到相关信息，不要编造。"        
        
        # 4. 结果组装
        context_str = "\n\n".join([n.text for n in valid_nodes])
        # 这里返回的内容是给大模型看的，可以加一点提示
        return f"【查到的参考文档】：\n{context_str}"
        
    except Exception as e:
        return f"检索服务暂时不可用: {str(e)}"
    