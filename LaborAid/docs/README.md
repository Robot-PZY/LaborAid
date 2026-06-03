# LaborAid 子项目文档

本目录仅保留 **与代码同级的专题说明**。通用文档在仓库根目录 [`docs/`](../../docs/README.md)。

## 本目录

| 文档 | 说明 |
|------|------|
| [专项维权通道 & 材料库](./special-channels-and-material-vault.md) | 农民工/实习生/女职工专区、材料库 |

## 根目录文档（配置 / 架构 / 规范）

| 文档 | 说明 |
|------|------|
| [文档总览](../../docs/README.md) | 索引与阅读顺序 |
| [产品架构](../../docs/product-architecture.md) | v1 设计稿（管理员后台等已落地，以 README 为准） |
| [API 配置位置](../../docs/api-config-locations.md) | 环境变量 |
| [模型配置指南](../../docs/model-config-guide.md) | LLM / OCR |
| [文件上传说明](../../docs/file-upload-guide.md) | 多模态与 OCR |
| [代码风格](../../docs/code-style.md) | 规范 |

## 快速链接

- 项目 README：[../../README.md](../../README.md)
- 环境变量：复制 [../../.env.example](../../.env.example) → `LaborAid/backend/.env`
- 智能体注册：`frontend/src/config/agents.ts`
- 劳权配置样例：`frontend/src/config/labor/`
