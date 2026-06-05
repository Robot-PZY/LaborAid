---
name: laboraid-architecture-diagrams
description: >-
  Generate and maintain LaborAid competition architecture diagrams (六层架构,
  LEAP/MICE/Graph-RAG/SAGD, Agent pipeline). Use when the user asks to draw
  architecture, flowchart, PPT diagram, 架构图, 流程图, or export diagrams for
  比赛答辩. Prefer docs/diagrams/*.mmd and *.d2 sources; Excalidraw/draw.io for
  final PPT polish.
---

# LaborAid 架构图与答辩可视化

## When to use

- 用户要画 **六层架构、LEAP/MICE 算法流程、Supervisor Agent、场景 Pipeline、Graph-RAG**
- 用户要 **更新方案稿配图** 或 **导出 PNG/SVG 贴 PPT**
- 用户提到 **盖诊通风格、比赛答辩图、技术架构图**

## Source of truth

| 文档 | 路径 |
|------|------|
| 方案稿 | `docs/competition-scenario-design-proposal.md` |
| 图源文件 | `docs/diagrams/*.mmd`（Mermaid）、`docs/diagrams/*.d2`（D2） |
| 导出说明 | `docs/diagrams/README.md` |

**修改架构叙事时**：先改方案稿对应章节，再同步改 `docs/diagrams/` 下图源，勿只改 PPT 截图。

## 命名规范（答辩统一口径）

| 缩写 | 全称 | 用途 |
|------|------|------|
| LEAP | Language-Enhanced Advocacy Planning | intake → 维权 Pipeline |
| MICE | Multimodal Integrity & Consistency Engine | OCR → 字段 → 质证 |
| Graph-RAG | 法理图谱增强检索 | 法条—情形—文书—证据 |
| SAGD | Structured Agentic Document Generation | 结构化文书生成 |
| SDAD | Scenario-Driven Advocacy Design | 场景设计总叙事 |

## 六层架构（固定层级，自上而下）

1. **用户层**：劳动者 · 基层援助人员 · 平台管理员  
2. **展现层**：服务首页 · Intake · 证据/文书/报告 · 办事资源  
3. **业务层**：场景 intake · 建案 · Pipeline · 材料库 · 记录  
4. **场景层**：农民工欠薪 · 试用期 · 女职工 · 通用劳动争议  
5. **技术层**：LEAP · MICE · Graph-RAG · SAGD · Supervisor Agent  
6. **数据层**：案件库 · 证据/OCR · Chroma · 文书模板 · 外链资源  

## Workflow

### A. 快速更新（推荐）

1. 编辑 `docs/diagrams/<name>.mmd` 或 `.d2`
2. 运行 `scripts/export-diagrams.ps1`（需 mmdc / d2 CLI）或打开 https://mermaid.live 粘贴导出
3. PNG 输出到 `docs/diagrams/export/`

### B. PPT 精修（盖诊通级视觉）

1. 以 Mermaid/D2 为逻辑底稿
2. 用 **Excalidraw**（https://excalidraw.com）或 **draw.io** 重绘深色科技风
3. 可选：安装 GitHub skill  
   `gh skills install github/awesome-copilot excalidraw-diagram-generator`  
   然后提示：「按 laboraid-architecture-diagrams skill 的六层架构，生成 Excalidraw 文件」

### C. 从代码自动补文档

```text
gh skills install github/awesome-copilot architecture-blueprint-generator
```

对仓库运行后生成 `Project_Architecture_Blueprint.md`，与 `docs/diagrams/` 人工图互补。

## 已有图清单

| 文件 | 内容 |
|------|------|
| `six-layer-architecture.mmd` / `.d2` | 六层体系主图 |
| `scenario-pipeline.mmd` | 场景五段式闭环 |
| `leap-algorithm-flow.mmd` | LEAP 关键算法一 |
| `mice-evidence-flow.mmd` | MICE 关键算法二 |
| `supervisor-agents.mmd` | 五 Agent + Supervisor |
| `graph-rag.mmd` | Graph-RAG 三元组 |
| `smart-advocacy-end-to-end.mmd` | 端到端总流程 |

## 输出要求

- Mermaid：兼容 GitHub 渲染；节点中文；避免过宽（>15 节点则拆图）
- D2：用于导出高清 SVG；`docs/diagrams/*.d2` 保持可编译
- 给用户的 PPT 建议：**深蓝底 +  cyan 强调色**（对标盖诊通），白底版另存 `-light` 后缀

## 禁止

- 不要声称自研 YOLO/CV 训练除非代码库真有
- 不要在未更新 `docs/diagrams/` 源文件的情况下只改口头描述

See `reference.md` for Mermaid/D2 snippets and Excalidraw prompt templates.
