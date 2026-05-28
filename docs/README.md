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

如果你本地出现 `LaborAid/LaborAid` 双层结构，请在仓库根目录运行：

```powershell
.\scripts\normalize-project-layout.ps1
```

---

Maintained by **Pulse Peng**
