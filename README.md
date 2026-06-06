

# 劳权智助 · LaborAid

**劳动者维权自助与智能法律工具平台** · *让劳动者维权更省心*

[Python](https://www.python.org/)
[FastAPI](https://fastapi.tiangolo.com/)
[React](https://react.dev/)
[TypeScript](https://www.typescriptlang.org/)
[License](./LICENSE)


| 访问       | 地址                                                                                   |
| -------- | ------------------------------------------------------------------------------------ |
| 🖥️用户端   | [http://127.0.0.1:5320](http://127.0.0.1:5320)                                       |
| 📖API 文档 | [http://127.0.0.1:8010/api/docs](http://127.0.0.1:8010/api/docs)                     |
| 🔐管理端    | [http://127.0.0.1:5320/login?portal=admin](http://127.0.0.1:5320/login?portal=admin) |


[🚀 快速开始](#-快速开始) · [📚 文档](#-文档) · [📖 API 文档](http://127.0.0.1:8010/api/docs)



---

## 🛡️ 项目简介

LaborAid 是 **前后端一体** 的劳动者维权平台：用户从首页选择维权入口，经案情 intake 建案后，在同一账号下使用证据整理、文书生成、法规检索、合同审查、案情报告等 AI 工具；管理端统一配置模型与知识库，普通用户无需自行填写 API Key。


| 入口      | 路径             | 说明                                                  |
| ------- | -------------- | --------------------------------------------------- |
| 🚀开始维权  | `/`（首页 intake） | **专项维权**：农民工 / 实习生 / 女职工等结构化表单；**普通入口**：自由文字 + 可选图片 |
| 🔗办事资源  | `/guidance`    | 全国 31 省官方申诉、仲裁、法援、热线等外链与一键办事（不重复案由步骤）               |
| 📂我的记录  | `/records`     | 案件、文书、研究报告、最近工具                                     |
| 🧰法律工具箱 | 见下表「工具路由」      | 检索、文书、证据、合同、研究、案件、模板、计算器等                           |


建案后，案由与证据清单写入案件 `ai_snapshot`，证据页与就绪度 API 可跨会话恢复，无需依赖浏览器临时 session。

---

## ✨ 核心功能

### 📋 维权流程（服务层）


| 模块      | 功能                 | 说明                                                                                              |
| ------- | ------------------ | ----------------------------------------------------------------------------------------------- |
| 🔀入口分流  | 专项 / 普通            | 专项走 `ChannelIntakeWizard` + `POST /intake/structured`；普通走 `IntakeDesk` + `POST /intake/analyze` |
| 📋维权安排  | 步骤计划               | 建案 → 证据 → 文书 → 报告；支持一键按推荐计划跳转                                                                   |
| 🤖案件协作  | Supervisor + 阶段智能体 | `GET /cases/{id}/workflow`、`/agents`、`/agent/next-step`                                         |
| 🏛️办事资源 | 权威外链               | 省级平台配置 `official-platforms.json`，省份与报告弹窗联动                                                      |


### 🧰 法律工具箱（工具层）


| 模块          | 路由                                        | 说明                       |
| ----------- | ----------------------------------------- | ------------------------ |
| 📁管理案件      | `/cases`                                  | 案件 CRUD、就绪度、材料包导出        |
| 📎整理证据      | `/evidence`                               | 上传、OCR、证据链分析、intake 清单对照 |
| 📝生成文书      | `/documents`                              | AI 文书 + 四步助手流水线（SSE）     |
| 📄审查合同      | `/contracts`                              | 劳动合同等风险审查                |
| 🔍检索法规      | `/search`                                 | 法规 / 案例检索                |
| 📊分析案情      | `/research`                               | 深度研究报告                   |
| 🗄️我的材料     | `/vault`                                  | 个人材料库；证据上传可自动归档          |
| 📑文书模板      | `/templates`                              | 模板浏览与管理端维护               |
| 🏢查询企业      | `/enterprise`                             | 企业信息查询                   |
| 🧮时效 / 赔偿计算 | `/tools/limitation`、`/tools/compensation` | 计算器工具                    |


### ⚙️ 管理端


| 模块        | 路由                            | 说明          |
| --------- | ----------------------------- | ----------- |
| 📈数据概览    | `/admin/overview`             | 统计看板        |
| 🤖模型 / 接口 | `/admin/models`、`/admin/apis` | LLM、OCR、连通性 |
| 👥用户管理    | `/admin/users`                | 账号与角色       |
| 📚知识库     | `/admin/knowledge`            | 法规知识维护与同步   |
| 📑文书模板    | `/admin/templates`            | 模板 CRUD     |
| ⚙️系统参数    | `/admin/system`               | 全局配置        |


---

## ⚡ 技术栈

### 🏗️ 核心架构

| 层级 | 技术 | 说明 |
|------|------|------|
| 🐍 **后端** | Python 3.11 · FastAPI · SQLAlchemy | REST API、案件与 intake 服务 |
| ⚛️ **前端** | React 19 · TypeScript · Vite · Tailwind | 用户端 + 管理端 SPA |
| 🗃️ **数据** | PostgreSQL · Redis · ChromaDB | 业务数据 · 缓存 · 向量存储 |

### 🤖 AI 技术栈

| 技术 | 框架/库 | 用途 |
|------|---------|------|
| 🧠 **LLM 编排** | LangChain (LCEL) | 可组合的 Prompt Pipeline |
| 🔄 **Agent 调度** | LangGraph | 多 Agent 状态机 |
| 🔍 **混合检索** | ChromaDB + BM25 + RRF | 向量检索 + 关键词检索 + 倒数排名融合 |
| 📝 **中文分词** | jieba | 法律文本预处理 |
| 👁️ **视觉 OCR** | qwen-vl-ocr · pypdf · PyMuPDF | 证据图片/扫描件识别 |
| 📊 **Embedding** | all-MiniLM-L6-v2 | 文本向量化 |

### 📚 详细文档

完整的 AI 技术架构说明请查阅：[docs/ai-architecture.md](./docs/ai-architecture.md)


---

## 🚀 快速开始

### 📌 环境要求

- 🐍 Python **3.11+**
- 📦 Node.js **18+**、npm **9+**
- 🐳 （可选）Docker — 当前以本地 dev 脚本为主

### ▶️ 启动步骤

在 **git 仓库根目录** 执行：

```powershell
copy .env.example LaborAid\backend\.env   # 填入 LLM_API_KEY 等
**方式一（推荐）**：在仓库根目录 **双击 `start-laboraid.bat`**（英文名，避免路径空格与中文编码问题），会自动打开前后端窗口并打开浏览器。停止时双击 `stop-laboraid.bat` 或关闭两个 PowerShell 窗口。详见 [快速启动.md](./快速启动.md)。

**方式二**：PowerShell 执行：

```powershell
.\scripts\dev.ps1
```

**方式三（Cursor / VS Code）**：`Ctrl+Shift+P` → **Tasks: Run Task** → **LaborAid: 启动开发环境**。

浏览器打开用户端；API 交互式文档见上表。

> 默认端口 **5320 / 8010**，避免与常见 Vite(5173)、Uvicorn(8000) 冲突；启动脚本仅清理这两个端口上的旧进程。

**手动启动**（双终端）：

```powershell
# 终端 1 — 后端
cd LaborAid\backend
python -m venv venv; .\venv\Scripts\activate
pip install -r requirements.txt
copy ..\..\.env.example .env
python -m uvicorn app.main:app --host 127.0.0.1 --port 8010 --reload

# 终端 2 — 前端
cd LaborAid\frontend
npm install; npm run dev
```

### 🌐 服务端口


| 服务        | 地址                                                               |
| --------- | ---------------------------------------------------------------- |
| 🖥️前端     | [http://127.0.0.1:5320](http://127.0.0.1:5320)                   |
| ⚙️后端 API  | [http://127.0.0.1:8010](http://127.0.0.1:8010)                   |
| 📖Swagger | [http://127.0.0.1:8010/api/docs](http://127.0.0.1:8010/api/docs) |


### 🔑 默认管理员（首次启动）


| 项   | 值                                                                                    |
| --- | ------------------------------------------------------------------------------------ |
| 入口  | [http://127.0.0.1:5320/login?portal=admin](http://127.0.0.1:5320/login?portal=admin) |
| 账号  | `Admin` 或 `admin@LaborAid.local`                                                     |
| 密码  | `123456`（可在 `.env` 覆盖）                                                               |


---

## 🏗️ 项目结构

当前为 **git 根 + `LaborAid/` 子目录** 双层布局：

```
<git-root>/
├── docs/                      产品、配置、规范文档
├── resources/verification/    功能验证清单
├── .env.example               → 复制到 LaborAid/backend/.env
├── start-laboraid.bat         双击一键启动（推荐，英文名）
├── stop-laboraid.bat          双击停止本地服务
├── 快速启动.md                启动说明（给日常自用）
├── scripts/dev.ps1            一键启动前后端
├── scripts/stop.ps1           释放 5320 / 8010 端口
└── LaborAid/
    ├── backend/app/
    │   ├── api/routers/       REST（含 intake、cases、orchestrator）
    │   ├── services/
    │   │   ├── intake/        分析、结构化 intake、案件绑定
    │   │   ├── agents/        协作智能体
    │   │   └── orchestrator/  快照、文书流水线
    │   └── tests/
    └── frontend/src/
        ├── config/labor/      guidance、channels、intake-scenarios、official-platforms
        ├── components/intake/ EntryGate、专项向导、动态表单
        └── pages/
```

扁平化目录（可选）：`scripts/normalize-project-layout.ps1`

---

## 🧭 路由一览


| 路径                    | 页面                 | 备注                               |
| --------------------- | ------------------ | -------------------------------- |
| `/`                   | 🏠服务首页 + 维权 intake | `?intake=special` / `general` 深链 |
| `/guidance`           | 🔗办事资源             | 官方平台与热线                          |
| `/records`            | 📂我的记录             |                                  |
| `/channels`           | ↪️重定向              | 重定向至首页专项入口                       |
| `/channels/:id`       | ↪️旧链接兼容            | 跳转首页并保留 channel 参数               |
| `/cases`              | 📁管理案件             |                                  |
| `/evidence`           | 📎整理证据             |                                  |
| `/documents`          | 📝生成文书             |                                  |
| `/contracts`          | 📄审查合同             |                                  |
| `/search`             | 🔍检索法规             |                                  |
| `/research`           | 📊分析案情             |                                  |
| `/vault`              | 🗄️我的材料            |                                  |
| `/templates`          | 📑文书模板             |                                  |
| `/enterprise`         | 🏢查询企业             |                                  |
| `/tools/limitation`   | 🧮时效计算             |                                  |
| `/tools/compensation` | 💰赔偿计算             |                                  |
| `/settings`           | ⚙️个人设置             |                                  |
| `/knowledge`          | ↪️重定向              | 重定向首页；知识库在管理端                    |


登录：`/login`（用户）· `/login?portal=admin`（管理）

---

## 🔧 配置要点

环境变量模板：[.env.example](./.env.example) · 说明：[docs/api-config-locations.md](./docs/api-config-locations.md)

### 🤖 AI 模型

```env
LLM_API_KEY=
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-chat

VISION_LLM_API_KEY=
VISION_LLM_MODEL=qwen-vl-ocr-latest
```

管理端保存后全平台生效 → [docs/model-config-guide.md](./docs/model-config-guide.md)

### 📡 案件协作 API（节选）


| 方法   | 路径                                      | 说明                  |
| ---- | --------------------------------------- | ------------------- |
| GET  | `/cases/{id}/readiness`                 | 材料就绪度 + intake 证据清单 |
| GET  | `/cases/{id}/workflow`                  | 四步工作流               |
| GET  | `/cases/{id}/agents`                    | 协作智能体状态             |
| POST | `/cases/{id}/agent/ask`                 | 案情问答                |
| POST | `/cases/{id}/agent/doc-pipeline-stream` | 文书流水线（SSE）          |
| POST | `/intake/analyze`                       | 普通入口案情分析            |
| POST | `/intake/structured`                    | 专项结构化 intake        |
| POST | `/intake/create-case`                   | 建案并绑定 intake 快照     |


---

## 📚 文档


| 文档                                                                                                                | 说明                |
| ----------------------------------------------------------------------------------------------------------------- | ----------------- |
| 📑 [docs/README.md](./docs/README.md)                                                                             | 文档索引与阅读顺序         |
| 🏛️ [docs/product-architecture.md](./docs/product-architecture.md)                                                | 产品架构（含当前 IA 演进说明） |
| ⚖️ [LaborAid/docs/special-channels-and-material-vault.md](./LaborAid/docs/special-channels-and-material-vault.md) | 专项 intake 与材料库    |
| 🔧 [docs/api-config-locations.md](./docs/api-config-locations.md)                                                 | 环境变量与配置优先级        |
| 🤖 [docs/model-config-guide.md](./docs/model-config-guide.md)                                                     | LLM / OCR 配置      |
| 📎 [docs/file-upload-guide.md](./docs/file-upload-guide.md)                                                       | 上传与多模态            |
| ✍️ [docs/code-style.md](./docs/code-style.md)                                                                     | 代码风格              |
| ✅ [resources/verification/](./resources/verification/)                                                            | 功能验证材料包           |


---

## ⚠️ 声明

本软件提供信息整理与工具辅助，**不构成法律意见或代理服务**。具体维权策略请咨询执业律师或当地劳动监察、仲裁机构。

---

## 📄 许可

[MIT License](./LICENSE) · Copyright © 2025–2026 Pulse Peng

---



**劳权智助 · LaborAid** — *让劳动者维权更省心*

