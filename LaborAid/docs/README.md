﻿# LaborAid 文档

本目录存放 LaborAid 的使用说明与配置指南，与代码分离，便于查阅和维护。

## 文档列表

| 文档 | 说明 |
|------|------|
| [**产品架构设计方案**](./product-architecture.md) | **服务平台 + 工具箱 + 四创新**（v1 设计稿） |
| [**专项维权通道 & 材料库**](./special-channels-and-material-vault.md) | **农民工/实习生/女职工专区**、一键举报、个人材料长期保存 |
| [API 配置位置一览](./api-config-locations.md) | **API Key 填哪里**（占位保留，自行配置） |
| [国内模型配置指南](./model-config-guide.md) | 推荐国内 LLM、按智能体分工、`.env` 与 Settings 配置 |
| [文件上传与多模态说明](./file-upload-guide.md) | 各页面支持的文件类型、OCR/音频能力与限制 |
| [代码风格约定](./code-style.md) | ESLint / Prettier / Ruff / Prompt 规范 |

## 目录整理（从 LaborAidAI 迁移）

若本地仍是 `LaborAid/LaborAid` 双层嵌套，请**关闭 Cursor 与 dev 服务**后，在 git 根目录执行：

```powershell
.\scripts\normalize-project-layout.ps1
```

将把 `backend`、`frontend` 提升到根目录，并将文件夹重命名为 **LaborAid**。

## 快速链接

- 项目 README：[../README.md](../README.md)（扁平化后在仓库根目录）
- 环境变量模板：[../.env.example](../.env.example)
- 智能体注册表：`frontend/src/config/agents.ts`
- 劳权配置样例：`frontend/src/config/labor/`（案由、证据清单、维权指引、专项通道）
- 专项通道配置：`frontend/src/config/labor/special-channels.json`
- 材料库配置：`frontend/src/config/labor/material-vault.json`
