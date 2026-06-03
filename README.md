# 劳权智助 · LaborAid

面向劳动者的维权自助与智能法律工具平台。Slogan：*让劳动者维权更省心*。

技术栈：Python 3.11 · FastAPI · React 19 · TypeScript · Vite。  
许可：[MIT](./LICENSE) · 维护：Pulse Peng

---

## 这是什么

LaborAid 是 **前后端一体的劳动者维权工具平台**：用户登录后可在同一界面调用多项 AI 法律能力（文书、证据、检索、合同审查、案情分析等），管理端统一配置模型与知识库。

**两层结构**（并非一功能一智能体）：

| 层次 | 说明 |
|------|------|
| **功能模块** | 导航中的独立工具（`agents.ts` 注册），随时可进入使用 |
| **协作智能体** | 按维权阶段分组（指引 → 证据 → 文书 → 报告 → 记录），Supervisor 根据案件材料推荐主责智能体，并关联多项功能 |

- **用户端**：案情 intake、维权指引、专项通道、证据/文书/检索/合同/计算器等工具、案件级协作调度。
- **管理端**：模型与 API、用户、知识库、统计。普通用户无需填写 Key。

登录入口：`/login`（用户）与 `/login?portal=admin`（管理员）。

---

## 本地运行

**依赖**：Python 3.11+、Node 18+、npm 9+。

**推荐**（在仓库 git 根目录）：

```powershell
copy .env.example LaborAid\backend\.env   # 填入 LLM_API_KEY 等
.\scripts\dev.ps1
```

浏览器打开 http://127.0.0.1:5320 。后端 API 文档：http://127.0.0.1:8010/api/docs 。

> 默认端口 **5320 / 8010**，避免与常见 Vite(5173)、FastAPI(8000) 项目冲突；`dev.ps1` 只会清理这两个端口。

**手动启动**：

```powershell
# 终端 1 — 后端
cd LaborAid\backend
python -m venv venv && .\venv\Scripts\activate
pip install -r requirements.txt
copy ..\..\.env.example .env
python -m uvicorn app.main:app --host 127.0.0.1 --port 8010 --reload

# 终端 2 — 前端
cd LaborAid\frontend
npm install && npm run dev
```

首次启动会创建默认管理员（可在 `.env` 覆盖）：

| | |
|---|---|
| 管理端入口 | http://127.0.0.1:5320/login?portal=admin |
| 账号 | `Admin` 或 `admin@LaborAid.local` |
| 密码 | `123456` |

---

## 仓库布局

当前为 **双层目录**（根目录下还有 `LaborAid/` 子目录）：

```
<git-root>/
├── docs/                 配置与架构文档
├── .env.example          → 复制到 LaborAid/backend/.env
├── scripts/dev.ps1       一键启动
└── LaborAid/
    ├── backend/          FastAPI 应用
    └── frontend/         React 应用
```

若要扁平化为根目录下的 `backend/`、`frontend/`，先停 dev 服务，再执行 `scripts/normalize-project-layout.ps1`。

核心代码路径：

```
LaborAid/backend/app/services/agents/     协作智能体 + Supervisor
LaborAid/backend/app/services/orchestrator/  编排快照、文书流水线
LaborAid/frontend/src/config/agents.ts    功能模块注册（导航）
```

---

## 路由

### 用户端

| 路径 | 页面 |
|------|------|
| `/` | 服务首页 |
| `/guidance` | 维权指引 |
| `/channels` | 专项维权 |
| `/records` | 我的记录 |
| `/cases` | 管理案件 |
| `/documents` | 生成文书（含助手流水线） |
| `/contracts` | 审查合同 |
| `/evidence` | 整理证据 |
| `/search` | 检索法规 |
| `/research` | 分析案情 |
| `/vault` | 我的材料 |
| `/templates` | 文书模板 |
| `/enterprise` | 查询企业 |
| `/tools/limitation` | 时效计算 |
| `/tools/compensation` | 赔偿计算 |
| `/settings` | 个人设置 |

`/knowledge` 已重定向至首页；法律知识库在管理端维护。

### 管理端（前缀 `/admin`）

| 路径 | 页面 |
|------|------|
| `/admin/overview` | 数据概览 |
| `/admin/models` | 模型配置 |
| `/admin/apis` | 接口管理 |
| `/admin/system` | 系统参数 |
| `/admin/users` | 用户管理 |
| `/admin/knowledge` | 知识库 |
| `/admin/templates` | 文书模板 |

---

## 配置要点

环境变量模板见 [.env.example](./.env.example)，说明见 [docs/api-config-locations.md](./docs/api-config-locations.md)。

```env
LLM_API_KEY=
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-chat

VISION_LLM_API_KEY=
VISION_LLM_MODEL=qwen-vl-ocr-latest
```

管理端保存后全平台生效，详见 [docs/model-config-guide.md](./docs/model-config-guide.md)。

案件级协作 API（Supervisor + 阶段智能体 + 四步工作流）：

- `GET /cases/{id}/workflow` — 四步工作流状态（生成案件 → 审查材料 → 生成文书 → 案件报告）
- `GET /cases/{id}/agents` — 各协作智能体状态
- `GET /cases/{id}/agent/next-step` — 调度推荐下一步
- `POST /cases/{id}/agent/ask` — 案情问答
- `POST /cases/{id}/agent/doc-pipeline-stream`（SSE）

---

## 文档

| | |
|---|---|
| [docs/README.md](./docs/README.md) | 文档索引 |
| [docs/product-architecture.md](./docs/product-architecture.md) | 产品架构（v1 设计稿，部分已演进） |
| [LaborAid/docs/special-channels-and-material-vault.md](./LaborAid/docs/special-channels-and-material-vault.md) | 专项通道与材料库 |
| [docs/code-style.md](./docs/code-style.md) | 代码风格 |

---

## 声明

本软件提供信息整理与工具辅助，**不构成法律意见或代理服务**。具体维权策略请咨询执业律师或当地劳动监察、仲裁机构。

---

## 许可

本项目采用 [MIT License](./LICENSE)，Copyright © 2025–2026 Pulse Peng。
