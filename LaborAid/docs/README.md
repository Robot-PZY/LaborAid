# 劳权智助 · LaborAid 文档

本目录存放项目使用说明与配置指南，与代码分离，便于查阅和维护。

## 文档列表

| 文档 | 说明 |
|------|------|
| [产品架构设计方案](../../docs/product-architecture.md) | 服务平台 + 工具箱设计（v1 设计稿） |
| [维权专区通道 & 材料库](./special-channels-and-material-vault.md) | 特定群体专区、一键举报、个人材料库 |
| [API 配置位置一览](../../docs/api-config-locations.md) | API Key 填哪里 |
| [国内模型配置指南](../../docs/model-config-guide.md) | 推荐国内 LLM、管理端配置 |
| [文件上传与多模态说明](../../docs/file-upload-guide.md) | 各页面支持的文件类型与限制 |
| [代码风格约定](../../docs/code-style.md) | ESLint / Prettier / Ruff / Prompt 规范 |

## 目录整理

若本地仍为 `LaborAid/LaborAid` 嵌套结构，请关闭 IDE 与 dev 服务后，在 git 根目录执行：

```powershell
.\scripts\normalize-project-layout.ps1
```

## 快速链接

- 项目 README：[../../README.md](../../README.md)
- 环境变量模板：[../../.env.example](../../.env.example)
- 品牌配置：`frontend/src/config/brand.ts`
- 智能体注册表：`frontend/src/config/agents.ts`
- 劳权配置样例：`frontend/src/config/labor/`

---

Maintained by **Pulse Peng**
