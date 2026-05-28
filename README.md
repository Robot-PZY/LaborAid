# 劳权智助 · LaborAid

一个面向劳动者维权场景的实用型 AI Web 项目：围绕“咨询 → 建案 → 证据 → 文书 → 分析”的主线流程，帮助用户更高效地完成材料准备与信息核验。

[License: MIT](LICENSE) · [Python](https://python.org) · [React](https://react.dev) · [FastAPI](https://fastapi.tiangolo.com)

---

## 🎯 项目定位

- 面向劳动者维权场景，提供从“描述问题”到“整理材料”的一站式流程
- 站内聚焦材料准备与信息整理，正式投诉/仲裁仍以官方渠道为准
- 支持用户端 + 管理端，普通用户可直接使用，无需额外配置 Key

## 💡 设计原则

- 先流程后工具：优先让用户知道“下一步做什么”
- 可执行优先：输出尽量是可直接复制、下载、提交的材料
- 稳定可控：关键能力支持回退策略与人工复核
- 低门槛表达：文案尽量通俗，减少法律术语负担

---

## 📌 核心能力

### 用户端（常用）

| 模块 | 路由 | 说明 |
|------|------|------|
| 快速咨询 | `/` | 输入案情，自动生成维权安排 |
| 管理案件 | `/cases` | 案件全流程管理 |
| 整理证据 | `/evidence` | 文件上传、OCR、结构化整理 |
| 生成文书 | `/documents` | 单份/批量文书生成 |
| 审查合同 | `/contracts` | 合同条款风险识别 |
| 检索法规 | `/search` | 法规/案例检索 |
| 分析案情 | `/research` | 研究报告与建议 |
| 维权专区 | `/channels` | 农民工/实习生/女职工通道 |
| 我的材料 | `/vault` | 账号级材料沉淀 |
| 我的记录 | `/records` | 案件、文书、证据、报告汇总 |

### 管理端

| 模块 | 路由 | 说明 |
|------|------|------|
| 数据概览 | `/admin` | 用户与业务统计 |
| 模型配置 | `/admin/models` | 文本 LLM / 视觉 OCR |
| 接口管理 | `/admin/apis` | 外部法律数据源 |
| 系统参数 | `/admin/system` | 通用系统配置 |
| 用户管理 | `/admin/users` | 角色与状态 |

管理端入口：<http://localhost:5173/login?portal=admin>

## 🖼️ 使用过程（截图）

> 可在此放 3~5 张核心流程截图：快速咨询、生成文书、整理证据、检索法规、管理端配置。
> 建议统一放到 `resources/screenshots/` 目录，并按以下命名：
>
> - `home-intake.png`
> - `doc-generate.png`
> - `evidence-ocr.png`
> - `search-laws.png`
> - `admin-models.png`
>
> 示例（放图后取消注释）：
>
> ```md
> ![快速咨询](./resources/screenshots/home-intake.png)
> ![生成文书](./resources/screenshots/doc-generate.png)
> ```

---

## 🚀 快速开始

### 1) 环境要求

- Python 3.12+
- Node.js 18+
- npm 9+

### 2) 启动后端

```powershell
cd LaborAid/backend
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
copy ..\.env.example .env
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 3) 启动前端

```powershell
cd LaborAid/frontend
npm install
npm run dev
```

### 4) 打开地址

- 用户端：<http://localhost:5173>
- 管理端：<http://localhost:5173/login?portal=admin>
- Swagger：<http://localhost:8000/api/docs>
- ReDoc：<http://localhost:8000/api/redoc>

---

## ⚠️ 最小可用配置（.env）

```env
# 文本模型（必填）
LLM_API_KEY=
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-v4-pro

# 图片 OCR（上传图片时必填）
VISION_LLM_API_KEY=
VISION_LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
VISION_LLM_MODEL=qwen-vl-ocr-latest
```

👉 完整变量请看：[`docs/api-config-locations.md`](./docs/api-config-locations.md)

---

## 🧭 推荐阅读顺序

1. [`docs/README.md`](./docs/README.md)：文档总索引
2. [`docs/api-config-locations.md`](./docs/api-config-locations.md)：配置项与位置
3. [`docs/model-config-guide.md`](./docs/model-config-guide.md)：模型配置实践
4. [`resources/verification/README.md`](./resources/verification/README.md)：验证材料总览

---

## ✅ 验证与验收

若你要做功能回归或演示，请按顺序执行：

1. [`resources/verification/00-验证环境与账号.md`](./resources/verification/00-验证环境与账号.md)
2. [`resources/verification/01-登录注册验证.md`](./resources/verification/01-登录注册验证.md)
3. [`resources/verification/02-维权前台验证.md`](./resources/verification/02-维权前台验证.md)
4. 继续按 `03` 到 `10` 模块化验证

---

## 📁 项目结构

```text
LaborAid/
├── LaborAid/
│   ├── backend/        # FastAPI
│   └── frontend/       # React + TypeScript
├── docs/               # 产品/配置/开发文档
├── resources/          # 验证材料与品牌资源
└── scripts/            # 工具脚本
```

---

## 许可与声明

- 协议：MIT（见 [`LICENSE`](./LICENSE)）
- AI 输出仅供辅助整理，不构成法律意见
- 涉及金额、时效、胜诉判断等请以人工和官方渠道复核

---

**作者**：Pulse Peng  
欢迎通过 Issue 提交建议与问题。