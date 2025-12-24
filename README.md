# 📘 Smart Doc Chat - 企业级 RAG 与 SQL 数据分析助手

Smart Doc Chat 是一个基于 **RAG (检索增强生成)** 和 **Agent (智能体)** 架构的企业级问答系统后端。

它不仅支持对非结构化文档（PDF/Word）的深度检索，还具备 Text-to-SQL 能力，能够查询业务数据并自动决策生成前端可渲染的图表数据（Table/Line/Bar/Pie）。系统深度集成了 **Langfuse**，用于全链路追踪和 Prompt（提示词）的云端管理。

## ✨ 核心特性

* **双路智能检索**:
* **RAG 引擎**: 基于 LlamaIndex + Qdrant，支持混合检索（关键词 + 向量）和 BGE-Reranker 重排序。
* **SQL Agent**: 基于 LangChain Tool Calling，能够执行 SQL 查询业务数据（如反馈表统计）。


* **智能可视化决策**: LLM 输出包含 `<<CHART_DATA>>` 协议，自动根据数据特征选择最合适的图表类型。
* **Prompt CMS**: 系统提示词和工具指令通过 Langfuse 平台动态管理，无需重启服务即可调整 AI 行为。
* **异步高性能**: 基于 FastAPI + Async SQLAlchemy + Redis，支持后台文件处理任务。
* **国产化模型适配**: 默认集成阿里云通义千问 (`qwen-max`) 和 BAAI 本地向量模型。

## 🛠 技术栈

* **框架**: FastAPI, Python 3.10+
* **LLM 编排**: LangChain (Agent), LlamaIndex (RAG)
* **模型服务**: DashScope (Qwen-Max), HuggingFace (Local Embeddings)
* **数据库**:
* **Vector DB**: Qdrant (Docker)
* **RDBMS**: MySQL 8.0 (Docker)
* **Cache**: Redis (Docker)


* **可观测性 & 配置**: Langfuse (Self-hosted)

---

## 🚀 快速开始

### 1. 环境要求

* Docker & Docker Compose
* Python 3.10+ (推荐使用 Conda)
* Git

### 2. 启动基础设施 (Docker)

项目依赖大量中间件，请优先启动 Docker 环境。

```bash
cd smart_doc_chat_docker

# 1. 启动所有服务 (Qdrant, MySQL, Redis, MinIO, Langfuse, Clickhouse, Postgres)
docker-compose up -d

# 2. 检查运行状态 (确保所有容器 status 为 Up)
docker-compose ps

```

* **Langfuse 控制台**: http://localhost:3333
* **Qdrant**: http://localhost:6333
* **MySQL**: 端口 3307 (账号 root / 密码 mysql123)

### 3. 初始化 Langfuse (关键步骤)

由于代码中使用了 `langfuse.get_prompt()` 动态获取提示词，**必须**在 Langfuse 后台手动配置，否则 Agent 无法启动。

1. 访问 http://localhost:3333 注册账户并创建项目。
2. 获取 **Public Key** and **Secret Key**。
3. 点击左侧 **Prompts**，新建以下 2 个 Prompt：

#### Prompt 1: 核心系统提示词

* **Name**: `rag-core-system`
* **Type**: `chat`
* **Content**: (复制 `app/core/prompts.py` 中的 `CORE_SYSTEM_TEMPLATE_RAW` 内容)
* *注意：保留 `{{schema}}` 占位符，代码会自动填充。*



#### Prompt 2: SQL 结果处理指令

* **Name**: `tool-sql-result-instruction`
* **Type**: `text`
* **Content**:
```text
查询执行成功。

【原始数据】
{{tool_output}}

请根据以上数据：
1. 分析数据特征，决定使用 bar(柱状图), line(折线图), pie(饼图) 还是 table(表格)。
2. 严格遵守 System Prompt 中的 <<CHART_DATA>> JSON 格式输出。
3. 给出简短的数据洞察。

```



