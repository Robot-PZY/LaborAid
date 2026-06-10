# LaborAid 技术文档

> 劳动者维权智能助手 - 完整技术架构文档

---

## 目录

1. [项目概述](#项目概述)
2. [前端架构](#前端架构)
3. [后端架构](#后端架构)
4. [数据库模型](#数据库模型)
5. [AI/Agent 系统](#aiagent-系统)
6. [RAG/检索系统](#rag检索系统)
7. [OCR/多模态处理](#ocr多模态处理)
8. [配置管理](#配置管理)
9. [测试体系](#测试体系)
10. [部署架构](#部署架构)

---

## 项目概述

LaborAid 是一个面向劳动者的智能法律服务助手，提供从维权指引、证据整理、文书生成到法律研究的全流程支持。

### 核心技术栈

**前端**
- React 19 + TypeScript + Vite
- react-router-dom v7 (路由)
- TanStack Query (状态管理)
- TailwindCSS + Radix UI (UI 组件库)

**后端**
- FastAPI (Web 框架)
- SQLAlchemy 2.0 (ORM)
- SQLite/PostgreSQL (数据库)
- LangGraph (Agent 编排)
- ChromaDB (向量数据库)

**AI/ML**
- DeepSeek V4 Pro (主 LLM)
- Qwen-VL-OCR (视觉识别)
- BM25 + 向量检索 (混合检索)

---

## 前端架构

### 目录结构

```
frontend/src/
├── pages/                    # 页面组件 (20+)
│   ├── Dashboard.tsx        # 仪表盘
│   ├── Cases.tsx            # 案件管理
│   ├── Evidence.tsx         # 证据管理
│   ├── DocumentGenerate.tsx # 文书生成
│   ├── Research.tsx         # 法律研究
│   ├── Search.tsx           # 统一检索
│   ├── Guidance.tsx         # 维权指引
│   ├── Vault.tsx            # 材料库
│   ├── Records.tsx          # 记录汇总
│   ├── ContractReview.tsx   # 合同审查
│   ├── EnterpriseLookup.tsx # 企业查询
│   ├── Knowledge.tsx        # 知识库
│   ├── Templates.tsx        # 模板管理
│   ├── Settings.tsx         # 系统设置
│   ├── Login.tsx            # 登录页
│   ├── admin/               # 管理后台
│   │   ├── AdminDashboard.tsx
│   │   ├── AdminUsers.tsx
│   │   ├── AdminConfig.tsx
│   │   └── AdminKnowledge.tsx
│   ├── channels/            # 维权渠道
│   │   ├── ChannelHub.tsx
│   │   ├── ChannelDetail.tsx
│   │   └── ChannelLegacyRedirect.tsx
│   └── tools/               # 工具页面
│       ├── CompensationCalculator.tsx
│       └── LimitationCalculator.tsx
│
├── components/               # 可复用组件 (75+)
│   ├── Layout.tsx           # 主布局
│   ├── AdminLayout.tsx      # 管理后台布局
│   ├── ProtectedRoute.tsx   # 路由守卫
│   ├── AdminRoute.tsx       # 管理员路由
│   ├── AgentHeader.tsx      # Agent 头部
│   ├── ui/                  # 基础 UI 组件
│   │   ├── Button.tsx
│   │   ├── Input.tsx
│   │   ├── Card.tsx
│   │   ├── Dialog.tsx
│   │   ├── Select.tsx
│   │   ├── Toast.tsx
│   │   ├── CredibilityBar.tsx
│   │   └── PageSkeleton.tsx
│   ├── intake/              # 咨询入口组件
│   │   ├── ChatIntake.tsx
│   │   ├── IntakePlanResult.tsx
│   │   ├── AnalysisResultCard.tsx
│   │   ├── ChannelIntakeWizard.tsx
│   │   ├── IntakeResumeBar.tsx
│   │   ├── IntakeDesk.tsx
│   │   ├── EntryGate.tsx
│   │   ├── DynamicForm.tsx
│   │   └── IntakeSampleCards.tsx
│   ├── cases/               # 案件相关组件
│   │   ├── CaseWorkflowStepper.tsx
│   │   ├── CaseJourneyPanel.tsx
│   │   ├── CaseAgentCoach.tsx
│   │   ├── CaseAgentsStrip.tsx
│   │   ├── CaseReadinessHint.tsx
│   │   └── EvidenceCoveragePanel.tsx
│   ├── evidence/            # 证据组件
│   │   └── EvidenceAnalysisSummary.tsx
│   ├── documents/           # 文书组件
│   │   ├── DocRecommendationPanel.tsx
│   │   └── CourtDocumentPreview.tsx
│   ├── channels/            # 渠道组件
│   │   ├── ReportDialog.tsx
│   │   ├── OfficialPlatformStrip.tsx
│   │   ├── OfficialEntryHint.tsx
│   │   └── ChannelScenarioPanel.tsx
│   ├── dashboard/           # 仪表盘组件
│   │   ├── DashboardHeroBanner.tsx
│   │   └── CalculatorToolRow.tsx
│   ├── guidance/            # 指引组件
│   │   └── GuidanceHubPanel.tsx
│   ├── ocr/                 # OCR 组件
│   │   └── OcrStatusBadge.tsx
│   ├── charts/              # 图表组件
│   │   └── SimpleCharts.tsx
│   ├── history/             # 历史记录
│   │   └── ToolHistoryPanel.tsx
│   ├── brand/               # 品牌组件
│   │   └── Logo.tsx
│   └── service/             # 服务组件
│       └── ServiceStrip.tsx
│
├── hooks/                    # 自定义 Hooks (6)
│   ├── useCaseWorkflow.ts   # 案件工作流
│   ├── useCaseAgents.ts     # 案件 Agents
│   ├── useCaseAgentStep.ts  # Agent 步骤
│   ├── useTheme.ts          # 主题切换
│   ├── useDebounce.ts       # 防抖
│   └── useLocalStorage.ts   # 本地存储
│
├── lib/                      # 工具库
│   ├── api/                 # API 客户端
│   │   ├── client.ts        # Axios 实例
│   │   ├── auth.ts          # 认证 API
│   │   ├── cases.ts         # 案件 API
│   │   ├── evidence.ts      # 证据 API
│   │   ├── documents.ts     # 文书 API
│   │   ├── research.ts      # 研究 API
│   │   ├── search.ts        # 检索 API
│   │   ├── guidance.ts      # 指引 API
│   │   ├── vault.ts         # 材料库 API
│   │   ├── records.ts       # 记录 API
│   │   ├── contracts.ts     # 合同 API
│   │   ├── enterprise.ts    # 企业 API
│   │   ├── knowledge.ts     # 知识库 API
│   │   ├── templates.ts     # 模板 API
│   │   ├── admin.ts         # 管理 API
│   │   ├── intake.ts        # 咨询 API
│   │   └── channels.ts      # 渠道 API
│   ├── channels.ts          # 渠道配置
│   ├── channel-themes.ts    # 渠道主题
│   ├── intake-scenarios.ts  # 咨询场景
│   ├── intake-plan.ts       # 咨询计划
│   ├── intake-session.ts    # 咨询会话
│   ├── doc-recommendations.ts # 文书推荐
│   ├── evidence-analysis-parse.ts # 证据分析解析
│   ├── report-province.ts   # 报告省份
│   ├── storage-keys.ts      # 存储键名
│   ├── tool-history.ts      # 工具历史
│   ├── case-ai-cache.ts     # AI 缓存
│   ├── active-case.ts       # 活跃案件
│   ├── network-status.tsx   # 网络状态
│   ├── toast.tsx            # 提示消息
│   ├── accessibility.tsx    # 无障碍
│   ├── keyboard.tsx         # 键盘快捷键
│   ├── loading.tsx          # 加载状态
│   ├── markdown.tsx         # Markdown 渲染
│   └── use-theme.ts         # 主题 Hook
│
├── config/                   # 配置文件
│   ├── agents.ts            # Agent 配置
│   ├── assets.ts            # 资源配置
│   ├── tool-labels.ts       # 工具标签
│   ├── guidance-labels.ts   # 指引标签
│   └── labor/               # 劳动法律配置
│       ├── official-platforms.json
│       ├── intake-scenarios.json
│       ├── special-channels.json
│       └── intake-samples.json
│
├── test/                     # 测试工具
│   ├── test-utils.tsx
│   └── setup.ts
│
├── App.tsx                   # 主应用组件
├── main.tsx                  # 入口文件
└── index.css                 # 全局样式
```

### 路由系统

使用 `react-router-dom v7`，支持代码分割和懒加载。

**主要路由**

```typescript
// App.tsx
const routes = [
  { path: '/login', element: <Login /> },
  { 
    path: '/', 
    element: <ProtectedRoute><Layout /></ProtectedRoute>,
    children: [
      { index: true, element: <Dashboard /> },
      { path: 'cases', element: <Cases /> },
      { path: 'evidence', element: <Evidence /> },
      { path: 'documents', element: <DocumentGenerate /> },
      { path: 'research', element: <Research /> },
      { path: 'search', element: <Search /> },
      { path: 'guidance', element: <Guidance /> },
      { path: 'vault', element: <Vault /> },
      { path: 'records', element: <Records /> },
      { path: 'contracts', element: <ContractReview /> },
      { path: 'enterprise', element: <EnterpriseLookup /> },
      { path: 'knowledge', element: <Knowledge /> },
      { path: 'templates', element: <Templates /> },
      { path: 'settings', element: <Settings /> },
      { path: 'channels', element: <ChannelHub /> },
      { path: 'channels/:id', element: <ChannelDetail /> },
      { path: 'tools/compensation', element: <CompensationCalculator /> },
      { path: 'tools/limitation', element: <LimitationCalculator /> },
    ]
  },
  {
    path: '/admin',
    element: <AdminRoute><AdminLayout /></AdminRoute>,
    children: [
      { index: true, element: <AdminDashboard /> },
      { path: 'users', element: <AdminUsers /> },
      { path: 'config', element: <AdminConfig /> },
      { path: 'knowledge', element: <AdminKnowledge /> },
    ]
  }
];
```

### 状态管理

使用 **TanStack Query** 进行服务端状态管理。

```typescript
// lib/api/client.ts
import axios from 'axios';

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器：添加 JWT Token
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// 响应拦截器：处理 401
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default apiClient;
```

**使用示例**

```typescript
// hooks/useCases.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { casesApi } from '@/lib/api/cases';

export function useCases() {
  return useQuery({
    queryKey: ['cases'],
    queryFn: () => casesApi.list(),
  });
}

export function useCreateCase() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (data: CreateCaseInput) => casesApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cases'] });
    },
  });
}
```

### UI 组件库

**技术选型**
- **TailwindCSS**: 原子化 CSS 框架
- **Radix UI**: 无样式的可访问性组件
- **Lucide React**: 图标库

**组件示例**

```typescript
// components/ui/Button.tsx
import * as React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils';

const buttonVariants = cva(
  'inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50',
  {
    variants: {
      variant: {
        default: 'bg-primary text-primary-foreground hover:bg-primary/90',
        destructive: 'bg-destructive text-destructive-foreground hover:bg-destructive/90',
        outline: 'border border-input bg-background hover:bg-accent hover:text-accent-foreground',
        secondary: 'bg-secondary text-secondary-foreground hover:bg-secondary/80',
        ghost: 'hover:bg-accent hover:text-accent-foreground',
        link: 'text-primary underline-offset-4 hover:underline',
      },
      size: {
        default: 'h-10 px-4 py-2',
        sm: 'h-9 rounded-md px-3',
        lg: 'h-11 rounded-md px-8',
        icon: 'h-10 w-10',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, ...props }, ref) => {
    return (
      <button
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    );
  }
);

export { Button, buttonVariants };
```

---

## 后端架构

### 目录结构

```
backend/app/
├── main.py                  # FastAPI 应用入口
├── config.py                # 配置管理
├── database.py              # 数据库连接
│
├── api/                     # API 层
│   └── routers/             # 路由 (22 个)
│       ├── auth.py          # 认证 (登录/注册)
│       ├── cases.py         # 案件管理
│       ├── evidence.py      # 证据管理
│       ├── documents.py     # 文书管理
│       ├── research.py      # 法律研究
│       ├── search.py        # 统一检索
│       ├── guidance.py      # 维权指引
│       ├── vault.py         # 材料库
│       ├── records.py       # 记录汇总
│       ├── contracts.py     # 合同审查
│       ├── enterprise.py    # 企业查询
│       ├── knowledge.py     # 知识库
│       ├── templates.py     # 模板管理
│       ├── admin.py         # 管理后台
│       ├── intake.py        # 咨询入口
│       ├── channels.py      # 维权渠道
│       ├── vector.py        # 向量检索
│       ├── llm_settings.py  # LLM 配置
│       ├── external_apis.py # 外部 API
│       ├── app_config.py    # 应用配置
│       ├── user_portal.py   # 用户门户
│       ├── verification.py  # 法条验证
│       └── health.py        # 健康检查
│
├── models/                  # SQLAlchemy 模型 (14 个)
│   ├── user.py              # 用户
│   ├── case.py              # 案件
│   ├── evidence.py          # 证据
│   ├── document.py          # 文书
│   ├── research.py          # 研究报告
│   ├── knowledge.py         # 知识库
│   ├── contract.py          # 合同
│   ├── template.py          # 模板
│   ├── vault.py             # 材料库
│   ├── search.py            # 搜索记录
│   ├── enterprise.py        # 企业
│   ├── channel.py           # 渠道
│   ├── intake.py            # 咨询
│   └── system.py            # 系统配置
│
├── schemas/                 # Pydantic 模型 (20 个)
│   ├── auth.py              # 认证 Schema
│   ├── case.py              # 案件 Schema
│   ├── evidence.py          # 证据 Schema
│   ├── document.py          # 文书 Schema
│   ├── research.py          # 研究 Schema
│   ├── search.py            # 检索 Schema
│   ├── guidance.py          # 指引 Schema
│   ├── vault.py             # 材料库 Schema
│   ├── records.py           # 记录 Schema
│   ├── contract.py          # 合同 Schema
│   ├── enterprise.py        # 企业 Schema
│   ├── knowledge.py         # 知识库 Schema
│   ├── template.py          # 模板 Schema
│   ├── admin.py             # 管理 Schema
│   ├── intake.py            # 咨询 Schema
│   ├── intake_chat.py       # 咨询聊天 Schema
│   ├── channels.py          # 渠道 Schema
│   ├── vector.py            # 向量 Schema
│   ├── llm_settings.py      # LLM 配置 Schema
│   ├── external_api.py      # 外部 API Schema
│   ├── app_config.py        # 应用配置 Schema
│   ├── user_portal.py       # 用户门户 Schema
│   ├── verification.py      # 验证 Schema
│   └── orchestrator.py      # 编排器 Schema
│
├── services/                # 业务逻辑层
│   ├── agents/              # Agent 系统
│   │   ├── supervisor.py    # 监督者 Agent
│   │   ├── graph.py         # LangGraph 定义
│   │   ├── base.py          # Agent 基类
│   │   ├── helpers.py       # 辅助函数
│   │   ├── routes.py        # Agent 路由
│   │   └── specialists/     # 专家 Agent
│   │       ├── guidance.py  # 指引 Agent
│   │       ├── evidence.py  # 证据 Agent
│   │       ├── docgen.py    # 文书 Agent
│   │       ├── research.py  # 研究 Agent
│   │       └── records.py   # 记录 Agent
│   │
│   ├── orchestrator/        # 编排器
│   │   ├── case_context.py  # 案件上下文
│   │   ├── gather.py        # 数据收集
│   │   ├── ask.py           # 问答
│   │   ├── snapshot.py      # 快照
│   │   ├── next_step.py     # 下一步
│   │   ├── doc_pipeline.py  # 文书流水线
│   │   ├── doc_facts.py     # 文书事实
│   │   ├── context_summary.py # 上下文摘要
│   │   └── pipeline_tasks.py # 流水线任务
│   │
│   ├── rag/                 # RAG 系统
│   │   ├── __init__.py      # RAG 导出
│   │   ├── retriever.py     # 检索器
│   │   └── chains.py        # LangChain 链
│   │
│   ├── search/              # 搜索服务
│   │   └── unified.py       # 统一搜索
│   │
│   ├── evidence/            # 证据服务
│   │   ├── ocr.py           # OCR 处理
│   │   ├── pdf_vision.py    # PDF 视觉
│   │   ├── analysis.py      # 证据分析
│<think>
├── tests/
│   ├── __init__.py
│   ├── conftest.py          # pytest 配置
│   ├── test_integration.py  # 集成测试
│   ├── test_agents.py       # Agent 测试
│   ├── test_rag.py          # RAG 测试
│   ├── test_auth.py         # 认证测试
│   ├── test_cases.py        # 案件测试
│   ├── test_evidence.py     # 证据测试
│   ├── test_documents.py    # 文书测试
│   └── test_search.py       # 搜索测试
│
├── .env.example             # 环境变量示例
├── requirements.txt         # Python 依赖
└── README.md                # 项目说明
```

### API 路由清单

**认证 (`/api/v1/auth`)**
- `POST /login` - 用户登录
- `POST /register` - 用户注册
- `GET /me` - 获取当前用户

**案件管理 (`/api/v1/cases`)**
- `GET /` - 案件列表
- `POST /` - 创建案件
- `GET /{case_id}` - 获取案件详情
- `PUT /{case_id}` - 更新案件
- `DELETE /{case_id}` - 删除案件

**证据管理 (`/api/v1/evidence`)**
- `GET /` - 证据列表
- `POST /upload` - 上传证据
- `GET /{evidence_id}` - 获取证据
- `POST /{evidence_id}/analyze` - 分析证据
- `DELETE /{evidence_id}` - 删除证据

**文书管理 (`/api/v1/documents`)**
- `GET /` - 文书列表
- `POST /generate` - 生成文书
- `GET /{document_id}` - 获取文书
- `PUT /{document_id}` - 更新文书
- `POST /{document_id}/export` - 导出文书

**法律研究 (`/api/v1/research`)**
- `POST /` - 创建研究报告
- `GET /` - 研究列表
- `GET /{report_id}` - 获取报告

**统一检索 (`/api/v1/search`)**
- `POST /unified` - 统一检索
- `POST /laws` - 法条检索
- `POST /cases` - 案例检索

**维权指引 (`/api/v1/guidance`)**
- `GET /steps` - 维权步骤
- `GET /channels` - 维权渠道
- `POST /intake` - 咨询入口

**材料库 (`/api/v1/vault`)**
- `GET /` - 材料列表
- `POST /upload` - 上传材料
- `GET /{file_id}` - 获取材料
- `DELETE /{file_id}` - 删除材料

**记录汇总 (`/api/v1/records`)**
- `GET /timeline` - 时间线
- `GET /statistics` - 统计信息

**合同审查 (`/api/v1/contracts`)**
- `POST /upload` - 上传合同
- `POST /{contract_id}/review` - 审查合同
- `GET /{contract_id}/report` - 获取审查报告

**企业查询 (`/api/v1/enterprise`)**
- `GET /search` - 搜索企业
- `GET /{enterprise_id}` - 获取企业详情
- `GET /{enterprise_id}/risk` - 获取风险信息

**知识库 (`/api/v1/knowledge`)**
- `GET /` - 知识列表
- `POST /` - 添加知识
- `GET /{knowledge_id}` - 获取知识
- `PUT /{knowledge_id}` - 更新知识
- `DELETE /{knowledge_id}` - 删除知识

**模板管理 (`/api/v1/templates`)**
- `GET /` - 模板列表
- `POST /` - 创建模板
- `GET /{template_id}` - 获取模板
- `PUT /{template_id}` - 更新模板
- `DELETE /{template_id}` - 删除模板

**管理后台 (`/api/v1/admin`)**
- `GET /users` - 用户列表
- `PUT /users/{user_id}` - 更新用户
- `GET /statistics` - 系统统计
- `GET /logs` - 系统日志

**咨询入口 (`/api/v1/intake`)**
- `POST /chat` - 聊天咨询
- `POST /analyze` - 分析咨询
- `GET /plan` - 获取咨询计划

**维权渠道 (`/api/v1/channels`)**
- `GET /` - 渠道列表
- `GET /{channel_id}` - 获取渠道
- `POST /{channel_id}/report` - 提交举报

**向量检索 (`/api/v1/vector`)**
- `POST /add` - 添加向量
- `POST /search` - 向量搜索
- `DELETE /{vector_id}` - 删除向量

**LLM 配置 (`/api/v1/llm-settings`)**
- `GET /` - 获取配置
- `PUT /` - 更新配置

**外部 API (`/api/v1/external-apis`)**
- `GET /` - API 列表
- `POST /` - 添加 API
- `PUT /{api_id}` - 更新 API
- `DELETE /{api_id}` - 删除 API

**应用配置 (`/api/v1/app-config`)**
- `GET /` - 配置列表
- `PUT /{key}` - 更新配置

**用户门户 (`/api/v1/user-portal`)**
- `GET /profile` - 用户资料
- `PUT /profile` - 更新资料

**法条验证 (`/api/v1/verification`)**
- `POST /check` - 验证法条

**健康检查 (`/api/v1/health`)**
- `GET /` - 健康状态

### 认证机制

使用 **JWT (JSON Web Token)** 进行身份验证。

**认证流程**

```python
# app/api/routers/auth.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.services.auth import authenticate_user, create_user, create_access_token
from app.core.security import get_current_user
from app.models.user import User

router = APIRouter()

@router.post("/login", response_model=TokenResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    user = authenticate_user(db, request.email, request.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token = create_access_token(data={"sub": user.id})
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/register", response_model=TokenResponse)
def register(request: RegisterRequest, db: Session = Depends(get_db)):
    user = create_user(db, request)
    access_token = create_access_token(data={"sub": user.id})
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    return current_user
```

**JWT 配置**

```python
# app/config.py
class Settings(BaseSettings):
    JWT_SECRET_KEY: str = "your-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 480  # 8 小时
```

**密码安全**

```python
# app/core/security.py
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)
```

**速率限制**

```python
# app/core/security.py
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.post("/login")
@limiter.limit("5/minute")
def login(request: Request, ...):
    ...
```

---

## 数据库模型

### ER 图

```
┌─────────────┐
│   User      │
├─────────────┤
│ id (PK)     │
│ email       │
│ password    │
│ name        │
│ role        │
│ is_active   │
│ created_at  │
└──────┬──────┘
       │
       │ 1:N
       ▼
┌─────────────┐       ┌─────────────┐
│   Case      │       │  Evidence   │
├─────────────┤       ├─────────────┤
│ id (PK)     │◄──────│ case_id(FK) │
│ user_id(FK) │  1:N  │ id (PK)     │
│ title       │       │ file_path   │
│ description │       │ ocr_text    │
│ case_type   │       │ analysis    │
│ status      │       │ created_at  │
│ created_at  │       └─────────────┘
└──────┬──────┘
       │
       │ 1:N
       ▼
┌─────────────┐       ┌─────────────┐
│  Document   │       │  Research   │
├─────────────┤       ├─────────────┤
│ id (PK)     │       │ id (PK)     │
│ case_id(FK) │       │ case_id(FK) │
│ title       │       │ query       │
│ content     │       │ report      │
│ doc_type    │       │ created_at  │
│ status      │       └─────────────┘
│ created_at  │
└─────────────┘

┌─────────────┐       ┌─────────────┐
│ Knowledge   │       │  Contract   │
├─────────────┤       ├─────────────┤
│ id (PK)     │       │ id (PK)     │
│ title       │       │ case_id(FK) │
│ content     │       │ file_path   │
│ category    │       │ review      │
│ created_at  │       │ created_at  │
└─────────────┘       └─────────────┘

┌─────────────┐       ┌─────────────┐
│  Template   │       │   Vault     │
├─────────────┤       ├─────────────┤
│ id (PK)     │       │ id (PK)     │
│ name        │       │ user_id(FK) │
│ doc_type    │       │ file_path   │
│ structure   │       │ file_name   │
│ prompt      │       │ created_at  │
│ created_at  │       └─────────────┘
└─────────────┘

┌─────────────┐       ┌─────────────┐
│   Search    │       │ Enterprise  │
├─────────────┤       ├─────────────┤
│ id (PK)     │       │ id (PK)     │
│ user_id(FK) │       │ name        │
│ query       │       │ credit_code │
│ results     │       │ risk_info   │
│ created_at  │       │ created_at  │
└─────────────┘       └─────────────┘

┌─────────────┐       ┌─────────────┐
│  Channel    │       │   Intake    │
├─────────────┤       ├─────────────┤
│ id (PK)     │       │ id (PK)     │
│ name        │       │ user_id(FK) │
│ description │       │ case_id(FK) │
│ platform    │       │ messages    │
│ created_at  │       │ plan        │
└─────────────┘       │ created_at  │
                      └─────────────┘

┌─────────────┐       ┌─────────────┐
│ LLMSettings │       │ ExternalAPI │
├─────────────┤       ├─────────────┤
│ id (PK)     │       │ id (PK)     │
│ api_key     │       │ name        │
│ base_url    │       │ base_url    │
│ model       │       │ auth_type   │
│ max_tokens  │       │ endpoints   │
│ updated_at  │       │ created_at  │
└─────────────┘       └─────────────┘

┌─────────────┐
│ AppConfig   │
├─────────────┤
│ id (PK)     │
│ key         │
│ value       │
│ description │
│ updated_at  │
└─────────────┘
```

### 模型定义

**用户模型**

```python
# app/models/user.py
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from app.database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    name = Column(String, nullable=False)
    role = Column(String, default="user")  # user, admin
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

**案件模型**

```python
# app/models/case.py
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base

class Case(Base):
    __tablename__ = "cases"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text)
    case_type = Column(String)  # labor_dispute, contract_dispute, etc.
    status = Column(String, default="active")  # active, closed, archived
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    evidences = relationship("Evidence", back_populates="case", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="case")
    research_reports = relationship("ResearchReport", back_populates="case")
```

**证据模型**

```python
# app/models/evidence.py
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base

class Evidence(Base):
    __tablename__ = "evidences"
    
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=False)
    file_path = Column(String, nullable=False)
    ocr_text = Column(Text)
    analysis = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    case = relationship("Case", back_populates="evidences")
```

**文书模型**

```python
# app/models/document.py
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base

class Document(Base):
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=False)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    doc_type = Column(String, nullable=False)  # complaint, evidence_list, etc.
    status = Column(String, default="draft")  # draft, final
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    case = relationship("Case", back_populates="documents")
```

**知识库模型**

```python
# app/models/knowledge.py
from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from app.database import Base

class Knowledge(Base):
    __tablename__ = "knowledge"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    category = Column(String)  # law, case, regulation
    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

---

## AI/Agent 系统

### 架构概览

```
┌─────────────────────────────────────────────────────────┐
│                   Supervisor Agent                      │
│  (协调所有专家 Agent，决定下一步行动)                     │
└────────────────────┬────────────────────────────────────┘
                     │
        ┌────────────┼────────────┬────────┬──────────┐
        │            │            │        │          │
        ▼            ▼            ▼        ▼          ▼
   ┌────────┐  ┌──────────┐  ┌────────┐ ┌────────┐ ┌────────┐
   │Guidance│  │ Evidence │  │ DocGen │  │Research│  │Records │
   │ Agent  │  │  Agent   │  │ Agent  │  │ Agent  │  │ Agent  │
   └────────┘  └──────────┘  └────────┘ └────────┘ └────────┘
       │            │            │        │          │
       │            │            │        │          │
       ▼            ▼            ▼        ▼          ▼
   维权指引      证据整理      文书生成   法律研究    记录汇总
```

### LangGraph 状态机

```python
# app/services/agents/graph.py
from langgraph.graph import StateGraph, END
from typing import TypedDict, Literal
from app.services.orchestrator.case_context import CaseContext

class AgentState(TypedDict):
    context: CaseContext
    current_agent: str
    next_action: str
    messages: list[dict]

def supervisor_node(state: AgentState) -> AgentState:
    """监督者节点：评估所有专家 Agent，决定下一步"""
    context = state["context"]
    
    # 评估所有专家 Agent
    evaluations = []
    for agent in [guidance_agent, evidence_agent, docgen_agent, research_agent, records_agent]:
        eval_result = agent.evaluate(context)
        evaluations.append(eval_result)
    
    # 选择优先级最高的 Agent
    best_agent = max(evaluations, key=lambda e: e.priority)
    
    return {
        **state,
        "current_agent": best_agent.name,
        "next_action": best_agent.next_step.action,
    }

def guidance_node(state: AgentState) -> AgentState:
    """指引专家节点"""
    context = state["context"]
    result = guidance_agent.execute(context)
    return {**state, "messages": state["messages"] + [result]}

def evidence_node(state: AgentState) -> AgentState:
    """证据专家节点"""
    context = state["context"]
    result = evidence_agent.execute(context)
    return {**state, "messages": state["messages"] + [result]}

def docgen_node(state: AgentState) -> AgentState:
    """文书专家节点"""
    context = state["context"]
    result = docgen_agent.execute(context)
    return {**state, "messages": state["messages"] + [result]}

def research_node(state: AgentState) -> AgentState:
    """研究专家节点"""
    context = state["context"]
    result = research_agent.execute(context)
    return {**state, "messages": state["messages"] + [result]}

def records_node(state: AgentState) -> AgentState:
    """记录专家节点"""
    context = state["context"]
    result = records_agent.execute(context)
    return {**state, "messages": state["messages"] + [result]}

# 构建状态图
workflow = StateGraph(AgentState)

# 添加节点
workflow.add_node("supervisor", supervisor_node)
workflow.add_node("guidance", guidance_node)
workflow.add_node("evidence", evidence_node)
workflow.add_node("docgen", docgen_node)
workflow.add_node("research", research_node)
workflow.add_node("records", records_node)

# 添加边
workflow.add_edge("supervisor", "guidance")
workflow.add_edge("supervisor", "evidence")
workflow.add_edge("supervisor", "docgen")
workflow.add_edge("supervisor", "research")
workflow.add_edge("supervisor", "records")

workflow.add_edge("guidance", END)
workflow.add_edge("evidence", END)
workflow.add_edge("docgen", END)
workflow.add_edge("research", END)
workflow.add_edge("records", END)

# 设置入口
workflow.set_entry_point("supervisor")

# 编译图
app = workflow.compile()
```

### Agent 基类

```python
# app/services/agents/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from app.services.orchestrator.case_context import CaseContext

@dataclass
class EvaluationResult:
    name: str
    priority: int
    next_step: NextStep
    summary: str

@dataclass
class NextStep:
    action: str
    reason: str
    explanation: str
    pipeline_stage: str
    blockers: list[str]
    prefill: dict
    alternatives: list[dict]

class BaseAgent(ABC):
    name: str
    role: str
    
    @abstractmethod
    def evaluate(self, context: CaseContext) -> EvaluationResult:
        """评估当前案件状态，返回优先级和建议"""
        pass
    
    @abstractmethod
    def execute(self, context: CaseContext) -> dict:
        """执行 Agent 任务"""
        pass
```

### 专家 Agent 示例

**指引 Agent**

```python
# app/services/agents/specialists/guidance.py
from app.services.agents.base import BaseAgent, EvaluationResult, NextStep
from app.services.orchestrator.case_context import CaseContext

class GuidanceAgent(BaseAgent):
    name = "guidance"
    role = "维权指引"
    
    def evaluate(self, context: CaseContext) -> EvaluationResult:
        # 分析案件状态
        has_case_type = context.case.case_type is not None
        has_evidence = len(context.evidences) > 0
        
        # 计算优先级
        priority = 0
        if not has_case_type:
            priority = 10  # 高优先级：需要确定案件类型
        elif not has_evidence:
            priority = 5   # 中优先级：需要收集证据
        
        # 确定下一步
        if not has_case_type:
            next_step = NextStep(
                action="navigate",
                reason="需要确定案件类型",
                explanation="请先选择案件类型，以便提供针对性的维权指引",
                pipeline_stage="guidance",
                blockers=[],
                prefill={"step": "select_case_type"},
                alternatives=[],
            )
        else:
            next_step = NextStep(
                action="navigate",
                reason="查看维权步骤",
                explanation="根据您的案件类型，查看具体的维权步骤和渠道",
                pipeline_stage="guidance",
                blockers=[],
                prefill={"case_type": context.case.case_type},
                alternatives=[],
            )
        
        return EvaluationResult(
            name=self.name,
            priority=priority,
            next_step=next_step,
            summary=f"案件类型：{context.case.case_type or '未确定'}",
        )
    
    def execute(self, context: CaseContext) -> dict:
        # 执行指引任务
        return {
            "agent": self.name,
            "action": "provide_guidance",
            "data": {...},
        }
```

**证据 Agent**

```python
# app/services/agents/specialists/evidence.py
from app.services.agents.base import BaseAgent, EvaluationResult, NextStep
from app.services.orchestrator.case_context import CaseContext

class EvidenceAgent(BaseAgent):
    name = "evidence"
    role = "证据整理"
    
    def evaluate(self, context: CaseContext) -> EvaluationResult:
        evidence_count = len(context.evidences)
        has_ocr = all(e.ocr_text for e in context.evidences)
        has_analysis = all(e.analysis for e in context.evidences)
        
        # 计算优先级
        priority = 0
        if evidence_count == 0:
            priority = 10  # 高优先级：需要上传证据
        elif not has_ocr:
            priority = 8   # 高优先级：需要 OCR 识别
        elif not has_analysis:
            priority = 6   # 中优先级：需要证据分析
        
        # 确定下一步
        if evidence_count == 0:
            next_step = NextStep(
                action="navigate",
                reason="需要上传证据",
                explanation="请上传相关证据文件，如合同、工资单、聊天记录等",
                pipeline_stage="evidence",
                blockers=[],
                prefill={"action": "upload"},
                alternatives=[],
            )
        elif not has_ocr:
            next_step = NextStep(
                action="navigate",
                reason="需要 OCR 识别",
                explanation="对上传的证据文件进行 OCR 文字识别",
                pipeline_stage="evidence",
                blockers=[],
                prefill={"action": "ocr"},
                alternatives=[],
            )
        else:
            next_step = NextStep(
                action="navigate",
                reason="进行证据分析",
                explanation="分析证据链的完整性和有效性",
                pipeline_stage="evidence",
                blockers=[],
                prefill={"action": "analyze"},
                alternatives=[],
            )
        
        return EvaluationResult(
            name=self.name,
            priority=priority,
            next_step=next_step,
            summary=f"证据数量：{evidence_count}，OCR：{'完成' if has_ocr else '待处理'}",
        )
    
    def execute(self, context: CaseContext) -> dict:
        # 执行证据任务
        return {
            "agent": self.name,
            "action": "process_evidence",
            "data": {...},
        }
```

### 案件上下文

```python
# app/services/orchestrator/case_context.py
from dataclasses import dataclass
from app.models.case import Case
from app.models.evidence import Evidence
from app.models.document import Document
from app.models.research import ResearchReport

@dataclass
class CaseContext:
    case: Case
    evidences: list[Evidence]
    documents: list[Document]
    research_reports: list[ResearchReport]
    
    @property
    def evidence_count(self) -> int:
        return len(self.evidences)
    
    @property
    def document_count(self) -> int:
        return len(self.documents)
    
    @property
    def has_complete_evidence(self) -> bool:
        return all(e.ocr_text and e.analysis for e in self.evidences)
```

---

## RAG/检索系统

### 架构概览

```
┌─────────────────────────────────────────────────────────┐
│                    统一检索接口                          │
└────────────────────┬────────────────────────────────────┘
                     │
        ┌────────────┼────────────┐
        │            │            │
        ▼            ▼            ▼
   ┌────────┐  ┌──────────┐  ┌────────┐
   │ChromaDB│  │  BM25    │  │External│
   │ 向量   │  │ 关键词   │  │  APIs  │
   └────────┘  └──────────┘  └────────┘
        │            │            │
        └────────────┼────────────┘
                     │
                     ▼
              ┌─────────────┐
              │ RRF 融合排序 │
              └─────────────┘
                     │
                     ▼
              ┌─────────────┐
              │  最终结果    │
              └─────────────┘
```

### ChromaDB 向量检索

```python
# app/services/rag/retriever.py
import chromadb
from chromadb.config import Settings
from app.config import get_settings

settings = get_settings()

# 初始化 ChromaDB 客户端
client = chromadb.HttpClient(
    host=settings.CHROMA_HOST,
    port=settings.CHROMA_PORT,
    settings=Settings(allow_reset=True),
)

# 获取或创建集合
def get_collection(name: str):
    return client.get_or_create_collection(
        name=name,
        metadata={"hnsw:space": "cosine"}
    )

# 向量检索
async def vector_search(query: str, collection_name: str, top_k: int = 10):
    collection = get_collection(collection_name)
    
    # 查询向量
    results = collection.query(
        query_texts=[query],
        n_results=top_k,
        include=["documents", "metadatas", "distances"]
    )
    
    return [
        {
            "id": id,
            "content": doc,
            "metadata": meta,
            "score": 1 - dist,  # 转换为相似度
        }
        for id, doc, meta, dist in zip(
            results["ids"][0],
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0]
        )
    ]
```

### BM25 关键词检索

```python
# app/services/rag/retriever.py
from rank_bm25 import BM25Okapi
import jieba

class BM25Retriever:
    def __init__(self, corpus: list[dict]):
        self.corpus = corpus
        self.corpus_texts = [doc["content"] for doc in corpus]
        
        # 分词
        self.tokenized_corpus = [list(jieba.cut(text)) for text in self.corpus_texts]
        
        # 初始化 BM25
        self.bm25 = BM25Okapi(self.tokenized_corpus)
    
    async def search(self, query: str, top_k: int = 10):
        # 分词查询
        tokenized_query = list(jieba.cut(query))
        
        # 计算分数
        scores = self.bm25.get_scores(tokenized_query)
        
        # 获取 top_k
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
        
        return [
            {
                **self.corpus[i],
                "score": float(scores[i]),
            }
            for i in top_indices
        ]
```

### RRF 融合排序

```python
# app/services/rag/retriever.py
def reciprocal_rank_fusion(results_list: list[list[dict]], k: int = 60) -> list[dict]:
    """
    Reciprocal Rank Fusion (RRF) 融合多路检索结果
    
    Args:
        results_list: 多路检索结果列表
        k: RRF 常数，默认为 60
    
    Returns:
        融合后的排序结果
    """
    # 计算每个文档的 RRF 分数
    rrf_scores = {}
    
    for results in results_list:
        for rank, result in enumerate(results):
            doc_id = result["id"]
            
            if doc_id not in rrf_scores:
                rrf_scores[doc_id] = {
                    "score": 0,
                    "result": result,
                }
            
            # RRF 公式：1 / (k + rank)
            rrf_scores[doc_id]["score"] += 1 / (k + rank + 1)
    
    # 按 RRF 分数排序
    sorted_docs = sorted(
        rrf_scores.values(),
        key=lambda x: x["score"],
        reverse=True
    )
    
    return [
        {
            **doc["result"],
            "rrf_score": doc["score"],
        }
        for doc in sorted_docs
    ]

# 混合检索
async def hybrid_search(query: str, collection_name: str, top_k: int = 10):
    # 并行执行向量检索和 BM25 检索
    vector_results = await vector_search(query, collection_name, top_k=top_k * 2)
    
    # 获取 BM25 语料库
    corpus = await get_corpus(collection_name)
    bm25_retriever = BM25Retriever(corpus)
    bm25_results = await bm25_retriever.search(query, top_k=top_k * 2)
    
    # RRF 融合
    fused_results = reciprocal_rank_fusion([vector_results, bm25_results])
    
    return fused_results[:top_k]
```

### LangChain 链

```python
# app/services/rag/chains.py
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from app.services.llm_client import get_llm

# 研究链
def create_research_chain():
    prompt = ChatPromptTemplate.from_template("""
    基于以下上下文信息，回答用户的问题。
    
    上下文：
    {context}
    
    问题：{question}
    
    请提供详细、准确的回答，并引用相关的法律法规和案例。
    """)
    
    llm = get_llm()
    
    def format_docs(docs):
        return "\n\n".join(doc["content"] for doc in docs)
    
    chain = (
        {
            "context": lambda x: format_docs(x["documents"]),
            "question": lambda x: x["question"],
        }
        | prompt
        | llm
        | StrOutputParser()
    )
    
    return chain

# 文书生成链
def create_document_chain():
    prompt = ChatPromptTemplate.from_template("""
    根据以下信息生成法律文书。
    
    案件信息：
    {case_info}
    
    证据材料：
    {evidence}
    
    文书类型：{doc_type}
    
    模板结构：
    {template}
    
    请生成完整、规范的法律文书。
    """)
    
    llm = get_llm()
    
    chain = (
        prompt
        | llm
        | StrOutputParser()
    )
    
    return chain
```

---

## OCR/多模态处理

### OCR 处理流程

```python
# app/services/evidence/ocr.py
import base64
from app.services.llm_client import get_vision_llm

async def ocr_image(image_bytes: bytes) -> str:
    """
    使用 Qwen-VL-OCR 进行图片文字识别
    """
    # 转换为 base64
    image_base64 = base64.b64encode(image_bytes).decode("utf-8")
    
    # 获取视觉 LLM
    llm = get_vision_llm()
    
    # 构建消息
    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{image_base64}",
                    },
                },
                {
                    "type": "text",
                    "text": "请识别并提取图片中的所有文字内容。",
                },
            ],
        }
    ]
    
    # 调用 API
    response = await llm.chat.completions.create(
        model="qwen-vl-ocr-latest",
        messages=messages,
    )
    
    return response.choices[0].message.content

async def ocr_pdf(pdf_bytes: bytes) -> str:
    """
    对 PDF 进行 OCR 识别
    """
    import fitz  # PyMuPDF
    
    # 打开 PDF
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    
    all_text = []
    
    # 逐页处理
    for page_num in range(len(doc)):
        page = doc[page_num]
        
        # 提取文本
        text = page.get_text()
        
        # 如果文本太少，可能是扫描件，需要 OCR
        if len(text.strip()) < 100:
            # 渲染为图片
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            image_bytes = pix.tobytes("png")
            
            # OCR 识别
            ocr_text = await ocr_image(image_bytes)
            all_text.append(ocr_text)
        else:
            all_text.append(text)
    
    doc.close()
    
    return "\n\n".join(all_text)
```

### PDF 处理

```python
# app/services/evidence/pdf_vision.py
import fitz  # PyMuPDF
from PIL import Image
import io

async def extract_pdf_text(pdf_bytes: bytes) -> str:
    """
    提取 PDF 文本内容
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    
    all_text = []
    for page in doc:
        text = page.get_text()
        all_text.append(text)
    
    doc.close()
    
    return "\n\n".join(all_text)

async def render_pdf_page(pdf_bytes: bytes, page_num: int, dpi: int = 150) -> bytes:
    """
    将 PDF 页面渲染为图片
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    page = doc[page_num]
    
    # 渲染
    mat = fitz.Matrix(dpi / 72, dpi / 72)
    pix = page.get_pixmap(matrix=mat)
    
    # 转换为 PNG
    image_bytes = pix.tobytes("png")
    
    doc.close()
    
    return image_bytes

async def extract_pdf_images(pdf_bytes: bytes) -> list[bytes]:
    """
    提取 PDF 中嵌入的图片
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    
    images = []
    for page in doc:
        image_list = page.get_images()
        
        for img_index, img in enumerate(image_list):
            xref = img[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            images.append(image_bytes)
    
    doc.close()
    
    return images
```

---

## 配置管理

### 环境变量

```bash
# .env.example

# 应用配置
APP_NAME=LaborAid
ENVIRONMENT=development
APP_DEBUG=true
APP_SECRET_KEY=your-secret-key-change-in-production
APP_HOST=0.0.0.0
APP_PORT=8000

# 数据库配置
DATABASE_URL=sqlite+aiosqlite:///./laboraid.db
DATABASE_URL_SYNC=sqlite:///./laboraid.db

# JWT 配置
JWT_SECRET_KEY=your-jwt-secret-key-change-in-production
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=480

# 管理员配置
ADMIN_EMAIL=admin@example.com
INITIAL_ADMIN_NAME=Admin
INITIAL_ADMIN_EMAIL=admin@laboraid.local
INITIAL_ADMIN_PASSWORD=changeme

# LLM 配置（主 LLM）
LLM_API_KEY=your-api-key
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-v4-pro
LLM_MAX_TOKENS=8192

# 视觉 LLM（OCR）
VISION_LLM_API_KEY=your-vision-api-key
VISION_LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
VISION_LLM_MODEL=qwen-vl-ocr-latest
VISION_LLM_MAX_TOKENS=4096

# ChromaDB 配置
CHROMA_HOST=localhost
CHROMA_PORT=8001
CHROMA_COLLECTION=laboraid_docs

# 中国法律 MCP
CHINESE_LAW_MCP_ENABLED=true

# 嵌入模型
EMBEDDING_MODEL=all-MiniLM-L6-v2
EMBEDDING_BASE_URL=

# 企查查 API（可选）
QICHACHA_API_KEY=
QICHACHA_SECRET_KEY=
QICHACHA_API_URL=https://api.qichacha.com

# 上传配置
UPLOAD_DIR=./uploads
MAX_UPLOAD_SIZE_MB=50

# CORS 配置
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

### 配置类

```python
# app/config.py
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # 应用配置
    APP_NAME: str = "LaborAid"
    ENVIRONMENT: str = "development"
    APP_DEBUG: bool = True
    APP_SECRET_KEY: str
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    
    # 数据库配置
    DATABASE_URL: str
    DATABASE_URL_SYNC: str
    
    # JWT 配置
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 480
    
    # 管理员配置
    ADMIN_EMAIL: str
    INITIAL_ADMIN_NAME: str
    INITIAL_ADMIN_EMAIL: str
    INITIAL_ADMIN_PASSWORD: str
    
    # LLM 配置
    LLM_API_KEY: str
    LLM_BASE_URL: str
    LLM_MODEL: str
    LLM_MAX_TOKENS: int = 8192
    
    # 视觉 LLM
    VISION_LLM_API_KEY: str
    VISION_LLM_BASE_URL: str
    VISION_LLM_MODEL: str
    VISION_LLM_MAX_TOKENS: int = 4096
    
    # ChromaDB
    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8001
    CHROMA_COLLECTION: str = "laboraid_docs"
    
    # 中国法律 MCP
    CHINESE_LAW_MCP_ENABLED: bool = True
    
    # 嵌入模型
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    EMBEDDING_BASE_URL: str = ""
    
    # 企查查
    QICHACHA_API_KEY: str = ""
    QICHACHA_SECRET_KEY: str = ""
    QICHACHA_API_URL: str = "https://api.qichacha.com"
    
    # 上传
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE_MB: int = 50
    
    # CORS
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

@lru_cache()
def get_settings() -> Settings:
    return Settings()
```

---

## 测试体系

### 测试结构

```
backend/tests/
├── conftest.py          # pytest 配置和 fixtures
├── test_integration.py  # 集成测试
├── test_agents.py       # Agent 测试
├── test_rag.py          # RAG 测试
├── test_auth.py         # 认证测试
├── test_cases.py        # 案件测试
├── test_evidence.py     # 证据测试
├── test_documents.py    # 文书测试
└── test_search.py       # 搜索测试
```

### pytest 配置

```python
# backend/tests/conftest.py
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.database import Base, get_db

# 测试数据库
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db_session():
    """创建测试数据库会话"""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def client(db_session):
    """创建测试客户端"""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

@pytest.fixture
def auth_headers(client):
    """获取认证头"""
    # 注册
    client.post("/api/v1/auth/register", json={
        "email": "test@example.com",
        "password": "testpass123",
        "name": "Test User",
    })
    
    # 登录
    response = client.post("/api/v1/auth/login", json={
        "email": "test@example.com",
        "password": "testpass123",
    })
    
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
```

### 集成测试示例

```python
# backend/tests/test_integration.py
import pytest
from unittest.mock import patch, AsyncMock

def test_full_case_workflow(client, auth_headers):
    """测试完整案件工作流"""
    # 1. 创建案件
    response = client.post(
        "/api/v1/cases",
        headers=auth_headers,
        json={
            "title": "劳动争议案件",
            "description": "工资拖欠",
            "case_type": "labor_dispute",
        }
    )
    assert response.status_code == 200
    case_id = response.json()["id"]
    
    # 2. 上传证据
    with patch("app.services.evidence.ocr.ocr_image", new_callable=AsyncMock) as mock_ocr:
        mock_ocr.return_value = "识别的文字内容"
        
        response = client.post(
            "/api/v1/evidence/upload",
            headers=auth_headers,
            files={"file": ("test.jpg", b"fake image content")},
            data={"case_id": case_id}
        )
        assert response.status_code == 200
        evidence_id = response.json()["id"]
    
    # 3. 生成文书
    with patch("app.services.agents.specialists.docgen.DocgenAgent.execute") as mock_docgen:
        mock_docgen.return_value = {"content": "仲裁申请书内容..."}
        
        response = client.post(
            "/api/v1/documents/generate",
            headers=auth_headers,
            json={
                "case_id": case_id,
                "doc_type": "complaint",
            }
        )
        assert response.status_code == 200
        document_id = response.json()["id"]
    
    # 4. 验证案件状态
    response = client.get(f"/api/v1/cases/{case_id}", headers=auth_headers)
    assert response.status_code == 200
    case_data = response.json()
    assert len(case_data["evidences"]) == 1
    assert len(case_data["documents"]) == 1
```

### Agent 测试

```python
# backend/tests/test_agents.py
import pytest
from app.services.agents.supervisor import SupervisorAgent
from app.services.orchestrator.case_context import CaseContext
from app.models.case import Case

def test_supervisor_evaluation():
    """测试监督者 Agent 评估"""
    # 创建测试案件
    case = Case(
        id=1,
        title="测试案件",
        description="测试描述",
        case_type="labor_dispute",
    )
    
    context = CaseContext(
        case=case,
        evidences=[],
        documents=[],
        research_reports=[],
    )
    
    # 评估
    supervisor = SupervisorAgent()
    result = supervisor.evaluate(context)
    
    # 验证
    assert result.current_agent == "guidance"
    assert result.next_action == "navigate"
```

### RAG 测试

```python
# backend/tests/test_rag.py
import pytest
from app.services.rag.retriever import hybrid_search, reciprocal_rank_fusion

@pytest.mark.asyncio
async def test_hybrid_search():
    """测试混合检索"""
    query = "劳动争议"
    results = await hybrid_search(query, "test_collection", top_k=5)
    
    assert len(results) <= 5
    assert all("rrf_score" in r for r in results)

def test_rrf_fusion():
    """测试 RRF 融合"""
    results_list = [
        [{"id": "1", "content": "doc1", "score": 0.9}],
        [{"id": "1", "content": "doc1", "score": 0.8}, {"id": "2", "content": "doc2", "score": 0.7}],
    ]
    
    fused = reciprocal_rank_fusion(results_list)
    
    assert len(fused) == 2
    assert fused[0]["id"] == "1"  # 文档 1 应该在第一位
```

---

## 部署架构

### 开发环境

```bash
# 1. 克隆仓库
git clone https://github.com/your-org/LaborAid.git
cd LaborAid

# 2. 后端
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# 编辑 .env 配置 API keys
uvicorn app.main:app --reload --port 8000

# 3. 前端
cd ../frontend
npm install
npm run dev

# 4. ChromaDB
docker run -p 8001:8000 chromadb/chroma:latest
```

### 生产环境

**Docker Compose**

```yaml
# docker-compose.yml
version: '3.8'

services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=production
      - DATABASE_URL=postgresql://user:pass@db:5432/laboraid
    depends_on:
      - db
      - chromadb
    volumes:
      - ./uploads:/app/uploads
  
  frontend:
    build: ./frontend
    ports:
      - "3000:80"
    depends_on:
      - backend
  
  db:
    image: postgres:15
    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
      - POSTGRES_DB=laboraid
    volumes:
      - pgdata:/var/lib/postgresql/data
  
  chromadb:
    image: chromadb/chroma:latest
    ports:
      - "8001:8000"
    volumes:
      - chroma_data:/chroma/chroma

volumes:
  pgdata:
  chroma_data:
```

**Nginx 配置**

```nginx
# nginx.conf
server {
    listen 80;
    server_name laboraid.example.com;
    
    # 前端
    location / {
        proxy_pass http://frontend:80;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    # 后端 API
    location /api {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 监控和日志

**日志配置**

```python
# app/main.py
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)

logger = logging.getLogger(__name__)
```

**健康检查**

```python
# app/api/routers/health.py
from fastapi import APIRouter
from app.database import engine

router = APIRouter()

@router.get("/health")
def health_check():
    try:
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
```

---

## 附录

### A. 依赖清单

**后端**

```txt
# requirements.txt
fastapi==0.109.0
uvicorn[standard]==0.27.0
sqlalchemy==2.0.25
alembic==1.13.1
pydantic==2.5.3
pydantic-settings==2.1.0
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6
httpx==0.26.0
chromadb==0.4.22
langchain==0.1.5
langgraph==0.0.26
rank-bm25==0.2.2
jieba==0.42.1
pymupdf==1.23.8
pillow==10.2.0
openai==1.10.0
python-dotenv==1.0.0
```

**前端**

```json
// package.json
{
  "dependencies": {
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "react-router-dom": "^7.1.1",
    "@tanstack/react-query": "^5.64.0",
    "axios": "^1.7.9",
    "tailwindcss": "^3.4.17",
    "@radix-ui/react-dialog": "^1.1.6",
    "@radix-ui/react-dropdown-menu": "^2.1.6",
    "@radix-ui/react-select": "^2.1.6",
    "@radix-ui/react-toast": "^1.2.6",
    "lucide-react": "^0.469.0",
    "class-variance-authority": "^0.7.1",
    "clsx": "^2.1.1",
    "tailwind-merge": "^2.6.0"
  },
  "devDependencies": {
    "typescript": "^5.7.0",
    "vite": "^6.0.0",
    "@vitejs/plugin-react": "^4.3.4",
    "vitest": "^4.1.8",
    "@testing-library/react": "^16.3.2",
    "@testing-library/jest-dom": "^6.9.1",
    "@testing-library/user-event": "^14.6.1"
  }
}
```

### B. API 文档

启动后端后访问：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### C. 常见问题

**Q: 如何更换 LLM 提供商？**

A: 修改 `.env` 中的 `LLM_BASE_URL` 和 `LLM_API_KEY`，支持任何 OpenAI 兼容的 API。

**Q: 如何禁用 OCR？**

A: 不设置 `VISION_LLM_API_KEY`，系统将跳过 OCR 步骤。

**Q: 如何使用 PostgreSQL？**

A: 修改 `DATABASE_URL` 为 `postgresql://user:pass@host:5432/dbname`。

**Q: 如何部署到生产环境？**

A: 使用 Docker Compose，设置 `ENVIRONMENT=production`，配置安全的密钥。

---

**文档版本**: 1.0  
**最后更新**: 2026-06-09  
**维护者**: Pulse Peng
