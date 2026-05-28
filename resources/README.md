# 劳权智助 · LaborAid 静态资源

本目录存放项目 **品牌与界面静态资源** 的源文件，与代码分离，便于统一维护。

## 目录结构

```
resources/
├── brand/                  # 品牌标识
│   ├── laboraid-logo.png   # 主 Logo / 应用头像
│   └── favicon.png         # 浏览器标签页图标（可与 logo 相同）
├── verification/           # 功能验证材料（Markdown，可转 PDF 提交）
│   ├── README.md           # 材料包索引与验证记录表
│   ├── 00-验证环境与账号.md
│   ├── 01-登录注册验证.md … 10-管理端验证.md
│   └── 附录-样例*.md       # 案情、合同样例正文
└── README.md
```

## 使用方式

1. **替换头像 / Logo**：直接覆盖 `brand/laboraid-logo.png`（建议正方形 PNG，≥512×512）
2. **开发 / 构建时**：Vite 会自动将 `resources/brand/` 同步到 `LaborAid/frontend/public/`
3. **代码引用**：通过 `frontend/src/config/assets.ts` 中的路径常量，勿硬编码 URL

## 功能验证材料

演示与验收用的 **Markdown 验证手册** 见 [`verification/`](./verification/README.md)，含：

- 各模块逐步验证清单（登录、维权前台、整理证据、生成文书、审查合同等）
- 可复制的样例案情与劳动合同正文
- 汇总验证记录表，便于转 PDF 提交

## 注意事项

- 请勿在 `frontend/public/` 手动改 logo，以本目录为准
- `public/` 中的副本由 Vite 自动生成，已加入 `.gitignore`
- 新增资源请在本 README 补充说明，并在 `assets.ts` 注册路径
