# 劳权智助 · LaborAid 国内模型配置指南

LaborAid 通过 **OpenAI 兼容协议** 接入国内大模型。配置分两层：

1. **`.env` 全局默认** — 后端启动时加载，适合设置主力模型
2. **系统设置 → LLM 配置** — 网页内添加多套模型，可测试连接（后续可扩展为按智能体绑定）

---

## 推荐配置方案

### 方案 A：性价比优先（推荐 — DeepSeek 文本 + 通义 VL 视觉）

**`.env` 文本（文书、分析、检索）：**

```env
LLM_API_KEY=你的DeepSeek密钥
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-v4-pro
LLM_MAX_TOKENS=8192
```

**`.env` 视觉（整理证据图片 OCR）：**

```env
VISION_LLM_API_KEY=你的DashScope密钥
VISION_LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
VISION_LLM_MODEL=qwen-vl-ocr-latest
VISION_LLM_MAX_TOKENS=4096
```

申请通义 Key：https://dashscope.aliyun.com/

首次登录后，Settings 会自动同步「LaborAid 默认」与「通义千问 VL（OCR）」两条配置（若 `.env` 已填 Key）。

### 方案 B：全智谱生态

适合已有智谱 API 账号的用户。

```env
LLM_API_KEY=你的智谱密钥
LLM_BASE_URL=https://open.bigmodel.cn/api/paas/v4
LLM_MODEL=glm-4-flash
```

Settings 再加 `glm-4v-plus` 用于识图。

### 方案 C：长文本优先

适合经常审查整份长合同、大量案情的场景。

```env
LLM_API_KEY=你的Kimi密钥
LLM_BASE_URL=https://api.moonshot.cn/v1
LLM_MODEL=moonshot-v1-128k
LLM_MAX_TOKENS=8192
```

---

## 国内模型对照表

| 厂商 | 配置名 | Base URL | 推荐模型 | 适用场景 |
|------|--------|----------|----------|----------|
| **DeepSeek** | deepseek | `https://api.deepseek.com` | `deepseek-v4-pro`（默认）/ `deepseek-v4-flash` | 文书生成、合同审查、法律研究（主力） |
| **通义千问** | qwen | `https://dashscope.aliyuncs.com/compatible-mode/v1` | `qwen-max` / `qwen-plus` | 复杂推理、结构化输出 |
| **通义千问 OCR** | qwen-vl-ocr | 百炼 | `qwen-vl-ocr-latest` | 整理证据图片文字提取（推荐） |
| **通义千问 VL** | qwen-vl | 百炼 | `qwen-vl-max` | 图像理解、场景描述 |
| **智谱 GLM** | zhipu | `https://open.bigmodel.cn/api/paas/v4` | `glm-4-flash` | 快速响应、检索摘要 |
| **智谱 GLM-4V** | zhipu-v | 同上 | `glm-4v-plus` | 证据照片、扫描 PDF OCR |
| **Kimi** | moonshot | `https://api.moonshot.cn/v1` | `moonshot-v1-128k` | 超长合同、大篇幅案情 |
| **文心一言** | ernie | `https://qianfan.baidubce.com/v2` | `ernie-4.0-8k` | 备选文本模型 |

> 获取 API Key：各厂商开放平台注册后，在控制台创建应用密钥即可。

---

## 按智能体推荐

| 智能体 | 推荐模型 | 原因 |
|--------|----------|------|
| **生成文书**（文书） | DeepSeek `deepseek-v4-pro` | 中文法律文书；轻量场景可换 `deepseek-v4-flash` |
| **审查合同**（合同） | DeepSeek 或 Kimi 128K | 短合同用 DeepSeek；整份长合同用 Kimi |
| **整理证据**（证据 OCR） | 百炼 `qwen-vl-ocr-latest` | 已自动走 `VISION_LLM_*` / Settings OCR 配置 |
| **检索法规**（检索） | GLM Flash `glm-4-flash` | 响应快，摘要够用 |
| **分析案情**（研究） | 通义 `qwen-max` | 多步推理与报告结构较稳 |
| **法律知识库**（知识库） | DeepSeek 或 GLM Flash | 入库与检索以文本为主 |

---

## 在网页中配置（Settings）

1. 登录 LaborAid → **系统设置** → **LLM 配置**
2. 点击 **添加配置**，或从预设模板一键填入
3. 填入：名称、Base URL、API Key、模型名、Max Tokens
4. 点击 **测试连接**，确认返回成功
5. 可将某条配置设为 **默认**

预设模板已内置：智谱、通义、文心、Kimi、DeepSeek 等。

---

## 常见问题

### Q：上传图片后 OCR 失败？

**A：** 检查当前模型是否为**视觉/OCR 模型**。`deepseek-v4-flash`、`glm-4-flash` 等纯文本模型无法识图，整理证据请用 `qwen-vl-ocr-latest` 或 `glm-4v-plus`。

### Q：扫描版 PDF 提取不出文字？

**A：** 文字版 PDF 用本地解析；扫描件会走 LLM 视觉 OCR，同样需要视觉模型，且页数多时会较慢。

### Q：Settings 里配的模型和 `.env` 哪个生效？

**A：** 目前后端业务调用主要读 **`.env` 中的 `LLM_*` 变量**（仍兼容旧版 `CLAUDE_*`）。Settings 中的配置用于管理、测试连接；首次登录且 `.env` 已配 Key 时会自动创建「LaborAid 默认」配置。

### Q：音频证据能自动转文字吗？

**A：** 仅当 API 支持 Whisper 兼容接口时可用（如 OpenAI）。国内模型通常不支持，见 [文件上传与多模态说明](./file-upload-guide.md)。

---

## 密钥安全

- 不要将 `.env` 提交到 Git（已在 `.gitignore` 中忽略）
- 生产环境使用强随机 `APP_SECRET_KEY` 和 `JWT_SECRET_KEY`：

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```
