# 劳权智助 · API 配置位置一览

> 本文只说明“填哪里、哪些必填、如何快速自检”。仓库不包含真实密钥。

---

## ✅ 先看最小必配（建议先跑通）

```env
# 文本模型（必填）
LLM_API_KEY=
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-v4-pro
LLM_MAX_TOKENS=8192

# 视觉 OCR（上传图片时必填）
VISION_LLM_API_KEY=
VISION_LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
VISION_LLM_MODEL=qwen-vl-ocr-latest
VISION_LLM_MAX_TOKENS=4096
```

---

## 1) 文本 LLM（必填）

**文件**：仓库根目录 `.env` 或 `LaborAid/backend/.env`（二者择一，推荐复制根目录 `.env.example`）

```env
# ── 在此填入你的大模型 API ──────────────────────────
LLM_API_KEY=                          # ← 填入 API Key（DeepSeek / 通义 / 智谱等）
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-v4-pro
LLM_MAX_TOKENS=8192
```

| 变量 | 说明 |
|------|------|
| `LLM_API_KEY` | **必填**，否则 AI 功能不可用 |
| `LLM_BASE_URL` | OpenAI 兼容接口地址 |
| `LLM_MODEL` | 模型名称 |
| `LLM_MAX_TOKENS` | 单次最大输出 token |

兼容旧名：`CLAUDE_API_KEY` 等（未设 `LLM_*` 时回退读取）。

**代码入口**：`LaborAid/backend/app/config.py` → `Settings.LLM_*`

---

## 2) 视觉 / OCR（图片上传时必填）

**与文本 LLM 分离**：文本生成与 OCR 可使用不同服务商。

```env
VISION_LLM_API_KEY=                   # ← 阿里云 DashScope API Key
VISION_LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
VISION_LLM_MODEL=qwen-vl-ocr-latest      # OCR 文字识别；图像理解可用 qwen-vl-max
VISION_LLM_MAX_TOKENS=4096
```

| 变量 | 说明 |
|------|------|
| `VISION_LLM_API_KEY` | 整理证据/法律知识库/生成文书 **上传图片** OCR 必填 |
| 申请地址 | https://dashscope.aliyun.com/ |

**解析优先级**：管理端「模型配置」里名称含「视觉/OCR」或模型含 `vl/ocr` → `.env` 的 `VISION_LLM_*`；**不再回退到文本主模型**（未配视觉则 OCR 会明确报错）。

**代码入口**：
- `LaborAid/backend/app/services/llm_resolver.py` → `resolve_vision_llm()`
- `LaborAid/backend/app/services/evidence/ocr.py`
- 查询当前视觉配置：`GET /api/v1/llm-settings/active-vision`

---

## 3) 管理端模型配置（推荐）

**路径**：管理员登录 → **管理端** → **模型配置**（`/admin/models`）

- 分开展示 **文本主模型** 与 **视觉/OCR 模型**
- 顶部横幅显示当前全站生效配置
- 首次进入且 `.env` 已配 Key 时，自动种子「劳权智助 默认」与「通义千问 OCR」条目
- 文本调用优先使用「默认主模型」；视觉识图使用 OCR 配置或 `VISION_LLM_*`
- 接口：`GET /api/v1/llm-settings/active`（文本）、`GET /api/v1/llm-settings/runtime-summary`（管理端汇总）

**代码入口**：
- 前端：`LaborAid/frontend/src/pages/Settings.tsx`、`LaborAid/frontend/src/pages/admin/AdminConfig.tsx`
- 后端：`LaborAid/backend/app/api/routers/llm_settings.py`

---

## 4) 外部数据源（可选）

**路径**：系统设置 → **外部 API**

| 预设 | 用途 | Key 填入位置 |
|------|------|--------------|
| 北大法宝 | 法规检索 | 管理端外部 API 表单 |
| 元典 / 智合 | 案例法规 | 同上 |
| Tavily | 网络检索 | 同上 |

**环境变量**（已接入：企查查「查询企业」、得理法律「法规/案例检索」）：

```env
QICHACHA_API_KEY=                     # ← 企查查 AppKey
QICHACHA_SECRET_KEY=                  # ← 企查查 SecretKey
QICHACHA_API_URL=https://api.qichacha.com

DELILEGAL_ENABLED=false               # ← true 时启用得理法律数据源
DELILEGAL_BASE_URL=https://openapi.delilegal.com
DELILEGAL_APPID=                      # ← 得理 AppID
DELILEGAL_SECRET=                     # ← 得理 Secret
```

**代码入口**：
- 企业风险扫描：`LaborAid/backend/app/services/enterprise/qichacha.py`
- API 路由：`GET /api/v1/enterprise/scan`、`/status`
- 前端页面：`/enterprise`（查询企业）
- 得理适配器：`LaborAid/backend/app/services/data_sources/delilegal.py`
- 启动注册：`LaborAid/backend/app/main.py`（读取 `DELILEGAL_*`）

外部法律数据库管理代码：`LaborAid/backend/app/api/routers/external_apis.py`

---

## 5) 向量 / Embedding（可选）

```env
CHROMA_HOST=localhost
CHROMA_PORT=8001
CHROMA_COLLECTION=LaborAid_docs
EMBEDDING_MODEL=all-MiniLM-L6-v2
EMBEDDING_BASE_URL=                   # ← 自定义 Embedding API（留空用本地模型）
```

**代码入口**：`LaborAid/backend/app/services/vector/store.py`

---

## 6) 北大法宝 MCP（可选）

```env
CHINESE_LAW_MCP_ENABLED=true          # 需本机安装 @ansvar/chinese-law-mcp
```

**代码入口**：`LaborAid/backend/app/services/data_sources/beida_fabao.py`

---

## 7) 安全密钥（生产必改）

```env
APP_SECRET_KEY=                       # ← 生产环境必填随机串
JWT_SECRET_KEY=                       # ← 生产环境必填随机串
```

生成方式：

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

---

## 🔍 快速检查清单

- [ ] `LLM_API_KEY` 已填入（DeepSeek V4 文本）
- [ ] `VISION_LLM_API_KEY` 已填入（通义 VL 图片 OCR）
- [ ] `LLM_BASE_URL` / `LLM_MODEL` 与 Key 对应厂商一致
- [ ] 管理端模型配置页「测试连接」通过
- [ ] 图片 OCR 场景另配视觉模型（见 [model-config-guide.md](./model-config-guide.md)）
- [ ] （可选）`QICHACHA_API_KEY` + `QICHACHA_SECRET_KEY` 已填入，劳动者可站内「查询企业」
- [ ] （可选）`DELILEGAL_ENABLED=true` 且 `DELILEGAL_APPID`/`DELILEGAL_SECRET` 已填入，法规/案例检索可接入得理
