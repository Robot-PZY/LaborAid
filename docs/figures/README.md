# LaborAid 答辩组成元素图

本目录存放 **答辩 / 文档 / PPT 备用配图**（架构、技术选型、流程、实验、效果图等）。图源为 SVG，导出为透明底 PNG，配色对齐产品 UI（暖纸 `#FAF9F6`、墨蓝 `#1C2433`、琥珀 `#D97706`）。

> **图内文字为英文**：避免 PNG 导出时中文乱码；本 README 用中文说明用途与分类。

## 目录结构

```
docs/figures/
  svg/           图源（透明底，可编辑）
  png/           导出 PNG（宽度 1600px，贴 PPT 用）
  preview.html   按分类浏览全部配图
  scripts/       export-figures.ps1 + resvg 导出脚本
```

逻辑底稿（Mermaid）见 [`docs/diagrams/`](../diagrams/README.md)；方案叙事见 [`competition-scenario-design-proposal.md`](../competition-scenario-design-proposal.md)。

---

## 配图索引

### 架构总览

| 文件名 | 说明 |
|--------|------|
| `arch-six-layers` | 六层体系（精简竖条版） |
| `arch-six-layers-rich` | 六层体系（分层标签 + 模块卡片，对标参考架构图风格） |
| `arch-agent-topology` | Supervisor + 五 Specialist Agent 拓扑 |
| `arch-deployment` | 部署架构：浏览器 / FastAPI / 数据 / 外部服务 |
| `arch-api-overview` | REST API 分组总览 |

### 技术选型

| 文件名 | 说明 |
|--------|------|
| `arch-tech-stack` | 全栈技术栈一览（前端 / 后端 / AI / 数据 / 运维） |
| `arch-tech-selection` | **选型对照表**：已选技术 vs 备选方案 vs 选型理由 |
| `arch-ai-stack` | AI 层：DeepSeek、Qwen-VL、Chroma、LEAP/MICE 等 |
| `arch-frontend-stack` | 前端：React 19、Vite、Tailwind、核心模块 |
| `arch-backend-stack` | 后端：FastAPI、路由/服务、持久化、文档处理 |
| `arch-data-stack` | 数据层：SQLite/Postgres、Chroma、文件存储策略 |
| `arch-external-integrations` | 外部集成：DeepSeek、DashScope、得理、企查查等 |
| `arch-security` | 安全：JWT、RBAC、CORS、上传限制 |
| `arch-monorepo` | 仓库目录结构与端口说明 |

### 用户端

| 文件名 | 说明 |
|--------|------|
| `ui-user-portal` | 用户端页面地图（路由与核心模块） |
| `ui-user-intake` | Intake 分流：专项场景 vs 普通入口 |
| `sec-rbac` | 角色权限：普通用户 vs 管理员 |

### 管理端

| 文件名 | 说明 |
|--------|------|
| `ui-admin-portal` | 管理端页面地图（概览 / 用户 / 模型 / 知识库等） |

### 流程与时序

| 文件名 | 说明 |
|--------|------|
| `flow-sdad-pipeline` | SDAD 场景五段式闭环 |
| `flow-leap` | LEAP 路径规划算法流 |
| `flow-mice` | MICE 证据质证算法流 |
| `flow-graph-rag` | Graph-RAG 图谱增强检索 |
| `flow-end-to-end` | 智能维权端到端总流程 |
| `flow-demo-case002` | 演示链路：case-002 试用期辞退 |
| `seq-evidence-mice` | 时序图：证据上传 → MICE 报告 |
| `seq-auth-request` | 时序图：登录与 JWT 鉴权 |

### 实验与测试

| 文件名 | 说明 |
|--------|------|
| `exp-ablation-bars` | 消融实验柱状图 |
| `exp-metrics-bars` | 全栈 vs 基线指标对比 |
| `exp-test-matrix` | 五组测试案例矩阵（`resources/test/`） |
| `exp-test-strategy` | 测试策略（单元 / 集成 / E2E） |
| `matrix-algorithm-tools` | 算法与工具矩阵 |

### 效果图（UI 示意）

| 文件名 | 说明 |
|--------|------|
| `effect-mice-panel` | MICE 质证面板：使用前 vs 使用后 |
| `effect-case-workflow` | 案件工作流步骤条 + next-step |
| `effect-compensation-ui` | 赔偿计算器结构化结果 |
| `effect-research-citations` | 研究引擎：法条引用 + 证据清单 |

---

## 使用方式

### 1. 浏览器预览（推荐）

用浏览器打开同目录下的 [`preview.html`](preview.html)，按分类查看全部 PNG；加载失败时会自动回退到 SVG。

### 2. 导出 / 更新 PNG

修改 `svg/` 内图源后，在仓库根目录或本目录执行：

```powershell
cd docs/figures/scripts
npm install          # 首次需要
./export-figures.ps1
```

也可只导出指定文件：

```powershell
node export-png.js arch-tech-stack.svg flow-mice.svg
```

### 3. 贴进 PPT

直接使用 `png/` 下对应文件即可（透明底）。无需整页幻灯片模板，按答辩章节挑选组件图组合排版。

---

## 维护说明

- **改逻辑**：优先同步 [`docs/diagrams/*.mmd`](../diagrams/README.md)，再改 `svg/` 终稿。
- **改配色**：与 `LaborAid/frontend/src/index.css` 保持一致。
- **增新图**：在 `svg/` 新增文件 → 运行导出脚本 → 在 `preview.html` 的 `CATALOG` 中登记分类与标题。
