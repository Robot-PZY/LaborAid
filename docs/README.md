# 劳权智助 · 文档总览

本目录统一管理产品说明、配置指南与开发规范。与代码同级的专题说明见 [`LaborAid/docs/`](../LaborAid/docs/README.md)。

---

## 新同学阅读顺序

| 顺序 | 文档 | 目的 |
|------|------|------|
| 1 | [项目 README](../README.md) | 定位、启动、路由、API 节选 |
| 2 | [API 配置位置一览](./api-config-locations.md) | 环境变量与优先级 |
| 3 | [国内模型配置指南](./model-config-guide.md) | 文本模型与视觉 OCR |
| 4 | [文件上传与多模态说明](./file-upload-guide.md) | 类型限制与 OCR 排查 |
| 5 | [产品架构设计方案](./product-architecture.md) | 业务边界与当前实现对照 |
| 6 | [专项 intake 与材料库](../LaborAid/docs/special-channels-and-material-vault.md) | 结构化维权与材料库 |

---

## 文档索引

| 文档 | 适用场景 |
|------|----------|
| [API 配置位置一览](./api-config-locations.md) | Key 填哪里、哪些是必填 |
| [国内模型配置指南](./model-config-guide.md) | 管理端配模型、测连通性 |
| [文件上传与多模态说明](./file-upload-guide.md) | 上传失败、OCR 效果 |
| [产品架构设计方案](./product-architecture.md) | 系统边界、IA 演进 |
| [代码风格约定](./code-style.md) | 命名、格式、提交质量 |
| [专项 intake 与材料库](../LaborAid/docs/special-channels-and-material-vault.md) | 农民工/实习生/女职工表单与 vault |

---

## 相关入口

| 资源 | 路径 |
|------|------|
| 功能验证材料包 | [`../resources/verification/README.md`](../resources/verification/README.md) |
| 环境变量模板 | [`../.env.example`](../.env.example) |
| 劳权静态配置 | `LaborAid/frontend/src/config/labor/` |
| 前端路由真源 | `LaborAid/frontend/src/App.tsx` |

---

## 目录结构提示

仓库为 **git 根 + `LaborAid/` 子目录**（`LaborAid/LaborAid/backend`）。快速启动：根目录 `.\scripts\dev.ps1`。

扁平化（可选）：

```powershell
.\scripts\normalize-project-layout.ps1
```

---

## 文档时效说明

| 文档 | 说明 |
|------|------|
| [product-architecture.md](./product-architecture.md) | v1 设计稿 + **§1.4 当前实现**；「不做管理端」等表述已过时 |
| [special-channels-and-material-vault.md](../LaborAid/docs/special-channels-and-material-vault.md) | 独立 `/channels` 页面已收敛至首页 intake；办事外链集中在 `/guidance` |
| 路由与功能 | 以 [README.md](../README.md) 与 `App.tsx` 为准 |

---

Maintained by **Pulse Peng**
