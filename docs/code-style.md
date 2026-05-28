# 劳权智助 · LaborAid 代码风格约定

## 前端

- 品牌 / 智能体文案 → `src/config/brand.ts`、`src/config/agents.ts`
- localStorage key → `src/lib/storage-keys.ts`
- 格式化：`npm run format`（Prettier）
- 检查：`npm run lint`（ESLint）

## 后端

- LLM / API 配置 → `.env` 的 `LLM_*`（见 [api-config-locations.md](./api-config-locations.md)）
- Prompt 人格 → `app/prompts/persona.py`
- 业务 Prompt → 各 `services/*/prompts` 或引擎内，须引用 persona
- 检查：`ruff check app/`（需安装 ruff）

## 禁止

- 在仓库中提交真实 API Key
- 新增 `LaborAid_*` 命名（仅 legacy localStorage 迁移映射，新代码用 `LaborAid_*`）
