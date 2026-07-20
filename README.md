# 🚀 TripCraft — 智能旅行规划助手

基于 AI 多智能体协作的旅行规划系统。6个专业Agent并行工作，结合实时天气、地图POI、**混合检索RAG知识库**、**分层用户记忆**和**容错执行引擎**，生成个性化旅行方案。

## ✨ 核心功能

| 功能 | 说明 |
|------|------|
| 🤖 **多智能体协作规划** | 天气、交通、住宿、景点、行程编排、Critic审查 — 6个Agent并行工作 |
| 🗺️ **地图路线可视化** | 集成高德地图，行程点位标注 + 路径连线 + 类型图例 |
| 💬 **对话式行程调整** | 像聊天一样对AI说"慢一点"或"加个景点"，流式响应 + 方案对比 |
| ⚡ **实时进度追踪** | WebSocket流式推送，看到每个Agent的工作状态 |
| 🧠 **分层记忆系统** | 短期会话(Redis) → 长期语义(PostgreSQL) → 运行时上下文组装，强化个性化推荐 |
| 🔀 **Hybrid RAG 检索** | Qdrant稠密向量 + PG BM25 + 结构化过滤，RRF(k=60)融合多路结果 |
| 🛡️ **Harness 容错引擎** | 统一工具执行：超时控制 + 指数退避重试 + 熔断器 + 分级降级 |
| 📊 **RAG 全链路评测** | 50条黄金Query基准，检索层+生成层多维度量化评估 |
| 📝 **AI导出预览** | LLM格式化润色行程为精美Markdown |
| 🔌 **插件系统** | 可扩展的插件架构，侧边栏集成实用工具 |

## 🏗️ 技术栈

### 前端
- **React 18** + TypeScript + Vite
- **Ant Design 5** — UI组件（深度定制暗色霓虹主题）
- **Zustand** — 状态管理
- **Framer Motion** — 动画
- **高德地图 JSAPI 2.0** — 地图

### 后端
- **FastAPI** + WebSocket
- **LangGraph** — 多Agent状态图编排
- **通义千问 (DashScope)** — LLM + Embedding
- **PostgreSQL** + SQLAlchemy async — 持久化 + BM25全文检索
- **Redis** — 缓存 + 会话记忆
- **Qdrant** — 向量检索 (RAG)

## 📂 项目结构

```
TripCraft/
├── frontend/                  # React 前端
│   └── src/
│       ├── components/        # 组件
│       │   ├── layout/        # 布局（Header, AnimatedBackground, FloatingAgentOrb）
│       │   └── ui/            # 通用UI（GlassCard, NeonButton, TiltCard, AnimatedNumber）
│       ├── api/client.ts      # HTTP + WebSocket 客户端
│       ├── stores/            # Zustand 状态管理
│       ├── styles/            # CSS（variables, utilities, animations, effects, app）
│       ├── plugins/           # 插件系统
│       └── types/             # TypeScript 类型
│
├── backend/                   # Python 后端
│   └── app/
│       ├── api/               # REST + WebSocket 路由
│       ├── agents/            # LangGraph 多Agent工作流
│       │   └── workflow.py    # DAG编排 + Harness集成
│       ├── core/config.py     # 配置管理（Hybrid RAG / Harness 参数）
│       ├── evaluation/        # RAG全链路评测体系
│       │   ├── golden_dataset.py   # 50条黄金测试Query（8城/3类型/3难度）
│       │   ├── metrics.py     # 检索指标：Recall/MRR/NDCG/HitRate
│       │   ├── ragas_eval.py   # 生成评测：RAGAS框架
│       │   └── run_evaluation.py   # 评测编排器 + CLI入口
│       ├── models/            # Pydantic + SQLAlchemy 模型
│       │   └── rag_chunk_models.py # rag_chunks表（BM25 + 结构化字段）
│       ├── services/          # 业务服务
│       │   ├── harness.py     # 容错执行引擎（超时/重试/熔断/降级）
│       │   ├── hybrid_rag.py  # RRF融合 + Markdown清洗 + 滑动窗口分块
│       │   ├── memory_service.py  # 三层记忆系统（短期/长期/运行时）
│       │   ├── preprocess.py  # RAG预处理管线（清洗→分块→实体抽取）
│       │   ├── rag.py         # Hybrid RAG服务（三路召回 + 双写）
│       │   ├── persistence.py # PostgreSQL CRUD
│       │   ├── seed_data.py   # 8城种子数据
│       │   ├── auth.py        # JWT 认证
│       │   ├── llm.py         # LLM 服务
│       │   ├── amap.py        # 高德地图 API
│       │   ├── cache.py       # Redis 缓存
│       │   ├── adjustment.py  # 行程调整
│       │   ├── export.py      # 导出服务
│       │   └── geo_optimizer.py # 路线优化
│       └── main.py            # FastAPI 应用入口
│
└── docs/                      # 文档
```

