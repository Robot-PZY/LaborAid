# LaborAid 架构图源文件

比赛答辩用 **Diagram-as-Code** 源文件。修改后重新导出 PNG/SVG 贴 PPT。

## 文件一览

| 文件 | 用途 | PPT 建议页 |
|------|------|-----------|
| `six-layer-architecture.mmd` / `.d2` | 六层体系主图 | 架构总览 |
| `scenario-pipeline.mmd` | 场景五段式 | 场景设计 |
| `leap-algorithm-flow.mmd` | LEAP 算法 | 关键算法一 |
| `mice-evidence-flow.mmd` | MICE 算法 | 关键算法二 |
| `graph-rag.mmd` | 图谱增强检索 | 关键算法三 |
| `supervisor-agents.mmd` | 多 Agent | 关键算法四 |
| `smart-advocacy-end-to-end.mmd` | 端到端 demo | 演示流程 |

方案叙事见 [competition-scenario-design-proposal.md](../competition-scenario-design-proposal.md)。

**答辩组成元素图（35+ 张备用）**：[`docs/figures/`](../figures/README.md) — 架构/技术选型/用户端/管理端/部署/时序/实验/效果图，English-only PNG；预览 [`preview.html`](../figures/preview.html)。

Cursor Agent Skill：`.cursor/skills/laboraid-architecture-diagrams/SKILL.md`

## 导出 PNG / SVG

### 方式一：脚本（推荐）

```powershell
# 仓库根目录
.\scripts\export-diagrams.ps1
```

输出目录：`docs/diagrams/export/`

### 方式二：在线（零安装）

1. 打开 https://mermaid.live  
2. 粘贴任意 `.mmd` 内容  
3. Actions → PNG/SVG  

D2：https://play.d2lang.com — 粘贴 `.d2` 文件内容。

### 方式三：CLI 手动

```powershell
# Mermaid（需 Node.js）
npx -y @mermaid-js/mermaid-cli -i docs/diagrams/six-layer-architecture.mmd -o docs/diagrams/export/six-layer.png -b transparent

# D2（需安装 https://github.com/terrastruct/d2）
d2 docs/diagrams/six-layer-architecture.d2 docs/diagrams/export/six-layer.svg
```

## PPT 精修

逻辑以本目录源文件为准；**深蓝科技风**终稿可用：

- [Excalidraw](https://excalidraw.com) 导入结构后美化  
- [draw.io](https://app.diagrams.net/)  

可选 GitHub Skills：

```bash
gh skills install github/awesome-copilot excalidraw-diagram-generator
gh skills install github/awesome-copilot architecture-blueprint-generator
```

在 Cursor 中说：「按 laboraid-architecture-diagrams skill，把 six-layer 导出为 Excalidraw」。
