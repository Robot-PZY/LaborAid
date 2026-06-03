# 劳权智助 · 文档总览

本目录用于统一管理产品说明、配置指南与开发规范。

## 🧭 新同学阅读顺序

1. [项目 README](../README.md)：项目定位、启动、常用入口
2. [API 配置位置一览](./api-config-locations.md)：环境变量与配置优先级
3. [国内模型配置指南](./model-config-guide.md)：文本模型与视觉 OCR 配置
4. [文件上传与多模态说明](./file-upload-guide.md)：文件类型、限制与注意点
5. [产品架构设计方案](./product-architecture.md)：业务结构与模块关系

## 📚 文档索引

| 文档 | 适用场景 |
|------|----------|
| [API 配置位置一览](./api-config-locations.md) | 不清楚 Key 填哪里、哪些是必填 |
| [国内模型配置指南](./model-config-guide.md) | 管理端配置模型、验证连通性 |
| [文件上传与多模态说明](./file-upload-guide.md) | 上传失败、OCR 识别效果排查 |
| [产品架构设计方案](./product-architecture.md) | 理解系统边界与模块职责 |
| [代码风格约定](./code-style.md) | 统一命名、格式和提交质量 |

## 🔗 相关入口

- 验证材料总览：[`../resources/verification/README.md`](../resources/verification/README.md)
- 环境变量模板：[`../.env.example`](../.env.example)

## ⚠️ 目录结构提示

当前仓库为 **git 根目录 + `LaborAid/` 子目录**（`LaborAid/LaborAid/backend`）。快速启动见根目录 [README](../README.md#-快速开始) 或运行 `scripts/dev.ps1`。

若需扁平化（`backend/`、`frontend/` 直接在根目录），在 git 根目录执行：

```powershell
.\scripts\normalize-project-layout.ps1
```

## 📌 文档时效说明

- [产品架构](./product-architecture.md) 为 **v1 设计稿**：其中「不做管理员后台」等表述已过时，实际已有完整管理端（见根 README）。
- 路由与功能以根目录 [README.md](../README.md) 及 `frontend/src/App.tsx` 为准。

---

Maintained by **Pulse Peng**
