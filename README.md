# 🚀 TripCraft — 智能旅行规划助手

基于 AI 多智能体协作的旅行规划系统。6个专业Agent并行工作，结合实时天气、地图POI、RAG知识库和用户偏好，生成个性化旅行方案。

## ✨ 核心功能

| 功能 | 说明 |
|------|------|
| 🤖 **多智能体协作规划** | 天气、交通、住宿、景点、行程编排、Critic审查 — 6个Agent并行工作 |
| 🗺️ **地图路线可视化** | 集成高德地图，行程点位标注 + 路径连线 + 类型图例 |
| 💬 **对话式行程调整** | 像聊天一样对AI说"慢一点"或"加个景点"，流式响应 + 方案对比 |
| ⚡ **实时进度追踪** | WebSocket流式推送，看到每个Agent的工作状态 |
| 🧠 **用户偏好学习** | 从每次对话中提取偏好记忆，逐步个性化推荐 |
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
- **PostgreSQL** + SQLAlchemy async — 持久化
- **Redis** — 缓存 + 对话记录
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
│       ├── services/          # 业务服务
│       │   ├── persistence.py # PostgreSQL CRUD
│       │   ├── auth.py        # JWT 认证
│       │   ├── llm.py         # LLM 服务
│       │   ├── amap.py        # 高德地图 API
│       │   ├── rag.py         # Qdrant 向量检索
│       │   ├── cache.py       # Redis 缓存
│       │   ├── adjustment.py  # 行程调整
│       │   ├── export.py      # 导出服务
│       │   └── geo_optimizer.py # 路线优化
│       ├── models/            # Pydantic + SQLAlchemy 模型
│       └── core/config.py     # 配置管理
│
└── docs/                      # 文档
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

## 🤖 Agent 工作流

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

| Agent | 职责 | 数据来源 |
|-------|------|---------|
| 🌤️ Weather | 获取目的地4天天气 | 高德天气API |
| 🚄 Transport | 生成交通建议 | 模板 + LLM |
| 🏨 Accommodation | 搜索酒店POI | 高德POI搜索 |
| 🎡 Attraction | 搜索景点 + RAG笔记 | 高德POI + Qdrant + LLM |
| 📋 Itinerary | AI编排每日行程 | LLM (通义千问) |
| 🔍 Critic | 5维度审查（体力/时间/预算/天气/数据） | 规则引擎 |

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
