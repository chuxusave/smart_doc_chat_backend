
# # evaluation/services/rag_client.py
# 专门负责调用 /api/chat 接口
import requests
import json

class RagApiClient:
    def __init__(self, base_url="http://127.0.0.1:8000"):
        self.base_url = base_url

    def chat(self, message, session_id="test-session"):
        """调用 RAG 接口获取回答"""
        url = f"{self.base_url}/api/chat"
        headers = {"X-Session-ID": session_id}
        payload = {"message": message}
        
        try:
            # 假设你是流式接口，这里简单处理为接收完整响应
            # 如果是流式，可以使用 stream=True 并拼接 content
            with requests.post(url, json=payload, headers=headers, stream=True) as r:
                r.raise_for_status()
                # 简单拼接流式响应 (根据你的实际返回格式调整)
                full_content = ""
                for chunk in r.iter_content(chunk_size=1024):
                    if chunk:
                        text = chunk.decode('utf-8')
                        full_content += text # 这里可能需要更复杂的 SSE 解析逻辑
                return full_content
        except Exception as e:
            print(f"API Call Failed: {e}")
            return None