## 🤖 Multi-Agent 工作流

### DAG 编排

```
                    START
                   /  |  \  \
           weather transport accommodation attraction
                   \  |    /
                    \ |   /
                   itinerary
                       |
                     critic
                    /       \
               retry         done
```

4个数据采集Agent并行 → Itinerary汇总编排 → Critic 5维审查（体力/时间/预算/天气/数据）。条件边实现 Critic→Itinerary 重试闭环，最多3轮迭代。

| Agent | 职责 | 数据来源 |
|-------|------|---------|
| 🌤️ Weather | 获取目的地4天天气 | 高德天气API |
| 🚄 Transport | 生成交通建议 | 模板 + LLM |
| 🏨 Accommodation | 搜索酒店POI | 高德POI搜索 |
| 🎡 Attraction | 搜索景点 + RAG笔记 | 高德POI + Qdrant + LLM |
| 📋 Itinerary | AI编排每日行程 | LLM (通义千问) |
| 🔍 Critic | 5维度审查 | 规则引擎 |

### Harness 容错集成

每个外部API调用统一通过 `_WorkflowHarness.api_call()` 入口，替代裸 try/except：

```python
weather_result = await self._harness.api_call(
    func=self.amap.weather,
    args=(request.destination,),
    fallback=lambda: {"city": request.destination, "casts": [], "fallback": True},
    tool_name="weather",
)
# weather_result: ToolResult(status=success/error/fallback/timeout, data=..., error=..., attempts=...)
```

## 🔀 Hybrid RAG 检索架构

### 三路召回 + RRF 融合

```
					Query
					  |
			┌─────────┼─────────┐
			▼         ▼         ▼
		Path A     Path B     Path C
	  Qdrant稠密   PG BM25   结构化过滤
	  向量检索   全文检索    (城市谓词)
			└─────────┬─────────┘
					  ▼
			  RRF(k=60) 融合
					  ▼
				Top-K 结果
```

| 路径 | 技术 | 解决的问题 |
|------|------|-----------|
| Path A | Qdrant cosine similarity | 语义模糊查询 |
| Path B | PostgreSQL `ts_rank_cd` BM25 | 精确关键词匹配（地名/酒店名） |
| Path C | 城市谓词 payload filter | 结构化过滤 |

**RRF 公式**: `score(d) = Σ_i 1/(k + rank_i(d))` — 同一文档出现在多路中自动获得累加权重，实现去重 + boost。

### 双写导入管线

```python
# Markdown 清洗 → 滑动窗口分块(700字+80重叠) → 实体抽取 → 双写
documents = [RagDocument(city="杭州", text="...", ...)]
await rag.ingest_notes("杭州", documents)
# ↓ 同时写入:
#   - Qdrant (dense vector index)
#   - rag_chunks 表 (BM25 sparse index + 结构化字段)
```

搜索降级链: `hybrid → dense-only → sparse-only → fallback_notes`（本地城市知识库兜底）。

### 预处理管线

```python
prepare_chunks(raw_text, base_meta)
# Step 1: Markdown 清洗（代码块/链接/HTML/表格 → 纯文本）
# Step 2: 滑动窗口分块（max_chars=700, overlap=80）
# Step 3: 实体抽取（POI/时间/价格/城市/时长 — 正则无模型依赖）
# Step 4: 输出 enriched chunks（含 uuid5 全局唯一 ID）
```

## 🧠 分层记忆系统

### 三层架构

