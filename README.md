📘 Smart Doc Chat - 企业级智能文档问答系统 (RAG Agent)
这是一个基于 RAG (检索增强生成) 和 Agent (智能体) 架构的企业级问答系统。它支持非结构化文档检索 (PDF/Word) 和结构化数据查询 (SQL)，并集成了 Langfuse 全链路追踪。

🛠 技术栈
后端框架: FastAPI, Python 3.10+

LLM 编排: LangChain, LlamaIndex

向量数据库: Qdrant

关系数据库: MySQL 8.0 (异步 SQLAlchemy)

缓存/队列: Redis Stack

对象存储: MinIO (用于 Langfuse 大数据存储)

可观测性: Langfuse v3 (基于 Clickhouse + Postgres)

模型: Qwen-Max (通义千问), BGE-Large (Embedding), BGE-Reranker

📂 目录结构
Plaintext

project_root/
├── backend/                  # Python 后端代码
│   ├── app/                  # 核心应用逻辑
│   ├── models/               # 本地模型文件 (bge-large, reranker)
│   ├── .env                  # 后端配置文件 (Key, DB连接等)
│   └── requirements.txt      # Python 依赖
│
└── smart_doc_chat_docker/    # 基础设施 (Docker)
    ├── docker-compose.yml    # 容器编排
    ├── clickhouse_config.xml # Clickhouse 配置文件
    └── .env                  # Docker 环境变量 (数据库初始密码等)
🚀 部署指南 (从零开始)
第一步：环境准备
确保你的机器已安装：

Docker & Docker Compose

Python 3.10+ (建议使用 Conda)

Git

第二步：启动基础设施 (Docker)
进入 Docker 配置目录并启动所有服务。

Bash

cd smart_doc_chat_docker

# 1. 确保目录内有 clickhouse_config.xml (如果没有，请从备份找回)
# 2. 启动服务
docker-compose up -d

# 3. 检查状态 (确保所有容器都是 Up)
docker-compose ps
注意端口映射：

Langfuse: http://localhost:3333

MinIO 控制台: http://localhost:9011 (API: 9010)

Redis UI: http://localhost:8001

MySQL: 宿主机端口 3307 (容器内 3306)

Qdrant: 6333

第三步：配置 Langfuse (关键)
因为使用了新的 Docker 环境，Langfuse 是空的，必须手动初始化。

访问 http://localhost:3333 并注册账号。

创建一个新项目 (Project)。

进入 Settings -> API Keys，生成 Public Key 和 Secret Key (稍后填入后端 .env)。

导入提示词 (Prompts)：

进入左侧 Prompts，点击 New Prompt。

Prompt 1:

Name: rag-core-system

Content: (复制 backend/prompts.py 中的 CORE_SYSTEM_TEMPLATE_RAW 内容)

Prompt 2:

Name: tool-sql-result-instruction

Content: (复制 "查询执行成功...【原始数据】..." 等指令内容)

第四步：后端环境配置
回到 backend 目录。

1. 创建 Python 虚拟环境

Bash

cd ../backend
conda create -n smart_doc_chat python=3.10
conda activate smart_doc_chat
2. 安装依赖

Bash

pip install -r requirements.txt
(如果没有 requirements.txt，请参考文末附录手动安装)

3. 下载本地模型

Bash

# 安装 HuggingFace CLI
pip install -U huggingface_hub

# 设置国内镜像
export HF_ENDPOINT=https://hf-mirror.com

# 下载 Embedding 模型 (注意路径要和 config.py 一致)
huggingface-cli download --resume-download BAAI/bge-large-zh-v1.5 --local-dir ./models/bge-large-zh-v1.5 --local-dir-use-symlinks False

# 下载 Reranker 模型
huggingface-cli download --resume-download BAAI/bge-reranker-base --local-dir ./models/bge-reranker-base --local-dir-use-symlinks False
4. 配置环境变量 (.env) 在 backend/ 目录下新建 .env 文件：

Ini, TOML

# --- 模型服务 ---
DASHSCOPE_API_KEY=sk-xxxxxxxxxxxxxxxx  # 你的通义千问 Key

# --- 数据库 (注意端口是 3307) ---
MYSQL_USER=root
MYSQL_PASSWORD=your_docker_password  # 必须与 docker 里的 MYSQL_ROOT_PASSWORD 一致
MYSQL_HOST=localhost
MYSQL_PORT=3307
MYSQL_DB=rag_db

# --- 基础设施 ---
REDIS_HOST=localhost
REDIS_PORT=6379
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION=enterprise_knowledge_base_hybrid_v1

# --- Langfuse ---
LANGFUSE_PUBLIC_KEY=pk-lf-xxxxxxxx  # 刚才在网页生成的
LANGFUSE_SECRET_KEY=sk-lf-xxxxxxxx
LANGFUSE_HOST=http://localhost:3333
第五步：启动后端服务
Bash

# 确保在 backend 目录下
python -m app.main
如果看到以下日志，说明启动成功：

Plaintext

🚀 服务正在启动...
✅ MySQL 表结构已同步
INFO:     Uvicorn running on http://0.0.0.0:8000
🕹️ 使用指南
API 文档
启动后访问：http://localhost:8000/docs

核心接口
/api/chat (POST): 智能对话接口，支持 Session 上下文。

/api/upload (POST): 上传 PDF/Word 文档，后台自动向量化。

/api/feedback (POST): 用户点赞/点踩反馈。

❓ 常见问题排查 (Troubleshooting)
Q1: 启动报错 bind: address already in use?

检查本地是否运行了 MySQL (3306) 或其他 Docker 容器。如果是 MySQL 冲突，请确保 .env 里配置的是映射端口 3307。

Q2: 报错 Unrecognized model in ...?

模型下载不完整。请删除 models/ 下对应文件夹，使用 huggingface-cli 重新下载，务必加上 --local-dir-use-symlinks False。

Q3: Langfuse 报错 500?

检查 Langfuse 是否有 Prompt。

检查 Python 代码中的 LANGFUSE_PUBLIC_KEY 是否正确。

📦 附录：requirements.txt (参考)
Plaintext

fastapi
uvicorn
python-dotenv
sqlalchemy
aiomysql
redis
qdrant-client
llama-index-core
llama-index-embeddings-huggingface
llama-index-vector-stores-qdrant
llama-index-llms-dashscope
llama-index-postprocessor-flag-embedding-reranker
langchain
langchain-openai
langchain-core
langfuse
dashscope
transformers
torch
python-multipart