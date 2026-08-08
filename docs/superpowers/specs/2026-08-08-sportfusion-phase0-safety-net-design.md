# SportFusion Phase 0 安全网设计规格

状态：已批准  
日期：2026-08-08  
适用仓库：`ChaoDaiShi/SportFusion`  
基线：`master@1d865fc4cd9dbb78cf355b19345fb44c16edd46e`

## 1. 目标

本阶段只建立后续口径迁移所需的测试、依赖、配置和数据库迁移基础，不修改识别、SportShare、规模估算、模型验证或前端业务语义。

完成后应同时保留两种能力：现有系统继续按原方式启动，新工程入口可以通过 uv、pytest 和 Alembic 独立运行。后续阶段修改算法或数据契约时，测试应能区分兼容性回归、报告口径违约和正式产物缺失。

## 2. 已确认的基线

仓库核查结果如下：

- 当前分支为 `master`，HEAD 与改造说明指定的 `1d865fc4cd9dbb78cf355b19345fb44c16edd46e` 一致。
- 前端现有 17 项 Node 契约测试通过。
- 后端现有 4 项 unittest 通过，服务、路由、API、模型和工具模块可以完成字节码编译。
- `data/processed_BATCH-20260803-R1` 含 76,687 条历史批次结果，但字段和计算链仍使用旧 `sport_ratio` 口径。
- `temp_experiments/phase2_annotation/annotation_complete_goldstandard.csv` 含 300 条历史标注样本，现有评估结果与正式报告锁定指标不一致。
- 仓库没有独立 SportShare RF 模型、冻结的 500 条训练样本、OOF q90 误差、证据校准配置、12 情景结果或 24 项审计产物。
- 根目录尚无 `pyproject.toml`、`uv.lock`、Alembic、顶层测试结构、正式配置目录和迁移基线说明。

以上历史批次和实验材料可以用于迁移核查，但本阶段不把它们认证为新的 formal artifact。

## 3. 范围

### 3.1 本阶段包含

- 建立根目录 Python 工程配置和 uv 锁文件。
- 保留 `backend/requirements.txt`，由新依赖配置导出，继续支持旧部署方式。
- 建立顶层 `tests/unit`、`tests/api`、`tests/integration`、`tests/golden`。
- 为当前 FastAPI 应用、路由注册和数据库初始化补充 smoke tests。
- 建立报告锁定指标 fixture，并验证指标之间的集合、求和和精度关系。
- 建立配置目录、配置清单、版本字段和 SHA256 校验器。
- 引入 Alembic，以当前 ORM metadata 生成数据库 baseline。
- 新增 `MIGRATION_BASELINE.md`，记录旧结构、已知语义问题和后续迁移边界。
- 新增基础 CI，执行静态检查、后端测试、前端测试和前端构建。

### 3.2 本阶段不包含

- 不修复 `/single`、`/batch` 丢失行业代码的问题。
- 不把 `sport_ratio` 重命名为 `sport_score`。
- 不训练或伪造 SportShare 模型。
- 不更改企业财务代理规模链。
- 不重写验证指标、图表数据源和监测数据源。
- 不修改现有 Vue 页面业务口径。
- 不把旧批次目录改名后当作正式产物。
- 不新增报告中未锁定的实验数值。

这些问题由 Phase 1 及后续阶段处理。Phase 0 只记录风险并建立检测入口。

## 4. 目标文件结构

本阶段新增或调整以下文件：

```text
SportFusion/
├─ pyproject.toml
├─ uv.lock
├─ alembic.ini
├─ MIGRATION_BASELINE.md
├─ .github/
│  └─ workflows/
│     └─ ci.yml
├─ alembic/
│  ├─ env.py
│  ├─ script.py.mako
│  └─ versions/
│     └─ 生成的当前结构 baseline revision
├─ config/
│  ├─ manifest.yaml
│  ├─ sportscore.yaml
│  ├─ sportshare.yaml
│  ├─ sports_business_dictionary.yaml
│  ├─ industry_code_map.yaml
│  ├─ evidence_calibration.yaml
│  ├─ official_structure_2022.yaml
│  └─ scale_scenarios.yaml
├─ backend/
│  └─ core/
│     ├─ __init__.py
│     ├─ configuration.py
│     └─ versions.py
└─ tests/
   ├─ conftest.py
   ├─ fixtures/
   │  └─ expected_formal_metrics.json
   ├─ unit/
   ├─ api/
   ├─ integration/
   └─ golden/
```