```
┌─────────────────────────────────────────┐
│           MemoryAssembler               │
│          (运行时上下文组装)                │
│   从三层并行召回 → 动态拼接为LLM上下文     │
└──────────┬──────────────┬───────────────┘
           ▼              ▼
   Short-term       Long-term
   (短期会话)        (长期语义)
   Redis List       PostgreSQL
   TTL=24h          衰减权重管理
```

| 层 | 存储 | TTL | 用途 |
|----|------|-----|------|
| 短期会话记忆 | Redis List | 24h | 多轮对话连贯性、最近调整意图 |
| 长期语义记忆 | PostgreSQL | 永久（衰减） | 用户偏好、旅行习惯、历史决策 |
| 运行时状态 | 请求级内存 | 单次 | 动态拼接LLM上下文 |

### 衰减权重管理

```
weight = recency × frequency × confidence

- recency: 指数衰减 e^(-λ×days)，半衰期30天
- frequency: log(1 + access_count)，边际递减
- confidence: 原始置信度 [0,1]
```

去重策略: **哈希精确去重** + **字符级 Jaccard 语义近似去重** (阈值0.85)。

### 使用方式

```python
# 组装上下文（每次规划前调用）
assembler = MemoryAssembler(owner_id="user_123")
context = await assembler.assemble_context(query="杭州美食", session_id="sess_abc")
# context["context_text"] → 直接拼入 LLM prompt

# 从调整指令中学习
await assembler.learn_from_adjustment(
    instruction="不要太早起",
    extracted=[MemoryItem(key="早起偏好", value="不早于9点", confidence=0.9)]
)
```

## 🛡️ Harness 容错执行引擎

### 核心组件

| 组件 | 职责 |
|------|------|
| `ToolExecutor` | 统一执行入口，编排超时+重试+熔断+降级 |
| `ToolResult` | 显式 Schema (success/error/fallback/timeout/circuit_open) |
| `CircuitBreaker` | 熔断器 (CLOSED→OPEN→HALF_OPEN→CLOSED) |
| `ExecutorConfig` | 可配置策略参数 |

### 状态机

```
             success
    ┌──────────────────┐
    ▼                  │
 CLOSED ──fail×N──► OPEN ──timeout──► HALF_OPEN
    ▲                  (拒绝请求)       │
    │                                  │ success×2
    └──────────────────────────────────┘
```

### 预配置执行器

```python
# API 调用：8s超时 + 2次重试 + 熔断
api_executor = ToolExecutor(ExecutorConfig(
    timeout_seconds=8.0, max_retries=2,
    base_backoff_seconds=0.5,
    circuit_breaker=CircuitBreaker(failure_threshold=5, recovery_timeout=60.0),
))

# LLM 调用：30s超时 + 1次重试
llm_executor = ToolExecutor(ExecutorConfig(
    timeout_seconds=30.0, max_retries=1, base_backoff_seconds=2.0,
))

# 缓存/本地：2s超时不重试
cache_executor = ToolExecutor(ExecutorConfig(
    timeout_seconds=2.0, max_retries=0,
))
```

### 分级降级

| 场景 | 降级策略 |
|------|---------|
| LLM 调用失败 | → 模板引擎生成 |
| API 超时/熔断 | → 本地兜底数据（城市知识库） |
| 单 Agent 异常 | → 隔离不影响其他 Agent |

## 📊 RAG 全链路评测体系

### 评测数据

- **8城** 种子数据（杭州/北京/上海/成都/西安/南京/重庆/苏州）
- **50条** 黄金测试 Query，覆盖3种类型:
  - `exact` 精确匹配 — 查询词直接出现在源文档
  - `semantic` 语义模糊 — 改写/意图表达
  - `negative` 否定查询 — 无相关文档
- 3种难度: `easy` / `medium` / `hard`

### 检索层指标

| 指标 | 说明 |
|------|------|
| Recall@k (k=3,5,10) | 召回率 |
| MRR | 首位相关文档排名倒数 |
| NDCG@k (k=3,5,10) | 归一化折损累积增益 |
| HitRate@k | Top-K 命中率 |

对比方案: **Dense-only** vs **BM25-only** vs **Hybrid+RRF**，量化验证混合检索提升幅度。

### 生成层指标

