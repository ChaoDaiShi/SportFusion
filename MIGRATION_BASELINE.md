# SportFusion Migration Baseline

- Business baseline: `master@1d865fc4cd9dbb78cf355b19345fb44c16edd46e`
- Safety-net design: `6e13f2f`
- Alembic revision: `1d865fc0001`
- Database: SQLite, workspace runtime file `backend/sports_industry.db`

## Current tables

`enterprises`, `enterprise_businesses`, `measurements`, `data_sources`,
`model_metrics`, `batches`, `recognition_results_v2`, `sport_share_results`,
`enterprise_scales`, `regional_scale_results`, `review_tasks`, `review_records`,
`arbitration_records`, `operation_logs`.

## Known semantic debt

- `enterprise_businesses.sport_revenue_ratio` and `measurements.sport_ratio` use legacy ratio language.
- `recognition_results_v2.sport_score` exists, while API schemas still expose ambiguous `sport_ratio`.
- `sport_share_results.model_share` currently reuses the legacy recognition score.
- `enterprise_scales.sport_scale` stores the legacy enterprise financial-proxy result.
- Batch locking, review history, scale scenarios, evaluation runs and audit checks are incomplete.

## Migration ownership

- Phase 1 separates SportScore from legacy `sport_ratio`.
- Phase 2 versions the dictionary and industry-code map.
- Phase 3 adds immutable SportShare model outputs and fallback provenance.
- Phase 4 adds scale runs, scenarios and constrained aggregate results.
- Phase 5 adds evaluation and audit runs.
- Phase 6 persists batch locking and review workflow.
- Phase 7 changes monitoring, charts and exports to read locked artifacts.
- Phase 8 removes legacy columns after the compatibility window.

## Safe commands

`upgrade head` 会执行迁移脚本并创建或变更数据库结构，只能用于新建数据库或明确允许变更的临时数据库。例如：先指定一个临时或新数据库 URL，再运行 `uv run alembic upgrade head`。

`stamp head` 不执行结构迁移，只在数据库中登记当前 Alembic revision。它用于已经具备这 14 张基线表的既有数据库。登记前必须先复制数据库、核对副本的表和业务行数，再只对副本运行 `uv run alembic stamp head`。

工作区运行库 `backend/sports_industry.db` 只能作为复制来源读取。禁止对它直接执行 `upgrade`、`stamp`、降级、删除或任何迁移试验；所有试验都必须针对临时数据库或复制件。