Alembic revision 文件名包含实际生成的 revision ID，不使用手写固定 ID。实现计划必须在创建后把准确文件名写入交付记录。

## 5. 依赖与运行方式

`pyproject.toml` 接管 Python 版本、运行依赖和开发依赖。运行依赖从当前 `backend/requirements.txt` 等价迁移；开发依赖加入 pytest、pytest-asyncio、httpx、ruff 和 Alembic。Phase 0 不强制引入 mypy，也不调整现有库的主版本。

推荐命令为：

```powershell
uv sync
uv run pytest tests/unit tests/api tests/integration tests/golden
uv run alembic upgrade head
uv run uvicorn backend.main:app --reload
```

旧入口继续可用：

```powershell
python -m uvicorn main:app --reload
```

`backend/requirements.txt` 通过 uv 导出后纳入版本控制。现有 `backend/.venv` 不删除，避免让依赖迁移和业务改造同时发生。

## 6. 测试设计

### 6.1 现状回归

现状回归测试回答“旧系统是否仍能运行”。范围包括：

- `backend.main` 可以导入，FastAPI 应用能够创建。
- 现有识别、比重、规模、验证、监测和助手路由仍被注册。
- 当前 ORM metadata 可以在空 SQLite 数据库中建表。
- 主要只读接口返回结构化响应，不能因基础设施调整出现新的 500 错误。
- 前端已有契约测试保持通过。

已知旧故障如果会阻止 smoke test，使用带问题编号和原因的 `xfail(strict=True)`。修复后意外通过会使测试失败，要求开发者删除对应 xfail，避免永久掩盖问题。

### 6.2 报告口径契约

`tests/fixtures/expected_formal_metrics.json` 保存报告锁定值。fixture 是测试期望，不是算法输入。测试至少覆盖：

- 传统集合、融合集合、交集、两侧独有和净增之间的算术关系。
- 951、934、977 使用不同键名，不能互换。
- 四类证据组之和为 8,950。
- SportShare 的 6,220 和 2,730 两类来源之和为 8,950。
- 九类规模合计为 2,170.80 亿元。
- 边界内外规模合计为 2,170.80 亿元。
- 市州规模合计为 2,170.80 亿元，映射 8,908 家并保留 42 家未识别。
- 12 个情景各自保持官方总量不变，边界外规模范围为 138.19 至 228.45 亿元。
- 验证指标使用文档规定的容差，不用字符串比较或不受控四舍五入。

这些测试验证报告契约是否自洽，不要求旧算法在 Phase 0 输出新结果。

### 6.3 正式批次 Golden 测试

完整批次测试使用 `formal_artifact` pytest marker。运行前检查所需产物清单和 SHA256：

- 产物齐全时，加载正式结果并与 fixture 比较。
- 产物缺失时，测试明确 skip，并在原因中列出缺失路径。
- 旧 `sport_ratio` CSV 不满足新产物 schema，不能被自动识别为正式结果。
- CI 常规任务不依赖受限正式数据；完整批次测试由本地或私有工作流显式启用。

skip 只允许用于缺失的正式产物。单元、API 和迁移测试不得因为环境配置不完整而静默跳过。

### 6.4 反作弊保护

Phase 0 建立策略测试，扫描新算法目录和后续新增的正式运行模块。Golden 数字只允许出现在 fixture、测试断言、报告来源配置和正式产物中。策略测试禁止出现按批次号直接返回固定结果、循环随机种子追指标或 formal 缺失时回退 demo 的实现。

现有 legacy 模块单独登记问题，不在 Phase 0 为了通过扫描而改写算法。

## 7. 配置与版本

### 7.1 配置状态

每个配置文件至少包含：

```yaml
schema_version: 1
config_id: SPORT-SCORE-CONFIG
version: NOT-IMPORTED
status: not_imported
source: report_alignment_migration
```

`NOT-IMPORTED` 是明确状态值，表示团队尚未补入正式配置，不代表可以使用默认值。配置加载器在 test 或 demo 模式可以读取测试 fixture；formal 模式遇到 `not_imported` 必须抛出 `FormalConfigurationUnavailable`。

正式配置导入后，manifest 保存相对路径、版本、SHA256 和生效批次。哈希按文件原始字节计算，不能先解析再重排内容。

### 7.2 加载接口

`backend/core/configuration.py` 提供三个边界清楚的接口：

```python
load_config(path: Path) -> dict
sha256_file(path: Path) -> str
require_formal_config(path: Path) -> dict
```

