# SportFusion Formal Artifacts

## Artifact Status (2026-08-09)

| Artifact ID | Status | Description |
|-------------|--------|-------------|
| enterprise_dataset | ✅ available | 76,687 records, full enterprise data |
| sport_ratio_results | ✅ available | Formal batch recognition output |
| model_validation | ✅ available | Model validation metrics |
| enterprise_boundaries | ✅ available | Enterprise boundary analysis |
| preprocess_stats | ✅ available | Preprocessing statistics |
| audit_output | ✅ available | Data audit from paper_revision |
| reference_labels | ❌ missing | 300 reference labels (190 sport, 95 non-sport, 15 insufficient) |
| category_labels | ❌ missing | 184 clear category labels |
| official_prior | ❌ missing | 9-category official structural prior |
| benchmark_logs | ❌ missing | Formal benchmark runtime logs |

## Required for Golden Regression

- **reference_labels (300)**: Binary recognition validation (Accuracy/Precision/Recall/F1)
- **category_labels (184)**: Category classification validation (Macro-F1, confusion matrix)
- **official_prior**: Alpha > 0 scenario runs (12-scenario engine)
- **benchmark_logs**: Performance benchmark Golden comparison

## State

**READY_WITH_MISSING_ARTIFACTS** — 6 of 10 formal artifacts available.
Core pipeline is complete and testable with available artifacts.
Golden validation for recognition/category/scenario/benchmark is skipped until missing artifacts are provided.
