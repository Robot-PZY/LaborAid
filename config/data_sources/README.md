# 自定义数据源配置

本目录用于扩展劳权智助的外部法律数据源（法规、案例、法条详情等）。

## 使用方式

1. 在本目录创建 `.yaml` 或 `.json` 文件，文件名作为数据源标识。
2. 按统一字段描述连接信息、能力范围与字段映射。
3. 使用 `${...}` 语法引用环境变量。
4. 修改后重启后端服务使配置生效。

## 配置模板

```yaml
name: My Custom Law Database
type: api          # api | database | file
enabled: true

# Connection details (vary by type)
connection:
  base_url: https://api.example.com
  api_key: ${MY_API_KEY}        # resolved from environment variables
  timeout: 30

# Capabilities this source provides
capabilities:
  - legislation_search           # full-text law search
  - provision_lookup             # exact article retrieval
  - case_search                  # case law search
  - citation_validation          # citation verification

# Field mapping (how results from this source map to LaborAid models)
field_map:
  title: doc_title
  content: full_text
  article_number: art_no
  document_id: doc_id
  promulgation_date: pub_date
  effective_date: eff_date
  status: validity
```

## 支持的数据源类型

| 类型 | 说明 |
|------|------|
| `api` | REST API 接口（需 `base_url`） |
| `database` | 直连数据库（需 `dsn`） |
| `file` | 本地或挂载文件路径（CSV、JSONL、XML） |

## 参考实现（后端）

可参考 `backend/app/services/data_sources/` 下的内置适配器：

- `beida_fabao.py` — 北大法宝（chinese-law MCP）
- `custom_api.py` — 通用 REST API 适配器
- `base.py` — 抽象基类

---

Maintained by **Pulse Peng**