基于 **RAGAS** 框架：
- `Faithfulness` — 答案忠实于上下文
- `Answer Relevance` — 答案与问题相关度
- `Context Precision` — 检索上下文精准率
- `Context Recall` — 检索上下文召回率

### 运行评测

```bash
cd backend
python -m app.evaluation.run_evaluation
# 输出对比报告：三种方案的指标对比表 + NDCG提升百分比
```

## 🚀 快速启动

### 环境要求
- Python 3.11+
- Node.js 18+
- PostgreSQL 15+
- Redis (可选)
- Qdrant (可选，RAG功能需要)

### 1. 后端

```bash
cd backend

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 安装依赖
pip install -e .

# 配置环境变量
cp .env.example .env
# 编辑 .env 填入 PostgreSQL、Redis、DashScope API Key等
```

**.env 必需配置：**
```env
SECRET_KEY=<生成一个32位随机字符串>
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=<你的密码>
POSTGRES_DB=tripcraft
DASHSCOPE_API_KEY=<阿里云DashScope API Key>
AMAP_API_KEY=<高德地图API Key>
```

**新增配置项（可选，有合理默认值）：**
```env
# Hybrid RAG
HYBRID_RAG_ENABLED=true
RRF_K=60
SPARSE_LIMIT_MULTIPLIER=3

# Harness 容错引擎
HARNESS_TIMEOUT=10.0
HARNESS_MAX_RETRIES=2
HARNESS_CIRCUIT_THRESHOLD=5

# Qdrant
QDRANT_URL=http://localhost:6333
QDRANT_TRAVEL_NOTES_COLLECTION=travel_notes
QDRANT_ATTRACTIONS_COLLECTION=attractions
```

**初始化种子数据（首次启动）：**
```bash
python -m app.services.seed_data
```

**启动：**
```bash
python run.py
# 或: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

API文档: http://localhost:8000/docs

### 2. 前端

```bash
cd frontend

# 安装依赖
npm install

# 配置环境变量
cp .env.example .env
# 编辑 .env 填入高德地图 JS API Key
```

**.env 配置：**
```env
VITE_API_BASE=/api/v1
VITE_WS_URL=ws://localhost:8000/api/v1/plans/stream
VITE_AMAP_WEB_JS_KEY=<高德地图JS API Key>
```

**启动：**
```bash
npm run dev
```

前端: http://localhost:5173

## 🔌 插件系统

项目支持插件扩展。内置 `QuickFacts` 插件展示目的地实用信息。

**开发插件：**
```typescript
import type { TripCraftPlugin } from './plugins'

export const MyPlugin: TripCraftPlugin = {
  meta: {
    id: 'my-plugin',
    name: '我的插件',
    version: '1.0.0',
    description: '插件描述',
    slot: 'sidebar',  // 'sidebar' | 'toolbar' | 'context-panel' | 'dashboard-tab'
  },
  render: (ctx) => {
    // ctx.plan 是当前行程
    return <div>插件内容</div>
  },
}

// 注册
pluginRegistry.register(MyPlugin)
```

## 📡 API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/auth/register` | 注册 |
| POST | `/api/v1/auth/login` | 登录 |
| GET | `/api/v1/plans` | 我的行程列表 |
| POST | `/api/v1/plans` | 创建行程 |
| GET | `/api/v1/plans/{id}` | 行程详情 |
| DELETE | `/api/v1/plans/{id}` | 删除行程 |
| WS | `/api/v1/plans/stream` | 流式规划 |
| POST | `/api/v1/plans/adjust` | 调整行程 |
| WS | `/api/v1/plans/adjust/stream` | 流式调整 |
| GET | `/api/v1/plans/{id}/export/markdown` | 导出Markdown |
| GET | `/api/v1/plans/{id}/export/preview` | AI预览导出 |
| GET | `/api/v1/memory` | 偏好记忆 |
| GET | `/api/v1/plans/{id}/chat` | 对话历史 |
| POST | `/api/v1/plans/{id}/chat` | 保存对话 |

## 🔒 安全

- JWT Bearer Token 认证
- 用户数据隔离（所有查询按 `owner_id` 过滤）
- 密码 SHA-256 + 随机盐
- CORS 白名单配置

## 📝 License

MIT
