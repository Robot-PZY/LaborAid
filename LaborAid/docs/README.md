# LaborAid 子项目文档

本目录保留 **与代码同级的专题说明**。通用文档在仓库根目录 [`docs/`](../../docs/README.md)。

---

## 本目录

| 文档 | 说明 |
|------|------|
| [专项维权 intake 与材料库](./special-channels-and-material-vault.md) | 首页专项表单、办事资源、材料库、快照闭环 |

---

## 根目录文档

| 文档 | 说明 |
|------|------|
| [文档总览](../../docs/README.md) | 索引与阅读顺序 |
| [产品架构](../../docs/product-architecture.md) | 设计稿 + §1.4 当前实现 |
| [API 配置位置](../../docs/api-config-locations.md) | 环境变量 |
| [模型配置指南](../../docs/model-config-guide.md) | LLM / OCR |
| [文件上传说明](../../docs/file-upload-guide.md) | 多模态与 OCR |
| [代码风格](../../docs/code-style.md) | 规范 |

---

## 配置与代码快链

| 资源 | 路径 |
|------|------|
| 项目 README | [../../README.md](../../README.md) |
| 环境变量 | [../../.env.example](../../.env.example) → `LaborAid/backend/.env` |
| 功能模块注册 | `frontend/src/config/agents.ts` |
| 劳权 JSON 配置 | `frontend/src/config/labor/` |
| Intake 组件 | `frontend/src/components/intake/` |