`load_config` 负责语法和基础 schema；`sha256_file` 只计算摘要；`require_formal_config` 检查状态、版本和 manifest 哈希。业务服务暂不接入这些接口，Phase 1 起逐项替换写死配置。

错误信息必须包含配置相对路径、当前状态和失败原因，不输出环境变量或敏感数据。

## 8. Alembic 基线

Alembic 使用现有 `backend.models.database.Base.metadata`。baseline 反映当前 ORM 结构，不借机加入未来字段。

迁移验证分为两条路径：

1. 对临时空 SQLite 数据库执行 `upgrade head`，检查生成表与 ORM metadata 一致。
2. 复制现有 `backend/sports_industry.db` 到临时目录，对副本执行 schema 检查和 `stamp head`，确认不修改业务行。

所有测试使用临时路径。不得对工作区中的真实数据库直接执行破坏性迁移。

`MIGRATION_BASELINE.md` 记录：

- Git 基线提交和生成日期。
- 当前数据库表、主键、外键和关键索引。
- `sport_ratio`、`sport_revenue_ratio`、`EnterpriseScale.sport_scale` 等歧义字段。
- 内存缓存、不可变批次和审计表的缺口。
- Phase 1 至 Phase 8 对应的迁移责任。
- 现有数据库备份与恢复命令。

## 9. CI

`.github/workflows/ci.yml` 在 Windows 或 Ubuntu 受支持的无状态环境中执行：

```text
uv sync
uv run ruff check backend/core tests alembic
uv run pytest tests/unit tests/api tests/integration tests/golden -m "not formal_artifact"
npm ci
npm test
npm run build
```

CI 不读取 `.env`，不调用 DeepSeek，不下载正式数据。需要密钥、正式数据或私有模型的测试不属于常规 workflow。

## 10. 错误处理

- 配置缺失、YAML 无法解析、版本为空或 SHA256 不一致时给出不同错误类型。
- `not_imported` 配置进入 formal 模式时直接失败，不使用 1.0、空字典或演示值替代。
- formal artifact 缺失时，测试报告列出缺失文件；运行时代码暂不接入该机制。
- Alembic 测试只操作临时数据库。目标路径指向工作区数据库时，测试辅助函数拒绝执行。
- 测试默认禁止外部网络和大模型调用。
- CI 或本地测试失败时保留完整命令、退出码和首个可操作错误，不以重跑掩盖不稳定测试。

## 11. 验收标准

Phase 0 只有在以下条件同时满足时完成：

- `uv sync` 成功并生成受版本控制的 `uv.lock`。
- 新增单元、API、集成和 Golden 契约测试通过。
- 缺失正式产物的测试只以 `formal_artifact` 原因跳过，并列出缺失项。
- 现有前端 17 项测试和后端 4 项测试保持通过。
- `npm run build` 通过。
- 空数据库可以执行 `alembic upgrade head`。
- 现有 SQLite 数据库副本可以安全 `stamp head`，业务行数不变。
- `backend/requirements.txt` 可由 uv 配置导出。
- `MIGRATION_BASELINE.md` 包含当前 schema、旧口径和后续迁移责任。
- Git diff 不包含识别、SportShare、规模、验证算法和 Vue 业务页面的修改。
- 没有新建虚假的模型、标签或正式批次产物。

## 12. 风险与控制

### 12.1 旧依赖与新锁文件不一致

先按当前 requirements 生成锁文件，再用现有测试验证。Phase 0 不升级主版本，减少环境变化。

### 12.2 FastAPI 导入触发真实数据库或环境变量

测试通过依赖注入和临时数据库隔离副作用。不能依赖开发机上的 `.env` 才通过。

### 12.3 Alembic baseline 与现有数据库漂移

分别比较 ORM metadata、空库升级结果和现有数据库副本。发现漂移时写入基线说明，不在本阶段自动修复业务表。

### 12.4 Golden 测试被误解为算法已达标

测试名称和文档明确区分 `contract` 与 `formal_artifact`。Phase 0 报告列出旧结果和报告口径之间的差异，不使用“正式批次复现完成”等表述。

### 12.5 受限数据无法进入 CI

常规 CI 只使用去标识化小 fixture。完整批次测试保留 marker 和导入约定，由本地或私有环境运行。

## 13. Phase 0 结束后的状态

Phase 0 完成后，系统业务表现与基线一致。仓库具备可复现依赖、迁移历史、分层测试和报告口径契约。随后是否进入 Phase 1 由单独评审决定；进入前需再次确认正式词典、行业代码映射和相关数据能否补入仓库。
