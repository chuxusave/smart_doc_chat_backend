import os
import logging
import sys

# 1. 设置 Debug 日志，这会打印出 SDK 到底在请求哪个 URL
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
# 针对 langfuse 开启 debug
logging.getLogger("langfuse").setLevel(logging.DEBUG)

from langfuse import Langfuse, observe

# 2. 硬编码配置 (暂时绕过 .env，排除干扰)
# 请填入你的公钥私钥
PUBLIC_KEY = "pk-lf-2c547d34-50a1-49ba-9832-9d1f810d7008"
SECRET_KEY = "sk-lf-d671854f-3497-47f4-b96d-172c5e66bcd3"
# 注意：这里千万不要带 /api，也不要带末尾斜杠
HOST = "http://localhost:3333"

# 3. 初始化
# 注意：新版 SDK 通常允许通过 debug=True 或 logging 配置来查看请求
os.environ["LANGFUSE_DEBUG"] = "True" 

langfuse = Langfuse(
    public_key=PUBLIC_KEY,
    secret_key=SECRET_KEY,
    host=HOST
)

@observe(name="debug_trace")
def test_function():
    return "ok"

if __name__ == "__main__":
    print(f"--- Testing Host: {HOST} ---")
    try:
        test_function()
        print("Flushing...")
        langfuse.flush()
        print("Done.")
    except Exception as e:
        print(e)