### 4. 后端环境配置

回到项目根目录：

```bash
# 1. 创建虚拟环境
conda create -n smart_doc_chat python=3.10
conda activate smart_doc_chat

# 2. 安装依赖
pip install -r requirements.txt

```

### 5. 下载本地模型

项目默认加载本地 Embedding 和 Reranker 模型，需下载到指定目录：

```bash
# 安装 huggingface 命令行工具
pip install -U huggingface_hub

# 设置国内镜像
export HF_ENDPOINT=https://hf-mirror.com

# 下载 BGE-Large Embedding
huggingface-cli download --resume-download BAAI/bge-large-zh-v1.5 --local-dir ./models/bge-large-zh-v1.5/BAAI/bge-large-zh-v1___5 --local-dir-use-symlinks False

# 下载 BGE-Reranker
huggingface-cli download --resume-download BAAI/bge-reranker-base --local-dir ./models/bge-reranker-base/BAAI/bge-reranker-base --local-dir-use-symlinks False

```

### 6. 环境变量配置 (.env)

在根目录下创建 `.env` 文件：

```ini
# --- 模型服务 (阿里云 DashScope) ---
DASHSCOPE_API_KEY=sk-xxxxxxxxxxxxxxxx

# --- Langfuse (从 http://localhost:3333 获取) ---
LANGFUSE_PUBLIC_KEY=pk-lf-xxxxxxxx
LANGFUSE_SECRET_KEY=sk-lf-xxxxxxxx
LANGFUSE_HOST=http://localhost:3333

# --- 数据库配置 (对应 Docker 设置) ---
MYSQL_PASSWORD=mysql123
MYSQL_HOST=localhost
MYSQL_PORT=3307
MYSQL_DB=rag_db

# --- 中间件 ---
REDIS_HOST=localhost
REDIS_PORT=6379
QDRANT_URL=http://localhost:6333

```

### 7. 启动服务

```bash
# 启动 FastAPI (自动重载模式)
python -m app.main

```

若看到 `🚀 服务正在启动...` 和 `✅ MySQL 表结构已同步`，即代表启动成功。
API 文档地址：http://localhost:8000/docs

---

## 📂 目录结构说明

```plaintext
project_root/
├── app/
│   ├── api/             # 路由定义 (chat, upload, feedback)
│   ├── core/            # 核心配置 (config, prompts, database)
│   ├── services/        # 业务逻辑 (rag_engine, file_service, llm_factory)
│   ├── tools/           # Agent 工具 (policy_tool, sql_tool)
│   ├── utils/           # 通用工具
│   └── main.py          # 程序入口
├── models/              # 本地模型存放目录
├── smart_doc_chat_docker/ # Docker 编排文件
└── requirements.txt     # Python 依赖

```

## 📝 开发指南

### 添加新知识库文件

通过 API `/api/upload` 上传 PDF/Word 文件。后台 `file_service` 会自动进行：

1. 解析文件
2. 文本分块 (SentenceSplitter)
3. 向量化 (BGE-Large)
4. 存入 Qdrant

### 修改图表输出逻辑

如果需要调整图表生成的判断逻辑，请前往 Langfuse 修改 `tool-sql-result-instruction` 提示词，无需修改代码。

### 常见问题 (FAQ)

**Q: 启动时报错 `ValueError: Model path ... not found`?**
A: 请检查步骤 5 中的模型是否完整下载，且路径与 `app/core/config.py` 中的 `EMBEDDING_MODEL_PATH` 完全一致。

**Q: Langfuse 连接失败?**
A: 确保 Docker 容器 `langfuse-web` 已启动，且 `.env` 中的 `LANGFUSE_HOST` 没有多余的斜杠（应为 `http://localhost:3333`）。

**Q: SQL 工具不执行?**
A: 检查 `app/core/prompts.py` 中的 Schema 定义是否与数据库实际表结构一致。目前仅支持查询 `feedbacks` 表。
