<div align="center">

# LaborAid

**连接法律与普通人的桥梁**

[![Python](https://img.shields.io/badge/Python-3.12+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![React](https://img.shields.io/badge/React-19-61DAFB?style=flat-square&logo=react&logoColor=black)](https://react.dev)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.7-3178C6?style=flat-square&logo=typescript&logoColor=white)](https://typescriptlang.org)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)

*劳动者维权服务 + 法律智能工具箱 —— 以 Nexus 为枢纽连接指引与专业工具*

[双端说明](#-双端架构) · [快速开始](#-快速开始) · [文档](#-文档)

</div>

---

## 🎯 双端架构

LaborAid 分为 **用户端** 与 **管理端**，登录入口分离，职责清晰：

| 端 | 登录入口 | 主要能力 |
|:---|:---------|:---------|
| **用户端** | 登录页 → 用户登录 | 维权指引、官方法律服务跳转、AI 工具（文书/证据/检索等）、个人记录 |
| **管理端** | 登录页 → 管理员登录 | 模型配置、外部 API、系统参数、用户管理、平台统计 |

> 普通用户的模型与 API 由平台统一配置；管理员在管理端维护，无需在用户设置中填写 Key。

---

## ✨ 用户端功能

| 模块 | 路由 | 说明 |
|:-----|:-----|:-----|
| 🏠 **服务首页** | `/` | 维权入口、官方渠道、常用工具 |
| 🧭 **维权指引** | `/guidance` | 按案由步骤 + 跳转 12348 / 人社 / 法规库 |
| 📂 **我的记录** | `/records` | 案件、文书、证据、研究汇总 |
| 📝 **文墨** | `/documents` | AI 法律文书起草 |
| 🛡️ **盾律** | `/contracts` | 合同风险审查 |
| 🔗 **证链** | `/evidence` | 证据 OCR 与分析 |
| 🔍 **法眼** | `/search` | 法规/案例检索 |
| 📚 **研法** / **智库** | `/research` `/knowledge` | 研究与知识库 |
| 📁 **案管** | `/templates` | 案件与模板 |
| 👤 **个人设置** | `/settings` | 账号信息（不含模型配置） |

---

## ⚙️ 管理端功能

| 模块 | 路由 | 说明 |
|:-----|:-----|:-----|
| 📊 **数据概览** | `/admin` | 用户与业务统计、7 日趋势 |
| 🤖 **模型配置** | `/admin/models` | 文本 LLM、视觉/OCR 模型 |
| 🔌 **接口管理** | `/admin/apis` | 外部法规/案例 API |
| 🖥️ **系统参数** | `/admin/system` | 向量库、通用配置 |
| 👥 **用户管理** | `/admin/users` | 角色、启用状态 |

---

## 📁 目录整理（重要）

从旧仓库克隆后，若存在 **`LaborAid/LaborAid`** 双层目录，请先整理再开发：

1. 关闭 Cursor、停止 `npm run dev` 与 `uvicorn`
2. 在 **含 `.git` 的文件夹** 中执行：

```powershell
.\scripts\normalize-project-layout.ps1
```

脚本会将 `backend`、`frontend` 提升到根目录，并把文件夹重命名为 **`LaborAid`**。完成后用 Cursor 重新打开 `...\LaborAid`。

---

## 🚀 快速开始

### 环境要求

- **Python** 3.12+
- **Node.js** 18+
- **npm** 9+

### 启动步骤

```powershell
# 1. 进入项目根目录（推荐文件夹名 LaborAid，见下方「目录整理」）
cd "F:\Undergraduate\Skill Learning\LaborAid"
# 若仍为旧路径 LaborAid，可先运行 scripts/normalize-project-layout.ps1

# 2. 启动后端
cd backend
python -m venv venv
.\venv\Scripts\activate          # macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
copy ..\.env.example .env        # 编辑 .env 填入 API Key
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 3. 启动前端（新开终端）
cd ..\frontend
npm install
npm run dev
```

浏览器访问 **http://localhost:5173**

**初始管理员**（首次启动自动创建，可在 `.env` 修改）：

| 项目 | 值 |
|------|-----|
| 入口 | http://localhost:5173/login?portal=admin |
| 账号 | `Admin` 或 `admin@LaborAid.local` |
| 密码 | `123456` |

---

## 🏗️ 项目结构

```
LaborAid/
├── backend/                 # FastAPI 后端
│   └── app/
│       ├── api/routers/     # REST API（含 admin、guidance、user）
│       └── services/        # AI 引擎与业务逻辑
├── frontend/                # React 前端
│   └── src/
│       ├── config/          # 品牌、智能体、劳权配置
│       ├── pages/           # 用户端页面
│       └── pages/admin/     # 管理端页面
├── docs/                    # 使用与架构文档
└── .env.example             # 环境变量模板
```

---

## 📚 文档

| 文档 | 说明 |
|------|------|
| [文档目录](./docs/README.md) | 全部文档索引 |
| [产品架构](./docs/product-architecture.md) | 服务平台 + 工具箱设计 |
| [API 配置位置](./docs/api-config-locations.md) | API Key 填哪里 |
| [模型配置指南](./docs/model-config-guide.md) | 国内 LLM 推荐 |
| [代码风格](./docs/code-style.md) | 命名与规范 |

---

## 🔌 AI 模型（简要）

```env
LLM_API_KEY=
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-chat

VISION_LLM_API_KEY=
VISION_LLM_MODEL=qwen-vl-ocr-latest
```

管理端配置后全平台生效。详见 [docs/model-config-guide.md](./docs/model-config-guide.md)。

---

## 📖 API 文档

- Swagger: http://localhost:8000/api/docs
- ReDoc: http://localhost:8000/api/redoc

---

## 📄 许可证

[MIT License](LICENSE) — LaborAid Contributors

---

<div align="center">

**LaborAid** — 连接法律与普通人的桥梁

</div>
