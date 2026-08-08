# SportFusion Risk Dashboard and Assistant Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the approved light, competition-ready monitoring cockpit, risk center, grounded analysis assistant, and trustworthy data fallback on top of the existing Vue 3 and FastAPI application.

**Architecture:** Add a FastAPI aggregation layer that normalizes existing chart results into versioned monitoring snapshots and leaves unavailable validation fields explicit. Vue consumes the snapshot through a Pinia store that enforces real/cached/demo provenance, then renders the cockpit, risk center, and two assistant surfaces from the same analysis context. The existing NLP, validation, measurement, export, and chart services remain the calculation source.

**Tech Stack:** Vue 3.5, Vue Router 4.5, Pinia 2.3, Element Plus 2.9, ECharts 5.5, Vite 6, FastAPI 0.115, Pydantic 2.10, Python 3.11, Node built-in test runner, Python `unittest`.

## Global Constraints

- Preserve the current NLP recognition and output calculation algorithms.
- Use the approved palette: `#F4EFE4`, `#FFFDF8`, `#1E2B31`, `#3157D6`, `#E75B43`, `#EFB63A`, `#00A58C`, and `#7657D5`.
- Do not render emoji, a mascot, a robot avatar, or a purple-blue AI gradient.
- Keep source files UTF-8 and keep Chinese labels readable in both development and production builds.
- Never silently mix real values with demo values in one snapshot or export.
- Prefer the latest valid real snapshot over demo data when a request fails.
- Require a preview confirmation before recalculation, report generation, or file export.
- Add no new runtime or test dependency; use the existing `node_modules`, Node `--test`, and Python `unittest`.
- The current workspace is not a Git repository. Record the suggested commit message after each task; run the commit command only after the workspace is opened inside a Git repository.

---

## File structure

### Backend

- `backend/services/monitoring_service.py`: pure snapshot normalization, provenance, risk construction, and model metric defaults.
- `backend/services/decision_assistant.py`: grounded context, deterministic fallback answers, citations, and suggested actions.
- `backend/routers/monitoring.py`: overview and risk read APIs.
- `backend/routers/assistant.py`: structured SSE assistant API.
- `backend/tests/test_monitoring_service.py`: snapshot and risk contract tests.
- `backend/tests/test_decision_assistant.py`: grounding and fallback tests.
- `backend/main.py`: register new routers.
- `backend/services/chat_service.py`: replace mascot/customer-service prompt with the approved analysis-assistant role.

### Frontend

- `frontend/src/styles/tokens.css`: palette, type, spacing, radius, and shadow variables.
- `frontend/src/styles/base.css`: global reset, page background, focus states, and reduced-motion behavior.
- `frontend/src/config/navigation.js`: grouped product navigation.
- `frontend/src/api/monitoring.js`: overview and risk requests.
- `frontend/src/api/assistant.js`: structured SSE request.
- `frontend/src/features/monitoring/data-policy.js`: real/cached/demo resolution and local snapshot cache.
- `frontend/src/features/assistant/sse.js`: chunk-safe SSE parser.
- `frontend/src/store/analysis-context.js`: shared region/year/category/risk selection.
- `frontend/src/store/monitoring.js`: snapshot, loading, error, selection, and refresh behavior.
- `frontend/src/store/assistant.js`: assistant messages, stream progress, citations, and actions.
- `frontend/src/components/common/DataModeBadge.vue`: explicit provenance label.
- `frontend/src/components/monitoring/MetricCard.vue`: competition metric card.
- `frontend/src/components/monitoring/MethodComparison.vue`: traditional versus model comparison.
- `frontend/src/components/monitoring/RiskTable.vue`: shared risk list.
- `frontend/src/components/assistant/ContextAssistantPanel.vue`: page-level assistant.
- `frontend/src/views/MonitoringCockpit.vue`: approved light cockpit.
- `frontend/src/views/RiskCenter.vue`: risk list and evidence drawer.
- `frontend/src/views/AnalysisAssistant.vue`: full analysis workspace.
- `frontend/src/views/ModelEvaluation.vue`: accuracy, robustness, runtime, and memory summary.
- `frontend/src/App.vue`: grouped light application shell; remove rendered mascot assistant.
- `frontend/src/router/index.js`: monitoring-first routes.
- `frontend/src/main.js`: import design tokens and base styles.
- `frontend/package.json`: add Node test script.
- `frontend/tests/navigation.test.js`: navigation contract.
- `frontend/tests/data-policy.test.js`: provenance behavior.
- `frontend/tests/sse.test.js`: split SSE parsing.

---

### Task 1: Establish the product shell and visual tokens

**Files:**
- Create: `frontend/src/styles/tokens.css`
- Create: `frontend/src/styles/base.css`
- Create: `frontend/src/config/navigation.js`
- Create: `frontend/tests/navigation.test.js`
- Modify: `frontend/package.json`
- Modify: `frontend/src/main.js`
- Modify: `frontend/src/App.vue`
- Modify: `frontend/src/router/index.js`

**Interfaces:**
- Produces: `navigationGroups: Array<{ label: string, items: NavigationItem[] }>` where `NavigationItem` is `{ path, label, icon }`.
- Produces: global CSS variables consumed by every later component.
- Preserves: existing `/data`, `/recognition`, `/compare`, `/dashboard`, and `/export` routes during this task.

- [ ] **Step 1: Add a failing navigation contract test**

Create `frontend/tests/navigation.test.js`:

```js
import test from 'node:test'
import assert from 'node:assert/strict'
import { navigationGroups } from '../src/config/navigation.js'

test('navigation uses the approved four product groups', () => {
  assert.deepEqual(
    navigationGroups.map((group) => group.label),
    ['监测总览', '核心分析', '可信验证', '成果应用'],
  )
})

test('navigation contains no mascot or emoji copy', () => {
  const text = JSON.stringify(navigationGroups)
  assert.equal(text.includes('小融'), false)
  assert.equal(/[\u{1F300}-\u{1FAFF}]/u.test(text), false)
})
```

Add this script to `frontend/package.json`:

```json
"scripts": {
  "dev": "vite",
  "build": "vite build",
  "preview": "vite preview",
  "test": "node --test tests/*.test.js"
}
```

- [ ] **Step 2: Run the test and verify it fails**

Run: `npm test` from `frontend`  
Expected: FAIL with `ERR_MODULE_NOT_FOUND` for `src/config/navigation.js`.

- [ ] **Step 3: Implement the navigation contract**

Create `frontend/src/config/navigation.js`:

```js
export const navigationGroups = [
  {
    label: '监测总览',
    items: [
      { path: '/monitoring', label: '统计监测驾驶舱', icon: 'DataAnalysis' },
      { path: '/risks', label: '风险事件中心', icon: 'Warning' },
    ],
  },
  {
    label: '核心分析',
    items: [
      { path: '/data', label: '企业数据治理', icon: 'Files' },
      { path: '/recognition', label: '企业边界识别', icon: 'Search' },
      { path: '/compare', label: '经营比重测算', icon: 'ScaleToOriginal' },
      { path: '/industry-analysis', label: '产业规模分析', icon: 'TrendCharts' },
    ],
  },
  {
    label: '可信验证',
    items: [
      { path: '/model-evaluation', label: '模型性能评估', icon: 'Histogram' },
      { path: '/data', label: '数据过程追踪', icon: 'Connection' },
    ],
  },
  {
    label: '成果应用',
    items: [
      { path: '/assistant', label: '智能决策问答', icon: 'ChatLineSquare' },
      { path: '/export', label: '报告与成果中心', icon: 'Download' },
    ],
  },
]
```

- [ ] **Step 4: Add the exact visual tokens and base rules**

Create `frontend/src/styles/tokens.css`:

```css
:root {
  --sf-bg: #f4efe4;
  --sf-surface: #fffdf8;
  --sf-surface-muted: #eee6d7;
  --sf-ink: #1e2b31;
  --sf-text: #505957;
  --sf-muted: #727a78;
  --sf-line: #ddd6c9;
  --sf-blue: #3157d6;
  --sf-red: #e75b43;
  --sf-yellow: #efb63a;
  --sf-teal: #00a58c;
  --sf-violet: #7657d5;
  --sf-radius-sm: 6px;
  --sf-radius-md: 10px;
  --sf-radius-lg: 16px;
  --sf-shadow: 0 14px 32px rgba(58, 46, 30, 0.10);
  --sf-font: "PingFang SC", "Microsoft YaHei", system-ui, sans-serif;
}
```

Create `frontend/src/styles/base.css`:

```css
* { box-sizing: border-box; }
html, body, #app { min-height: 100%; margin: 0; }
body { background: var(--sf-bg); color: var(--sf-ink); font-family: var(--sf-font); }
button, input, textarea { font: inherit; }
:focus-visible { outline: 3px solid color-mix(in srgb, var(--sf-blue) 35%, transparent); outline-offset: 2px; }
.page-shell { min-width: 0; }
.page-heading { display: flex; align-items: end; justify-content: space-between; gap: 16px; margin-bottom: 16px; }
.page-heading h1 { margin: 0; font-size: 24px; letter-spacing: -0.02em; }
.page-heading p { margin: 6px 0 0; color: var(--sf-muted); font-size: 13px; }
@media (prefers-reduced-motion: reduce) { *, *::before, *::after { scroll-behavior: auto !important; transition-duration: 0.01ms !important; animation-duration: 0.01ms !important; } }
```

Import both files after Element Plus in `frontend/src/main.js`:

```js
import './styles/tokens.css'
import './styles/base.css'
```

- [ ] **Step 5: Replace the dark shell and remove the rendered mascot assistant**

Rewrite `frontend/src/App.vue` around `navigationGroups`. The implementation must:

```vue
<template>
  <div class="app-shell">
    <aside class="app-sidebar">
      <div class="brand"><span class="brand-mark" aria-hidden="true"></span><span>体融识界</span></div>
      <nav aria-label="主导航">
        <section v-for="group in navigationGroups" :key="group.label" class="nav-group">
          <h2>{{ group.label }}</h2>
          <RouterLink v-for="item in group.items" :key="`${group.label}-${item.path}-${item.label}`" :to="item.path" class="nav-item">
            <el-icon><component :is="item.icon" /></el-icon><span>{{ item.label }}</span>
          </RouterLink>
        </section>
      </nav>
      <div class="system-note"><span></span>真实接口优先<br>演示保障可用</div>
    </aside>
    <main class="app-main"><RouterView /></main>
  </div>
</template>

<script setup>
import { RouterLink, RouterView } from 'vue-router'
import { navigationGroups } from './config/navigation'
</script>
```

Do not import or render `ChatAssistant.vue`. Add this scoped shell CSS:

```css
.app-shell { min-height: 100vh; display: grid; grid-template-columns: 176px minmax(0, 1fr); background: var(--sf-bg); }
.app-sidebar { position: sticky; top: 0; height: 100vh; overflow-y: auto; padding: 18px 12px; border-right: 1px solid var(--sf-line); background: var(--sf-surface-muted); }
.brand { display: flex; align-items: center; gap: 9px; padding: 0 8px 18px; font-size: 16px; font-weight: 900; }
.brand-mark { width: 26px; height: 26px; border-radius: 7px; background: var(--sf-blue); box-shadow: 8px 8px 0 -4px var(--sf-red); }
.nav-group { margin-top: 15px; }.nav-group h2 { margin: 0 8px 6px; color: #8a887f; font-size: 10px; letter-spacing: .12em; font-weight: 600; }
.nav-item { display: flex; align-items: center; gap: 8px; margin: 2px 0; padding: 9px 10px; border-radius: 7px; color: var(--sf-text); font-size: 13px; text-decoration: none; }
.nav-item.router-link-active { background: var(--sf-ink); color: white; font-weight: 800; }.nav-item.router-link-active .el-icon { color: var(--sf-yellow); }
.system-note { margin-top: 20px; padding: 12px 8px; border-top: 1px solid #d7cebd; color: var(--sf-muted); font-size: 11px; line-height: 1.7; }.system-note > span { display: inline-block; width: 7px; height: 7px; margin-right: 6px; border-radius: 50%; background: var(--sf-teal); }
.app-main { min-width: 0; padding: 18px; }
@media (max-width: 1024px) { .app-shell { grid-template-columns: 132px minmax(0, 1fr); }.brand { font-size: 14px; }.nav-item { font-size: 12px; padding-inline: 8px; }.app-main { padding: 12px; } }
```

- [ ] **Step 6: Register temporary route redirects without broken imports**

Update `frontend/src/router/index.js` so the root redirects to `/monitoring`, and temporarily map unimplemented approved routes to existing working pages:

```js
{ path: '/', redirect: '/monitoring' },
{ path: '/monitoring', redirect: '/dashboard' },
{ path: '/risks', redirect: '/dashboard' },
{ path: '/industry-analysis', name: 'IndustryAnalysis', component: () => import('../views/IndustryDashboard.vue'), meta: { title: '产业规模分析' } },
{ path: '/assistant', redirect: '/dashboard' },
{ path: '/model-evaluation', redirect: '/compare' },
```

Keep the legacy route names unique. Set the document title suffix to `体融识界`.

- [ ] **Step 7: Run tests and build**

Run: `npm test`  
Expected: PASS, 2 tests.

Run: `npm run build`  
Expected: Vite exits 0 and writes `frontend/dist` without unresolved route or Vue template errors.

- [ ] **Step 8: Record checkpoint**

Suggested commit: `feat: establish SportFusion product shell`  
If Git is available: `git add frontend && git commit -m "feat: establish SportFusion product shell"`

---

### Task 2: Add the monitoring snapshot and trustworthy data policy

**Files:**
- Create: `backend/services/monitoring_service.py`
- Create: `backend/routers/monitoring.py`
- Create: `backend/tests/test_monitoring_service.py`
- Modify: `backend/main.py`
- Create: `frontend/src/api/monitoring.js`
- Create: `frontend/src/features/monitoring/data-policy.js`
- Create: `frontend/tests/data-policy.test.js`
- Create: `frontend/src/store/analysis-context.js`
- Create: `frontend/src/store/monitoring.js`

**Interfaces:**
- Produces backend `GET /api/monitoring/overview?file_id=` and `GET /api/monitoring/risks?file_id=`.
- Produces `build_monitoring_snapshot(dashboard, mode, updated_at) -> dict`; a real snapshot may be partial, but it never borrows demo-only fields.
- Produces `resolveSnapshot({ remote, cached, demo }) -> MonitoringSnapshot`.
- Produces Pinia `useMonitoringStore()` and `useAnalysisContextStore()`.

- [ ] **Step 1: Write failing backend contract tests**

Create `backend/tests/test_monitoring_service.py`:

```py
import unittest
from services.monitoring_service import build_monitoring_snapshot


class MonitoringServiceTest(unittest.TestCase):
    def test_demo_snapshot_is_explicit_and_complete(self):
        snapshot = build_monitoring_snapshot({}, mode="demo", updated_at="2026-08-01T18:20:00+08:00")
        self.assertEqual(snapshot["provenance"]["mode"], "demo")
        self.assertTrue(snapshot["provenance"]["is_complete"])
        self.assertEqual(len(snapshot["metrics"]), 4)
        self.assertGreaterEqual(len(snapshot["risks"]), 4)
        self.assertIn("runtime_seconds_per_10k", snapshot["model_metrics"])

    def test_real_snapshot_preserves_values_without_demo_mixing(self):
        dashboard = {
            "overview": {"sport_enterprises": 12, "total_output_index": 345.6, "crossover_count": 4},
            "map": {"data": [{"name": "成都市", "value": 210.0}]},
            "line": {"labels": ["2025"], "series": [{"name": "体育用品", "data": [210.0]}]},
            "concentration": {"cr3_pct": 64.0},
            "structure": {"diversity_index": 0.75},
        }
        snapshot = build_monitoring_snapshot(dashboard, mode="real", updated_at="2026-08-01T18:20:00+08:00")
        self.assertEqual(snapshot["metrics"][0]["value"], 12)
        self.assertEqual(snapshot["metrics"][1]["value"], 345.6)
        self.assertEqual(snapshot["regions"][0]["name"], "成都市")
        self.assertEqual(snapshot["provenance"]["mode"], "real")
        self.assertFalse(snapshot["provenance"]["is_complete"])
        self.assertIn("model_metrics", snapshot["provenance"]["missing_fields"])
        self.assertEqual(snapshot["model_metrics"], {})
        self.assertEqual(snapshot["risks"][0]["type"], "industry_structure")
        self.assertNotEqual(snapshot["risks"][0]["id"], "R-2025-071")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Verify the backend test fails**

Run from `backend`: `.\.venv\Scripts\python.exe -m unittest discover -s tests -v`  
Expected: ERROR because `services.monitoring_service` does not exist.

- [ ] **Step 3: Implement the pure monitoring service**

Create `backend/services/monitoring_service.py` with these public constants and functions:

```py
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

PIPELINE = [
    {"id": "data", "label": "企业数据治理", "description": "清洗、分词、标签"},
    {"id": "recognition", "label": "业务边界识别", "description": "类型与置信度"},
    {"id": "ratio", "label": "经营比重测算", "description": "多维加权模型"},
    {"id": "scale", "label": "产业规模估算", "description": "区域与分业态产出"},
    {"id": "decision", "label": "验证与决策", "description": "性能、风险、建议"},
]

DEMO_DASHBOARD = {
    "overview": {"sport_enterprises": 8950, "total_output_index": 579124.95, "crossover_count": 977},
    "map": {"data": [
        {"name": "成都市", "value": 237694.59}, {"name": "绵阳市", "value": 13636.0},
        {"name": "宜宾市", "value": 11993.47}, {"name": "泸州市", "value": 11251.82},
        {"name": "乐山市", "value": 10318.35},
    ]},
    "line": {"labels": ["2019", "2020", "2021", "2022", "2023", "2024", "2025"], "series": []},
    "concentration": {"cr3_pct": 77.3},
    "structure": {"diversity_index": 0.7638, "crossover_rate_pct": 10.92},
}

MODEL_METRICS = {
    "accuracy": 0.916, "precision": 0.928, "recall": 0.904, "mae": 0.083,
    "normal_input_pass_rate": 0.916, "missing_text_pass_rate": 0.962,
    "noise_input_pass_rate": 0.947, "runtime_seconds_per_10k": 8.7, "peak_memory_mb": 486,
}

DEMO_RISKS = [
    {"id": "R-2025-071", "title": "成都健身服务市场集中度异常", "type": "industry_structure", "level": "high", "status": "analyzing", "score": 89, "confidence": 0.93, "region": "成都市", "category": "健身休闲", "deviation_score": 91, "impact_score": 84, "evidence_score": 93, "enterprise_ids": [], "evidence": ["CR3 升至 77.3%，超过 60% 预警阈值", "头部区域产出占比继续上升", "新增样本区域分布不均衡"]},
    {"id": "R-2025-062", "title": "企业业务边界识别置信度偏低", "type": "enterprise_boundary", "level": "medium", "status": "pending_verification", "score": 76, "confidence": 0.81, "region": "绵阳市", "category": "健身休闲", "deviation_score": 74, "impact_score": 69, "evidence_score": 81, "enterprise_ids": ["DEMO-001", "DEMO-002"], "evidence": ["18 家企业置信度低于 0.60", "主营业务文本存在跨业态描述"]},
    {"id": "R-2025-055", "title": "区域样本缺失率连续升高", "type": "data_quality", "level": "medium", "status": "pending_action", "score": 69, "confidence": 0.88, "region": "宜宾市", "category": None, "deviation_score": 70, "impact_score": 58, "evidence_score": 88, "enterprise_ids": [], "evidence": ["主要业务活动缺失率连续两期升高"]},
    {"id": "R-2025-043", "title": "模型结果较基线发生轻微漂移", "type": "model_performance", "level": "watch", "status": "monitoring", "score": 54, "confidence": 0.90, "region": "德阳市", "category": None, "deviation_score": 48, "impact_score": 42, "evidence_score": 90, "enterprise_ids": [], "evidence": ["低置信度样本占比上升 2.1 个百分点"]},
]

def _provenance(mode: str, updated_at: str | None, missing_fields: list[str]) -> dict[str, Any]:
    timestamp = updated_at or datetime.now(timezone.utc).isoformat()
    return {"mode": mode, "dataset_id": "sichuan-enterprises-2025", "data_version": "2025.07", "model_version": "V3.2", "updated_at": timestamp, "is_complete": not missing_fields, "missing_fields": missing_fields}

def _real_structure_risks(source: dict[str, Any]) -> list[dict[str, Any]]:
    cr3 = float(source.get("concentration", {}).get("cr3_pct", 0) or 0)
    if cr3 <= 60:
        return []
    return [{"id": "REAL-STRUCTURE-CR3", "title": "头部区域产业集中度超过预警阈值", "type": "industry_structure", "level": "high" if cr3 >= 75 else "medium", "status": "pending_verification", "score": min(99, round(cr3 + 12)), "confidence": 0.90, "region": "全省", "category": None, "deviation_score": round(cr3), "impact_score": 80, "evidence_score": 90, "enterprise_ids": [], "evidence": [f"当前批次 CR3 为 {cr3:.1f}%，超过 60% 预警阈值"]}]

def build_monitoring_snapshot(dashboard: dict[str, Any], mode: str, updated_at: str | None = None) -> dict[str, Any]:
    is_demo = mode == "demo"
    source = deepcopy(DEMO_DASHBOARD if is_demo else dashboard)
    if not source or not source.get("overview"):
        raise ValueError("真实快照缺少 overview，不能用演示数据补齐")
    overview = source.get("overview", {})
    output_index = round(float(overview.get("total_output_index", 0)), 2)
    sport_enterprises = int(overview.get("sport_enterprises", 0))
    crossover_count = int(overview.get("crossover_count", 0))
    metrics = [
        {"id": "sport_enterprises", "label": "识别体育企业", "value": sport_enterprises, "unit": "家", "tone": "teal", "note": f"其中跨界经营 {crossover_count} 家"},
        {"id": "output_index", "label": "体育产业总产出指数", "value": output_index, "unit": "", "tone": "red", "note": "按企业体育业务比重加权"},
    ]
    if is_demo:
        metrics += [
            {"id": "method_gap", "label": "传统方法低估差异", "value": 18.7, "unit": "%", "tone": "yellow", "note": "演示对比口径"},
            {"id": "model_accuracy", "label": "模型综合一致率", "value": 91.6, "unit": "%", "tone": "blue", "note": "异常输入通过率 96.2%"},
        ]
    missing_fields = [] if is_demo else ["method_comparison", "model_metrics", "robustness_metrics"]
    return {
        "pipeline": deepcopy(PIPELINE),
        "metrics": metrics,
        "method_comparison": {"traditional": 486900.0, "model": output_index, "gap_percent": 18.7} if is_demo else None,
        "regions": source.get("map", {}).get("data", []),
        "trend": source.get("line", {"labels": [], "series": []}),
        "risks": deepcopy(DEMO_RISKS) if is_demo else _real_structure_risks(source),
        "model_metrics": deepcopy(MODEL_METRICS) if is_demo else {},
        "provenance": _provenance(mode, updated_at, missing_fields),
    }
```

This separation is mandatory: `DEMO_RISKS`, `MODEL_METRICS`, and the 18.7% comparison are used only when `mode == "demo"`. A real dashboard with unavailable evaluation fields returns those fields empty and lists them in `missing_fields`; the frontend renders an explicit unavailable state instead of filling them with demo numbers.

- [ ] **Step 4: Add monitoring routes without duplicating chart calculations**

Create `backend/routers/monitoring.py`:

```py
from typing import Optional
from fastapi import APIRouter, Query
from routers.chart_data import get_dashboard_data
from services.monitoring_service import build_monitoring_snapshot

router = APIRouter()

async def get_monitoring_snapshot(file_id: Optional[int]):
    response = await get_dashboard_data(file_id)
    mode = "demo" if response.get("note") else "real"
    return build_monitoring_snapshot(response.get("data") or {}, mode=mode)

@router.get("/overview", summary="获取统计监测驾驶舱快照")
async def overview(file_id: Optional[int] = Query(None)):
    return {"code": 200, "message": "获取监测快照成功", "data": await get_monitoring_snapshot(file_id)}

@router.get("/risks", summary="获取风险事件")
async def risks(file_id: Optional[int] = Query(None), level: Optional[str] = Query(None), risk_type: Optional[str] = Query(None)):
    items = (await get_monitoring_snapshot(file_id))["risks"]
    if level:
        items = [item for item in items if item["level"] == level]
    if risk_type:
        items = [item for item in items if item["type"] == risk_type]
    return {"code": 200, "message": "获取风险事件成功", "data": {"items": items, "total": len(items)}}

@router.get("/risks/{risk_id}", summary="获取风险证据")
async def risk_detail(risk_id: str, file_id: Optional[int] = Query(None)):
    item = next((risk for risk in (await get_monitoring_snapshot(file_id))["risks"] if risk["id"] == risk_id), None)
    if not item:
        return {"code": 404, "message": "风险事件不存在", "data": None}
    return {"code": 200, "message": "获取风险详情成功", "data": item}
```

Register it in `backend/main.py`:

```py
from routers import data_preprocess, enterprise_recognition, output_calc, chart_data, model_validate, chat, monitoring
app.include_router(monitoring.router, prefix="/api/monitoring", tags=["统计监测"])
```

- [ ] **Step 5: Run backend tests**

Run: `.\.venv\Scripts\python.exe -m unittest discover -s tests -v`  
Expected: PASS, 2 tests.

Run: `.\.venv\Scripts\python.exe -m compileall routers services`  
Expected: exits 0.

- [ ] **Step 6: Write failing frontend provenance tests**

Create `frontend/tests/data-policy.test.js`:

```js
import test from 'node:test'
import assert from 'node:assert/strict'
import { resolveSnapshot } from '../src/features/monitoring/data-policy.js'

const snapshot = (mode, value, isComplete = true) => ({ metrics: [{ value }], provenance: { mode, is_complete: isComplete, missing_fields: isComplete ? [] : ['model_metrics'] } })

test('a complete remote snapshot wins and remains real', () => {
  assert.equal(resolveSnapshot({ remote: snapshot('real', 1), cached: snapshot('cached', 2), demo: snapshot('demo', 3) }).provenance.mode, 'real')
})

test('a partial real snapshot wins without demo fields being inserted', () => {
  const result = resolveSnapshot({ remote: snapshot('real', 1, false), cached: snapshot('real', 2), demo: snapshot('demo', 3) })
  assert.equal(result.provenance.mode, 'real')
  assert.deepEqual(result.provenance.missing_fields, ['model_metrics'])
  assert.equal(result.metrics[0].value, 1)
})

test('a cached real snapshot wins over demo when remote is absent', () => {
  const result = resolveSnapshot({ remote: null, cached: snapshot('real', 2), demo: snapshot('demo', 3) })
  assert.equal(result.provenance.mode, 'cached')
  assert.equal(result.metrics[0].value, 2)
})

test('demo is used only when remote and cache are invalid', () => {
  assert.equal(resolveSnapshot({ remote: null, cached: null, demo: snapshot('demo', 3) }).provenance.mode, 'demo')
})
```

- [ ] **Step 7: Implement the frontend data policy, API, and stores**

Create `frontend/src/features/monitoring/data-policy.js`:

```js
const CACHE_KEY = 'sportfusion.monitoring.snapshot.v1'
export const isUsableSnapshot = (value) => Boolean(value?.metrics?.length && ['real', 'cached', 'demo'].includes(value?.provenance?.mode))

export function resolveSnapshot({ remote, cached, demo }) {
  if (isUsableSnapshot(remote)) return remote
  if (isUsableSnapshot(cached)) return { ...cached, provenance: { ...cached.provenance, mode: 'cached' } }
  return demo
}

export function readCachedSnapshot(storage = localStorage) {
  try { return JSON.parse(storage.getItem(CACHE_KEY) || 'null') } catch { return null }
}

export function writeCachedSnapshot(snapshot, storage = localStorage) {
  if (snapshot?.provenance?.mode === 'real' && isUsableSnapshot(snapshot)) storage.setItem(CACHE_KEY, JSON.stringify(snapshot))
}
```

The policy prefers any usable real response, including an honestly partial one. It never merges individual fields across modes. Cached mode is only a relabelled copy of a prior real response; demo mode is a complete standalone snapshot.

Create `frontend/src/api/monitoring.js`:

```js
import request from './index'
export const getMonitoringOverview = (fileId) => request.get('/monitoring/overview', { params: fileId ? { file_id: fileId } : {} })
export const getRisks = (params = {}) => request.get('/monitoring/risks', { params })
export const getRiskDetail = (riskId, fileId) => request.get(`/monitoring/risks/${riskId}`, { params: fileId ? { file_id: fileId } : {} })
```

Create `frontend/src/store/analysis-context.js`:

```js
import { defineStore } from 'pinia'
import { reactive } from 'vue'
export const useAnalysisContextStore = defineStore('analysis-context', () => {
  const context = reactive({ fileId: null, region: '四川省', year: '2025', category: '', riskType: '', riskLevel: '', selectedEnterpriseIds: [], selectedRiskId: '', dataVersion: '', modelVersion: '' })
  const patch = (value) => Object.assign(context, value)
  const clearSelection = () => Object.assign(context, { category: '', riskType: '', riskLevel: '', selectedEnterpriseIds: [], selectedRiskId: '' })
  return { context, patch, clearSelection }
})
```

Create `frontend/src/store/monitoring.js`:

```js
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getMonitoringOverview } from '../api/monitoring'
import { readCachedSnapshot, resolveSnapshot, writeCachedSnapshot } from '../features/monitoring/data-policy'
import { useAnalysisContextStore } from './analysis-context'

const demoSnapshot = {
  pipeline: [
    { id: 'data', label: '企业数据治理', description: '清洗、分词、标签' },
    { id: 'recognition', label: '业务边界识别', description: '类型与置信度' },
    { id: 'ratio', label: '经营比重测算', description: '多维加权模型' },
    { id: 'scale', label: '产业规模估算', description: '区域与分业态产出' },
    { id: 'decision', label: '验证与决策', description: '性能、风险、建议' },
  ],
  metrics: [
    { id: 'sport_enterprises', label: '识别体育企业', value: 8950, unit: '家', tone: 'teal', note: '其中跨界经营 977 家' },
    { id: 'output_index', label: '体育产业总产出指数', value: 579124.95, unit: '', tone: 'red', note: '按企业体育业务比重加权' },
    { id: 'method_gap', label: '传统方法低估差异', value: 18.7, unit: '%', tone: 'yellow', note: '演示对比口径' },
    { id: 'model_accuracy', label: '模型综合一致率', value: 91.6, unit: '%', tone: 'blue', note: '异常输入通过率 96.2%' },
  ],
  method_comparison: { traditional: 486900, model: 579124.95, gap_percent: 18.7 },
  regions: [{ name: '成都市', value: 237694.59 }, { name: '绵阳市', value: 13636 }, { name: '宜宾市', value: 11993.47 }, { name: '泸州市', value: 11251.82 }],
  trend: { labels: [], series: [] },
  risks: [
    { id: 'R-2025-071', title: '成都健身服务市场集中度异常', type: 'industry_structure', level: 'high', status: 'analyzing', score: 89, confidence: 0.93, region: '成都市', category: '健身休闲', deviation_score: 91, impact_score: 84, evidence_score: 93, evidence: ['CR3 升至 77.3%，超过 60% 预警阈值', '头部区域产出占比继续上升'] },
    { id: 'R-2025-062', title: '企业业务边界识别置信度偏低', type: 'enterprise_boundary', level: 'medium', status: 'pending_verification', score: 76, confidence: 0.81, region: '绵阳市', category: '健身休闲', deviation_score: 74, impact_score: 69, evidence_score: 81, evidence: ['18 家企业置信度低于 0.60'] },
    { id: 'R-2025-055', title: '区域样本缺失率连续升高', type: 'data_quality', level: 'medium', status: 'pending_action', score: 69, confidence: 0.88, region: '宜宾市', category: '', deviation_score: 70, impact_score: 58, evidence_score: 88, evidence: ['主要业务活动缺失率连续两期升高'] },
    { id: 'R-2025-043', title: '模型结果较基线发生轻微漂移', type: 'model_performance', level: 'watch', status: 'monitoring', score: 54, confidence: 0.90, region: '德阳市', category: '', deviation_score: 48, impact_score: 42, evidence_score: 90, evidence: ['低置信度样本占比上升 2.1 个百分点'] },
  ],
  model_metrics: { accuracy: 0.916, precision: 0.928, recall: 0.904, mae: 0.083, normal_input_pass_rate: 0.916, missing_text_pass_rate: 0.962, noise_input_pass_rate: 0.947, runtime_seconds_per_10k: 8.7, peak_memory_mb: 486 },
  provenance: { mode: 'demo', dataset_id: 'sichuan-enterprises-2025', data_version: '2025.07', model_version: 'V3.2', updated_at: '2026-08-01T18:20:00+08:00', is_complete: true, missing_fields: [] },
}

export const useMonitoringStore = defineStore('monitoring', () => {
  const snapshot = ref(demoSnapshot)
  const loading = ref(false)
  const error = ref('')
  const selectedRisk = ref(null)

  async function refresh(fileId) {
    loading.value = true
    error.value = ''
    let remote = null
    try {
      const response = await getMonitoringOverview(fileId)
      remote = response.code === 200 ? response.data : null
      writeCachedSnapshot(remote)
    } catch (requestError) {
      error.value = requestError.message || '监测接口暂不可用，已切换到可用快照'
    } finally {
      snapshot.value = resolveSnapshot({ remote, cached: readCachedSnapshot(), demo: demoSnapshot })
      const contextStore = useAnalysisContextStore()
      contextStore.patch({ fileId: fileId || null, dataVersion: snapshot.value.provenance.data_version, modelVersion: snapshot.value.provenance.model_version })
      loading.value = false
    }
  }

  const selectRisk = (risk) => { selectedRisk.value = risk }
  const clearRisk = () => { selectedRisk.value = null }
  return { snapshot, loading, error, selectedRisk, refresh, selectRisk, clearRisk }
})
```

- [ ] **Step 8: Run all contract tests**

Run from `frontend`: `npm test`  
Expected: PASS, 6 tests.

Run from `backend`: `.\.venv\Scripts\python.exe -m unittest discover -s tests -v`  
Expected: PASS, 2 tests.

- [ ] **Step 9: Record checkpoint**

Suggested commit: `feat: add versioned monitoring snapshot`  
If Git is available: `git add backend frontend && git commit -m "feat: add versioned monitoring snapshot"`

---

### Task 3: Build the monitoring cockpit

**Files:**
- Create: `frontend/src/components/common/DataModeBadge.vue`
- Create: `frontend/src/components/monitoring/MetricCard.vue`
- Create: `frontend/src/components/monitoring/MethodComparison.vue`
- Create: `frontend/src/components/monitoring/RiskTable.vue`
- Create: `frontend/src/views/MonitoringCockpit.vue`
- Modify: `frontend/src/router/index.js`
- Modify: `frontend/src/config/navigation.js` only if a route label changed during implementation.

**Interfaces:**
- Consumes: `useMonitoringStore().snapshot` and `useAnalysisContextStore().context`.
- Produces: `RiskTable` event `select(risk)`.
- Produces: route `/monitoring` named `MonitoringCockpit`.

- [ ] **Step 1: Create the provenance and metric components**

Create `frontend/src/components/common/DataModeBadge.vue`:

```vue
<template><el-tooltip :content="tooltip"><span class="mode-badge" :data-mode="provenance.mode">{{ labels[provenance.mode] || '数据状态未知' }}</span></el-tooltip></template>
<script setup>
import { computed } from 'vue'
const props = defineProps({ provenance: { type: Object, default: () => ({ mode: 'demo' }) } })
const labels = { real: '真实数据', cached: '历史快照', demo: '演示数据保障' }
const tooltip = computed(() => `${labels[props.provenance.mode] || '数据状态未知'} · ${props.provenance.updated_at || '无更新时间'}`)
</script>
<style scoped>
.mode-badge { display: inline-flex; padding: 6px 9px; border-radius: 6px; font-size: 12px; font-weight: 700; }
.mode-badge[data-mode="real"] { background: #dcf1eb; color: #087665; }
.mode-badge[data-mode="cached"] { background: #fff0ca; color: #875a00; }
.mode-badge[data-mode="demo"] { background: #e4e8f7; color: #3046a5; }
</style>
```

Create `frontend/src/components/monitoring/MetricCard.vue`:

```vue
<template><article class="metric-card" :style="{ '--tone': toneColor }"><span class="metric-dot"></span><small>{{ label }}</small><strong>{{ formatted }}<em>{{ unit }}</em></strong><p>{{ note }}</p></article></template>
<script setup>
import { computed } from 'vue'
const props = defineProps({ label: String, value: [Number, String], unit: String, note: String, tone: { type: String, default: 'blue' } })
const colors = { teal: 'var(--sf-teal)', red: 'var(--sf-red)', yellow: 'var(--sf-yellow)', blue: 'var(--sf-blue)' }
const toneColor = computed(() => colors[props.tone] || colors.blue)
const formatted = computed(() => typeof props.value === 'number' ? props.value.toLocaleString('zh-CN', { maximumFractionDigits: 2 }) : props.value)
</script>
<style scoped>
.metric-card { position: relative; padding: 16px; border: 1px solid var(--sf-line); border-radius: var(--sf-radius-md); background: var(--sf-surface); }
.metric-dot { position: absolute; right: 14px; top: 14px; width: 9px; height: 9px; border-radius: 50%; background: var(--tone); }
small, p { color: var(--sf-muted); } strong { display: block; margin-top: 8px; font-size: 28px; letter-spacing: -0.04em; } em { margin-left: 5px; font-size: 12px; font-style: normal; font-weight: 500; } p { margin: 7px 0 0; font-size: 12px; }
</style>
```

- [ ] **Step 2: Create the method comparison and risk table**

Create `frontend/src/components/monitoring/MethodComparison.vue`:

```vue
<template><div class="comparison"><div v-for="row in rows" :key="row.label" class="comparison-row"><div><span>{{ row.label }}</span><strong>{{ format(row.value) }}</strong></div><div class="track"><i :style="{ width: `${row.width}%`, background: row.color }"></i></div></div><p>模型测算较传统方法高 <strong>{{ comparison.gap_percent }}%</strong></p></div></template>
<script setup>
import { computed } from 'vue'
const props = defineProps({ comparison: { type: Object, required: true } })
const max = computed(() => Math.max(props.comparison.traditional || 0, props.comparison.model || 0, 1))
const rows = computed(() => [{ label: '传统行业代码法', value: props.comparison.traditional, width: props.comparison.traditional / max.value * 100, color: 'var(--sf-yellow)' }, { label: 'NLP 融合模型', value: props.comparison.model, width: props.comparison.model / max.value * 100, color: 'var(--sf-teal)' }])
const format = (value) => Number(value || 0).toLocaleString('zh-CN', { maximumFractionDigits: 1 })
</script>
<style scoped>
.comparison-row { margin-bottom: 12px; }.comparison-row > div:first-child { display: flex; justify-content: space-between; font-size: 12px; }.track { height: 8px; margin-top: 6px; overflow: hidden; border-radius: 8px; background: #ebe5da; }.track i { display: block; height: 100%; border-radius: inherit; }.comparison p { color: var(--sf-muted); font-size: 12px; }
</style>
```

Create `RiskTable.vue`:

```vue
<template>
  <div class="risk-table" role="table" aria-label="风险事件">
    <button v-for="risk in risks" :key="risk.id" class="risk-row" type="button" @click="$emit('select', risk)">
      <span class="risk-level" :data-level="risk.level">{{ levelLabel[risk.level] }}</span>
      <span class="risk-copy"><strong>{{ risk.title }}</strong><small>{{ typeLabel[risk.type] }} · {{ risk.region }}</small></span>
      <span class="risk-score">{{ risk.score }}</span>
    </button>
  </div>
</template>
<script setup>
defineProps({ risks: { type: Array, default: () => [] } })
defineEmits(['select'])
const levelLabel = { high: '高风险', medium: '中风险', watch: '关注' }
const typeLabel = { enterprise_boundary: '企业识别', industry_structure: '产业结构', data_quality: '数据质量', model_performance: '模型性能', measurement_gap: '测算偏差' }
</script>
```

Style the row as a full-width light button, not a chat chip. Level labels must include text and color.

- [ ] **Step 3: Implement the cockpit composition**

Create `MonitoringCockpit.vue` with this hierarchy:

```vue
<template>
  <section v-loading="loading" class="page-shell cockpit-page">
    <header class="page-heading">
      <div><h1>体育产业统计监测驾驶舱</h1><p>企业级识别、经营比重测算与区域风险研判</p></div>
      <div class="heading-actions"><DataModeBadge :provenance="snapshot.provenance"/><el-button type="primary" @click="router.push('/export')">生成成果报告</el-button></div>
    </header>
    <el-alert v-if="error" :title="error" type="warning" show-icon :closable="false"><el-button link @click="refresh(fileId)">重新加载</el-button></el-alert>
    <div class="pipeline"><article v-for="(step, index) in snapshot.pipeline" :key="step.id"><span>{{ index + 1 }}</span><strong>{{ step.label }}</strong><small>{{ step.description }}</small></article></div>
    <div class="metric-grid"><MetricCard v-for="metric in snapshot.metrics" :key="metric.id" v-bind="metric"/></div>
    <div class="cockpit-grid">
      <article class="panel"><header><strong>测算差异与重点风险</strong></header><MethodComparison v-if="snapshot.method_comparison" :comparison="snapshot.method_comparison"/><el-empty v-else description="当前真实批次尚未生成方法对比结果" :image-size="54"/><RiskTable :risks="snapshot.risks.slice(0, 3)" @select="openRisk"/></article>
      <article class="panel map-panel"><header><strong>区域产业规模与结构风险</strong></header><MapHeatmap :data="snapshot.regions" :height="270"/></article>
      <article class="panel insight-panel"><span>智能研判</span><h2>传统方法为何低估体育产业规模？</h2><p>差异主要来自多元经营企业的漏识别修正。点击进入完整分析，查看数据批次与企业证据。</p><el-button @click="router.push('/assistant')">进入智能研判</el-button></article>
    </div>
    <article class="panel result-panel"><header><strong>风险事件明细</strong><el-button link @click="router.push('/risks')">查看全部</el-button></header><RiskTable :risks="snapshot.risks" @select="openRisk"/></article>
  </section>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { storeToRefs } from 'pinia'
import { useRouter } from 'vue-router'
import DataModeBadge from '../components/common/DataModeBadge.vue'
import MapHeatmap from '../components/MapHeatmap.vue'
import MetricCard from '../components/monitoring/MetricCard.vue'
import MethodComparison from '../components/monitoring/MethodComparison.vue'
import RiskTable from '../components/monitoring/RiskTable.vue'
import { useAnalysisContextStore } from '../store/analysis-context'
import { useDataStore } from '../store/data'
import { useMonitoringStore } from '../store/monitoring'

const router = useRouter()
const dataStore = useDataStore()
const monitoringStore = useMonitoringStore()
const analysisContext = useAnalysisContextStore()
const { snapshot, loading, error } = storeToRefs(monitoringStore)
const fileId = computed(() => dataStore.queryParams.fileId)

function openRisk(risk) {
  monitoringStore.selectRisk(risk)
  analysisContext.patch({ selectedRiskId: risk.id, region: risk.region || '四川省', category: risk.category || '' })
  router.push({ path: '/risks', query: { risk_id: risk.id } })
}

onMounted(() => monitoringStore.refresh(fileId.value))
</script>

<style scoped>
.cockpit-page { min-width: 0; }
.heading-actions, .panel > header { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
.pipeline { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 8px; margin-bottom: 12px; }
.pipeline article { position: relative; display: grid; grid-template-columns: 30px 1fr; gap: 2px 8px; align-items: center; padding: 10px; border: 1px solid var(--sf-line); border-radius: var(--sf-radius-sm); background: var(--sf-surface); }
.pipeline article:not(:last-child)::after { position: absolute; right: -8px; width: 8px; height: 1px; background: var(--sf-yellow); content: ''; }
.pipeline span { grid-row: 1 / 3; display: grid; width: 28px; height: 28px; place-items: center; border-radius: 50%; background: #e5eafa; color: var(--sf-blue); font-weight: 800; }
.pipeline small { color: var(--sf-muted); }
.metric-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; margin-bottom: 12px; }
.cockpit-grid { display: grid; grid-template-columns: minmax(260px, .84fr) minmax(420px, 1.45fr) minmax(280px, .92fr); gap: 10px; }
.panel { min-width: 0; padding: 14px; border: 1px solid var(--sf-line); border-radius: var(--sf-radius-md); background: var(--sf-surface); }
.panel > header { margin-bottom: 12px; }
.insight-panel { display: flex; flex-direction: column; background: var(--sf-ink); color: white; }
.insight-panel > span { color: var(--sf-yellow); font-size: 12px; font-weight: 800; }
.insight-panel h2 { margin: 18px 0 10px; font-size: 20px; line-height: 1.45; }
.insight-panel p { color: #d2d8d6; line-height: 1.7; }
.insight-panel .el-button { align-self: flex-start; margin-top: auto; }
.result-panel { margin-top: 10px; }
@media (max-width: 1100px) { .cockpit-grid { grid-template-columns: 1fr; }.metric-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }.pipeline { grid-template-columns: 1fr; }.pipeline article::after { display: none; } }
@media (max-width: 650px) { .metric-grid { grid-template-columns: 1fr; }.heading-actions { align-items: flex-start; flex-direction: column; } }
</style>
```

The `v-if` around `MethodComparison` is part of the provenance policy: incomplete real snapshots show an unavailable state and never reuse the demo 18.7% value.

- [ ] **Step 4: Replace the monitoring redirect with the real route**

In `frontend/src/router/index.js`:

```js
{ path: '/monitoring', name: 'MonitoringCockpit', component: () => import('../views/MonitoringCockpit.vue'), meta: { title: '统计监测驾驶舱' } },
```

Keep legacy `/dashboard` as a redirect to `/monitoring`; keep `/industry-analysis` mapped to the old detailed dashboard.

- [ ] **Step 5: Verify cockpit behavior**

Run: `npm test`  
Expected: all Node tests pass.

Run: `npm run build`  
Expected: build exits 0.

Manual check at `/monitoring`:
- four metrics are visible at 1920×1080 without a page-level horizontal scrollbar;
- `DataModeBadge` says `演示数据保障` when no processed file is selected;
- clicking a risk navigates to `/risks?risk_id=...`;
- no mascot or floating chat button is present.

- [ ] **Step 6: Record checkpoint**

Suggested commit: `feat: build monitoring cockpit`  
If Git is available: `git add frontend && git commit -m "feat: build monitoring cockpit"`

---

### Task 4: Build the risk event center and evidence drawer

**Files:**
- Create: `frontend/src/views/RiskCenter.vue`
- Modify: `frontend/src/router/index.js`

**Interfaces:**
- Consumes: `snapshot.risks` from Task 2.
- Produces: query-driven selected risk, level/type filters, evidence drawer, and local status transitions for prototype review.
- Produces: route `/risks` named `RiskCenter`.

- [ ] **Step 1: Verify the selected-risk interface from Task 2**

Run this contract check from `frontend`:

```powershell
Select-String -Path '.\src\store\monitoring.js' -Pattern 'selectedRisk|selectRisk|clearRisk'
```

Expected: all three names are present. Task 2 already defines `selectedRisk`, `selectRisk(risk)`, and `clearRisk()`; this task consumes that interface and does not duplicate it.

- [ ] **Step 2: Implement the risk center**

Create `frontend/src/views/RiskCenter.vue`:

```vue
<template>
  <section class="page-shell risk-page">
    <header class="page-heading"><div><h1>风险事件中心</h1><p>按事件核验触发依据、影响范围与处置状态</p></div><DataModeBadge :provenance="snapshot.provenance" /></header>
    <div class="filters"><el-input v-model="query" clearable placeholder="搜索风险、区域或业态"/><el-select v-model="level" clearable placeholder="风险等级"><el-option label="高风险" value="high"/><el-option label="中风险" value="medium"/><el-option label="关注" value="watch"/></el-select><el-select v-model="riskType" clearable placeholder="风险类型"><el-option v-for="(label, value) in typeLabels" :key="value" :label="label" :value="value"/></el-select></div>
    <div class="risk-list"><button v-for="risk in filteredRisks" :key="risk.id" type="button" class="risk-item" @click="openRisk(risk)"><span class="level" :data-level="risk.level">{{ levelLabels[risk.level] }}</span><span class="copy"><strong>{{ risk.title }}</strong><small>{{ typeLabels[risk.type] }} · {{ risk.region }} · {{ statusLabels[risk.status] }}</small></span><span><small>可信度</small><strong>{{ Math.round(risk.confidence * 100) }}%</strong></span><b>{{ risk.score }}</b></button></div>

    <el-drawer v-model="drawerOpen" size="420px" title="风险证据与处置">
      <template v-if="selectedRisk"><span class="level" :data-level="selectedRisk.level">{{ levelLabels[selectedRisk.level] }}</span><h2>{{ selectedRisk.title }}</h2><p class="meta">{{ selectedRisk.id }} · {{ selectedRisk.region }} · 可信度 {{ Math.round(selectedRisk.confidence * 100) }}%</p>
        <div class="score-grid"><div v-for="item in scoreItems" :key="item.label"><span>{{ item.label }}</span><el-progress :percentage="item.value" :show-text="false"/><b>{{ item.value }}</b></div></div>
        <el-tabs v-model="activeTab"><el-tab-pane label="触发证据" name="evidence"><ul><li v-for="evidence in selectedRisk.evidence" :key="evidence">{{ evidence }}</li></ul></el-tab-pane><el-tab-pane label="变化轨迹" name="timeline"><ol class="lifecycle"><li class="done">已发现</li><li class="done">待核验</li><li class="current">分析中</li><li>待处置</li><li>已解决/持续观察</li></ol></el-tab-pane><el-tab-pane label="处置记录" name="actions"><el-empty description="当前事件尚无已完成处置记录" :image-size="64"/></el-tab-pane></el-tabs>
        <div class="drawer-actions"><el-button @click="markVerified">标记核验结果</el-button><el-button type="primary" @click="goAssistant">进入智能研判</el-button><el-button class="wide" type="warning" @click="previewOpen = true">运行校正测算</el-button></div>
      </template>
    </el-drawer>

    <el-dialog v-model="previewOpen" title="校正测算预览" width="480px"><el-descriptions v-if="selectedRisk" :column="1" border><el-descriptions-item label="风险事件">{{ selectedRisk.id }}</el-descriptions-item><el-descriptions-item label="影响区域">{{ selectedRisk.region }}</el-descriptions-item><el-descriptions-item label="数据版本">{{ snapshot.provenance.data_version }}</el-descriptions-item><el-descriptions-item label="模型版本">{{ snapshot.provenance.model_version }}</el-descriptions-item></el-descriptions><template #footer><el-button @click="previewOpen = false">取消</el-button><el-button type="warning" @click="confirmPreview">确认运行</el-button></template></el-dialog>
  </section>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import DataModeBadge from '../components/common/DataModeBadge.vue'
import { useMonitoringStore } from '../store/monitoring'
import { useDataStore } from '../store/data'

const route = useRoute(); const router = useRouter(); const monitoring = useMonitoringStore(); const dataStore = useDataStore()
const { snapshot, selectedRisk } = storeToRefs(monitoring)
const query = ref(''); const level = ref(''); const riskType = ref(''); const drawerOpen = ref(false); const previewOpen = ref(false); const activeTab = ref('evidence')
const levelLabels = { high: '高风险', medium: '中风险', watch: '关注' }
const typeLabels = { enterprise_boundary: '企业识别', industry_structure: '产业结构', data_quality: '数据质量', model_performance: '模型性能', measurement_gap: '测算偏差' }
const statusLabels = { new: '新发现', pending_verification: '待核验', analyzing: '分析中', pending_action: '待处置', resolved: '已解决', monitoring: '持续观察' }
const filteredRisks = computed(() => snapshot.value.risks.filter((risk) => (!query.value || `${risk.title}${risk.region}${risk.category || ''}`.includes(query.value)) && (!level.value || risk.level === level.value) && (!riskType.value || risk.type === riskType.value)))
const scoreItems = computed(() => selectedRisk.value ? [{ label: '偏离程度', value: selectedRisk.value.deviation_score }, { label: '影响范围', value: selectedRisk.value.impact_score }, { label: '证据可信度', value: selectedRisk.value.evidence_score }] : [])
function openRisk(risk) { monitoring.selectRisk(risk); drawerOpen.value = true; router.replace({ query: { ...route.query, risk_id: risk.id } }) }
function openFromQuery() { const risk = snapshot.value.risks.find((item) => item.id === route.query.risk_id); if (risk) openRisk(risk) }
function markVerified() { ElMessage.success('核验结果已记录在当前演示会话'); activeTab.value = 'timeline' }
function goAssistant() { router.push(`/assistant?risk_id=${selectedRisk.value.id}`) }
function confirmPreview() { previewOpen.value = false; ElMessage.success('校正测算已完成预览，原始结果未被覆盖') }
onMounted(async () => { await monitoring.refresh(dataStore.queryParams.fileId); openFromQuery() })
watch(() => route.query.risk_id, openFromQuery)
</script>

<style scoped>
.filters { display: grid; grid-template-columns: 1fr 180px 180px; gap: 10px; margin-bottom: 14px; }.risk-list { overflow: hidden; border: 1px solid var(--sf-line); border-radius: var(--sf-radius-md); background: var(--sf-surface); }.risk-item { width: 100%; display: grid; grid-template-columns: 72px 1fr 86px 48px; gap: 14px; align-items: center; padding: 15px; border: 0; border-bottom: 1px solid var(--sf-line); background: transparent; color: var(--sf-ink); text-align: left; cursor: pointer; }.risk-item:hover { background: #f8f3e9; }.copy { display: grid; gap: 5px; }.copy small, .meta { color: var(--sf-muted); }.level { width: max-content; padding: 4px 7px; border-radius: 5px; font-size: 12px; font-weight: 800; }.level[data-level="high"] { background: #fbe0da; color: #c34732; }.level[data-level="medium"] { background: #fff0ca; color: #976200; }.level[data-level="watch"] { background: #dff3ed; color: #127867; }.score-grid > div { display: grid; grid-template-columns: 80px 1fr 30px; gap: 8px; align-items: center; margin: 12px 0; }.drawer-actions { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-top: 18px; }.drawer-actions .wide { grid-column: 1 / -1; }.lifecycle { display: grid; gap: 8px; padding-left: 20px; }.lifecycle .done { color: var(--sf-teal); }.lifecycle .current { color: #9a6500; font-weight: 800; } @media (max-width: 900px) { .filters { grid-template-columns: 1fr; }.risk-item { grid-template-columns: 70px 1fr 42px; }.risk-item > span:nth-child(3) { display: none; } }
</style>
```

`进入智能研判` routes to `/assistant?risk_id=<id>`. `运行校正测算` is a non-destructive preview in this phase; it never overwrites source data.

- [ ] **Step 3: Register the route**

Replace the risk redirect with:

```js
{ path: '/risks', name: 'RiskCenter', component: () => import('../views/RiskCenter.vue'), meta: { title: '风险事件中心' } },
```

- [ ] **Step 4: Verify the risk workflow**

Run: `npm run build`  
Expected: exits 0.

Manual check:
- opening `/risks?risk_id=R-2025-071` opens the matching drawer;
- selecting `高风险` leaves only high-risk events;
- evidence bars have text values and are not color-only;
- recalculation requires confirmation;
- closing the drawer preserves filters.

- [ ] **Step 5: Record checkpoint**

Suggested commit: `feat: add traceable risk center`  
If Git is available: `git add frontend && git commit -m "feat: add traceable risk center"`

---

### Task 5: Replace the mascot chat with grounded, structured analysis

**Files:**
- Create: `backend/services/decision_assistant.py`
- Create: `backend/routers/assistant.py`
- Create: `backend/tests/test_decision_assistant.py`
- Modify: `backend/services/chat_service.py`
- Modify: `backend/main.py`
- Create: `frontend/src/features/assistant/sse.js`
- Create: `frontend/tests/sse.test.js`
- Create: `frontend/src/api/assistant.js`
- Create: `frontend/src/store/assistant.js`
- Create: `frontend/src/components/assistant/ContextAssistantPanel.vue`
- Create: `frontend/src/views/AnalysisAssistant.vue`
- Modify: `frontend/src/views/MonitoringCockpit.vue`
- Modify: `frontend/src/router/index.js`

**Interfaces:**
- Produces: `build_grounding(message, snapshot) -> { context_text, citations, actions, fallback_answer }`.
- Produces: `POST /api/assistant/stream` with structured SSE events.
- Produces: `consumeSseChunk(buffer, chunk) -> { events, remainder }`.
- Produces: shared assistant store used by the cockpit panel and full workspace.

- [ ] **Step 1: Write failing grounding tests**

Create `backend/tests/test_decision_assistant.py`:

```py
import unittest
from services.decision_assistant import build_grounding
from services.monitoring_service import build_monitoring_snapshot


class DecisionAssistantTest(unittest.TestCase):
    def setUp(self):
        self.snapshot = build_monitoring_snapshot({}, mode="demo", updated_at="2026-08-01T18:20:00+08:00")

    def test_method_gap_answer_uses_snapshot_values(self):
        result = build_grounding("为什么模型比传统方法高？", self.snapshot)
        self.assertIn("18.7%", result["fallback_answer"])
        self.assertGreaterEqual(len(result["citations"]), 2)
        self.assertEqual(result["citations"][0]["data_version"], "2025.07")

    def test_risk_answer_contains_traceable_action(self):
        result = build_grounding("成都集中度风险是什么原因？", self.snapshot)
        self.assertTrue(any(action["type"] == "open_risk" for action in result["actions"]))
        self.assertNotIn("小融", result["fallback_answer"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run backend tests and verify failure**

Run: `.\.venv\Scripts\python.exe -m unittest discover -s tests -v`  
Expected: ERROR because `services.decision_assistant` does not exist.

- [ ] **Step 3: Implement deterministic grounding**

Create `backend/services/decision_assistant.py`:

```py
from typing import Any

def _citation(cid: str, label: str, value: str, snapshot: dict[str, Any]) -> dict[str, str]:
    provenance = snapshot["provenance"]
    return {"id": cid, "label": label, "value": value, "data_version": provenance["data_version"], "model_version": provenance["model_version"]}

def build_grounding(message: str, snapshot: dict[str, Any]) -> dict[str, Any]:
    metrics = {item["id"]: item for item in snapshot["metrics"]}
    citations = [
        _citation("metric-enterprises", "识别体育企业", f"{metrics['sport_enterprises']['value']} 家", snapshot),
        _citation("metric-output", "总产出指数", str(metrics['output_index']['value']), snapshot),
    ]
    comparison = snapshot.get("method_comparison")
    if comparison:
        citations.insert(0, _citation("metric-gap", "传统方法低估差异", f"{comparison['gap_percent']}%", snapshot))
    if ("集中度" in message or "风险" in message or "成都" in message) and snapshot.get("risks"):
        risk = snapshot["risks"][0]
        answer = f"{risk['title']}的综合风险值为 {risk['score']}。主要依据包括：" + "；".join(risk["evidence"][:2]) + "。建议先核验关联样本，再运行校正测算。"
        actions = [{"id": "open-risk", "type": "open_risk", "label": "查看风险证据", "payload": {"risk_id": risk["id"]}}, {"id": "recalculate", "type": "preview_recalculation", "label": "预览校正测算", "payload": {"risk_id": risk["id"]}}]
    elif comparison:
        gap = comparison["gap_percent"]
        answer = f"当前模型测算结果较传统行业代码法高 {gap}%。差异主要来自多元经营企业的漏识别修正；本批次识别体育企业 {metrics['sport_enterprises']['value']} 家。"
        actions = [{"id": "compare", "type": "navigate", "label": "联动测算对比", "payload": {"path": "/compare"}}, {"id": "report", "type": "preview_report", "label": "生成政策摘要", "payload": {"report_type": "policy"}}]
    else:
        answer = f"当前真实批次识别体育企业 {metrics['sport_enterprises']['value']} 家，总产出指数为 {metrics['output_index']['value']}。该批次尚未生成方法对比和模型评测结果，因此不能判断低估幅度。"
        actions = [{"id": "compare", "type": "navigate", "label": "运行测算对比", "payload": {"path": "/compare"}}, {"id": "evaluation", "type": "navigate", "label": "查看模型评估", "payload": {"path": "/model-evaluation"}}]
    context_text = "\n".join(f"{item['label']}: {item['value']}" for item in citations)
    return {"context_text": context_text, "citations": citations, "actions": actions, "fallback_answer": answer}
```

- [ ] **Step 4: Replace the old system prompt and implement structured SSE**

In `backend/services/chat_service.py`, replace `SYSTEM_PROMPT` with a concise role that says:

```py
SYSTEM_PROMPT = """你是体融识界的统计分析助手。只依据请求中提供的数据上下文回答体育产业边界识别、经营比重、规模测算、模型评估和风险研判问题。先给结论，再解释依据。没有数据时明确说明缺口，不得编造数值、企业或来源。不要自称小融，不使用表情符号。"""
```

Create `backend/routers/assistant.py`:

```py
import json
import logging
from typing import Any, Literal, Optional

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from routers.monitoring import get_monitoring_snapshot
from services.chat_service import stream_chat
from services.decision_assistant import build_grounding

router = APIRouter()
logger = logging.getLogger(__name__)


class AssistantMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class AssistantRequest(BaseModel):
    message: str
    history: list[AssistantMessage] = Field(default_factory=list)
    context: dict[str, Any] = Field(default_factory=dict)
    file_id: Optional[int] = None


def sse(event_type: str, data: dict[str, Any]) -> str:
    return f"data: {json.dumps({'type': event_type, **data}, ensure_ascii=False)}\n\n"


@router.post("/stream", summary="基于监测上下文的流式研判")
async def assistant_stream(payload: AssistantRequest):
    async def event_stream():
        try:
            snapshot = await get_monitoring_snapshot(payload.file_id)
            grounding = build_grounding(payload.message, snapshot)
            provenance = snapshot["provenance"]
            yield sse("context_ready", {
                "data_version": provenance["data_version"],
                "model_version": provenance["model_version"],
                "fallback_mode": provenance["mode"],
                "missing_fields": provenance["missing_fields"],
            })
            yield sse("tool_started", {"label": "读取监测快照"})
            yield sse("tool_finished", {"label": "读取监测快照"})

            prompt = (
                f"用户问题：{payload.message}\n"
                f"页面筛选上下文：{json.dumps(payload.context, ensure_ascii=False)}\n"
                f"可引用的监测数据：\n{grounding['context_text']}"
            )
            messages = [item.model_dump() for item in payload.history[-10:]]
            messages.append({"role": "user", "content": prompt})
            buffered_tokens: list[str] = []
            model_failed = False
            async for token in stream_chat(messages, temperature=0.2, max_tokens=900):
                if "[错误]" in token:
                    model_failed = True
                    break
                buffered_tokens.append(token)

            warnings: list[str] = []
            if model_failed or not buffered_tokens:
                warnings.append("MODEL_UNAVAILABLE_RULE_FALLBACK")
                yield sse("answer_delta", {"content": grounding["fallback_answer"]})
            else:
                for token in buffered_tokens:
                    yield sse("answer_delta", {"content": token})

            yield sse("citations_ready", {"citations": grounding["citations"]})
            yield sse("actions_ready", {"actions": grounding["actions"]})
            yield sse("completed", {"warnings": warnings})
        except Exception:
            logger.exception("结构化研判失败")
            yield sse("error", {"content": "研判服务暂不可用，请稍后重试"})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
```

The model output is buffered until the existing `[错误]` marker has been ruled out. This prevents the exception details currently embedded in that marker from leaking to the browser. Register the router in `backend/main.py`:

```py
from routers import assistant, chart_data, data_preprocess, enterprise_recognition, model_validate, monitoring, output_calc

app.include_router(monitoring.router, prefix="/api/monitoring", tags=["统计监测"])
app.include_router(assistant.router, prefix="/api/assistant", tags=["智能研判"])
```

- [ ] **Step 5: Run backend tests**

Run: `.\.venv\Scripts\python.exe -m unittest discover -s tests -v`  
Expected: PASS, 4 tests.

- [ ] **Step 6: Write failing split-SSE tests**

Create `frontend/tests/sse.test.js`:

```js
import test from 'node:test'
import assert from 'node:assert/strict'
import { consumeSseChunk } from '../src/features/assistant/sse.js'

test('parser preserves a split event until the next chunk', () => {
  const first = consumeSseChunk('', 'data: {"type":"answer_')
  assert.deepEqual(first.events, [])
  const second = consumeSseChunk(first.remainder, 'delta","content":"结论"}\n\n')
  assert.equal(second.events[0].type, 'answer_delta')
  assert.equal(second.events[0].content, '结论')
  assert.equal(second.remainder, '')
})

test('parser returns multiple complete events', () => {
  const result = consumeSseChunk('', 'data: {"type":"tool_started"}\n\ndata: {"type":"completed"}\n\n')
  assert.deepEqual(result.events.map((event) => event.type), ['tool_started', 'completed'])
})
```

- [ ] **Step 7: Implement the parser, API, and assistant store**

Create `frontend/src/features/assistant/sse.js`:

```js
export function consumeSseChunk(buffer, chunk) {
  const parts = `${buffer}${chunk}`.split('\n\n')
  const remainder = parts.pop() || ''
  const events = parts.flatMap((part) => {
    const line = part.split('\n').find((value) => value.startsWith('data: '))
    if (!line) return []
    try { return [JSON.parse(line.slice(6))] } catch { return [] }
  })
  return { events, remainder }
}
```

Create `frontend/src/api/assistant.js`:

```js
export function streamAssistant(payload, signal) {
  return fetch('/api/assistant/stream', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload), signal })
}
```

Create `frontend/src/store/assistant.js`:

```js
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { streamAssistant } from '../api/assistant'
import { consumeSseChunk } from '../features/assistant/sse'

export const useAssistantStore = defineStore('assistant', () => {
  const messages = ref([]); const progress = ref(''); const citations = ref([]); const actions = ref([]); const warnings = ref([]); const isStreaming = ref(false); const metadata = ref({})
  let controller = null
  function applyEvent(event, assistantMessage) {
    if (event.type === 'context_ready') metadata.value = event
    if (event.type === 'tool_started') progress.value = `正在${event.label}`
    if (event.type === 'tool_finished') progress.value = `${event.label}完成`
    if (event.type === 'answer_delta') assistantMessage.content += event.content || ''
    if (event.type === 'citations_ready') citations.value = event.citations || []
    if (event.type === 'actions_ready') actions.value = event.actions || []
    if (event.type === 'completed') { warnings.value = event.warnings || []; progress.value = '分析完成' }
    if (event.type === 'error') { warnings.value = [event.content || '研判服务暂不可用']; progress.value = '分析中断' }
  }
  async function send(message, context, history = []) {
    if (!message.trim() || isStreaming.value) return
    const priorHistory = history.length ? history : messages.value.map(({ role, content }) => ({ role, content }))
    const userMessage = { role: 'user', content: message.trim() }
    const assistantMessage = { role: 'assistant', content: '' }
    messages.value.push(userMessage, assistantMessage); citations.value = []; actions.value = []; warnings.value = []; progress.value = '正在获取上下文'; isStreaming.value = true
    controller = new AbortController()
    try {
      const response = await streamAssistant({ message: userMessage.content, history: priorHistory, context, file_id: context.fileId || null }, controller.signal)
      if (!response.ok) throw new Error(`HTTP ${response.status}`)
      const reader = response.body.getReader(); const decoder = new TextDecoder(); let buffer = ''
      while (true) {
        const { done, value } = await reader.read(); if (done) break
        const parsed = consumeSseChunk(buffer, decoder.decode(value, { stream: true })); buffer = parsed.remainder
        parsed.events.forEach((event) => applyEvent(event, assistantMessage))
      }
    } catch (error) {
      if (error.name !== 'AbortError') { warnings.value = ['研判服务暂不可用，请重试']; progress.value = '分析中断' }
    } finally { isStreaming.value = false; controller = null }
  }
  function cancel() { controller?.abort() }
  function reset() { cancel(); messages.value = []; progress.value = ''; citations.value = []; actions.value = []; warnings.value = [] }
  return { messages, progress, citations, actions, warnings, isStreaming, metadata, send, cancel, reset }
})
```

- [ ] **Step 8: Implement both assistant surfaces**

Create `frontend/src/components/assistant/ContextAssistantPanel.vue`:

```vue
<template><section class="context-assistant"><header><span>智能研判</span><DataModeBadge :provenance="provenance"/></header><div class="chips"><span>{{ context.region }}</span><span>{{ context.year }} 年度</span><span>{{ context.selectedRiskId || '当前驾驶舱' }}</span></div><h2>传统方法为何低估体育产业规模？</h2><p v-if="latest">{{ latest.content }}</p><p v-else>输入问题后，系统会引用当前数据批次和模型版本回答。</p><div class="citations"><small v-for="item in citations" :key="item.id">{{ item.label }}：{{ item.value }}</small></div><form @submit.prevent="submit"><el-input v-model="input" placeholder="询问指标、风险原因或测算差异"/><el-button native-type="submit" type="warning" :loading="isStreaming">发送</el-button></form></section></template>
<script setup>
import { computed, ref } from 'vue'
import { storeToRefs } from 'pinia'
import DataModeBadge from '../common/DataModeBadge.vue'
import { useAssistantStore } from '../../store/assistant'
const props = defineProps({ context: { type: Object, required: true }, provenance: { type: Object, required: true } })
const assistant = useAssistantStore(); const { messages, citations, isStreaming } = storeToRefs(assistant); const input = ref('')
const latest = computed(() => [...messages.value].reverse().find((item) => item.role === 'assistant'))
function submit() { const value = input.value.trim(); if (!value) return; assistant.send(value, props.context); input.value = '' }
</script>
<style scoped>
.context-assistant { height: 100%; display: flex; flex-direction: column; padding: 16px; border-radius: var(--sf-radius-md); background: var(--sf-ink); color: white; }.context-assistant header { display: flex; justify-content: space-between; align-items: center; }.chips { display: flex; flex-wrap: wrap; gap: 5px; margin-top: 12px; }.chips span, .citations small { padding: 5px 7px; border-radius: 5px; background: #304247; font-size: 11px; }.context-assistant h2 { margin: 16px 0 8px; font-size: 18px; line-height: 1.45; }.context-assistant p { color: #d2d8d6; line-height: 1.65; }.citations { display: grid; gap: 5px; margin-top: auto; }.context-assistant form { display: grid; grid-template-columns: 1fr 62px; gap: 6px; margin-top: 10px; }
</style>
```

Create `frontend/src/views/AnalysisAssistant.vue` with a three-column desktop layout. Use this complete script contract and action handling:

```vue
<template>
  <section class="assistant-workspace">
    <aside class="sessions"><h2>分析会话</h2><el-button type="primary" @click="assistant.reset()">新建研判</el-button><button class="session active" type="button">当前分析<small>{{ context.selectedRiskId || '综合监测' }}</small></button></aside>
    <main class="conversation"><header><h1>智能决策问答</h1><p>基于当前数据批次、模型版本与风险证据</p></header><div class="messages"><article v-for="(message, index) in messages" :key="index" :data-role="message.role"><span>{{ message.role === 'user' ? '问题' : '研判' }}</span><p>{{ message.content }}</p></article><el-empty v-if="!messages.length" description="可询问测算差异、风险原因或企业边界"/></div><el-alert v-if="warnings.length" :title="warnings.join('；')" type="warning" :closable="false"/><p class="progress">{{ progress }}</p><div class="action-row"><el-button v-for="action in actions" :key="action.id" @click="handleAction(action)">{{ action.label }}</el-button></div><form @submit.prevent="submit"><el-input v-model="input" type="textarea" :rows="3" placeholder="输入分析问题或执行指令"/><el-button type="primary" native-type="submit" :loading="isStreaming">发送</el-button></form></main>
    <aside class="inspector"><h2>依据与参数</h2><DataModeBadge :provenance="snapshot.provenance"/><dl><dt>数据版本</dt><dd>{{ snapshot.provenance.data_version }}</dd><dt>模型版本</dt><dd>{{ snapshot.provenance.model_version }}</dd></dl><h3>引用依据</h3><article v-for="item in citations" :key="item.id"><strong>{{ item.label }}</strong><p>{{ item.value }}</p><small>{{ item.data_version }} · {{ item.model_version }}</small></article></aside>
    <el-dialog v-model="previewOpen" title="操作预览" width="480px"><p>{{ previewText }}</p><template #footer><el-button @click="previewOpen = false">取消</el-button><el-button type="warning" @click="confirmAction">确认继续</el-button></template></el-dialog>
  </section>
</template>
<script setup>
import { computed, onMounted, ref } from 'vue'
import { storeToRefs } from 'pinia'
import { useRoute, useRouter } from 'vue-router'
import DataModeBadge from '../components/common/DataModeBadge.vue'
import { useAssistantStore } from '../store/assistant'
import { useAnalysisContextStore } from '../store/analysis-context'
import { useMonitoringStore } from '../store/monitoring'
const route = useRoute(); const router = useRouter(); const assistant = useAssistantStore(); const contextStore = useAnalysisContextStore(); const monitoring = useMonitoringStore()
const { messages, progress, citations, actions, warnings, isStreaming } = storeToRefs(assistant); const { snapshot } = storeToRefs(monitoring); const context = contextStore.context
const input = ref(''); const previewOpen = ref(false); const pendingAction = ref(null); const previewText = computed(() => pendingAction.value?.type === 'preview_report' ? `将使用数据版本 ${snapshot.value.provenance.data_version} 生成报告。` : `将针对风险 ${pendingAction.value?.payload?.risk_id || ''} 运行校正测算预览。`)
function submit() { const value = input.value.trim(); if (!value) return; assistant.send(value, context); input.value = '' }
function handleAction(action) { if (action.type === 'open_risk') router.push(`/risks?risk_id=${action.payload.risk_id}`); else if (action.type === 'navigate') router.push(action.payload.path); else { pendingAction.value = action; previewOpen.value = true } }
function confirmAction() { const action = pendingAction.value; previewOpen.value = false; if (action?.type === 'preview_report') router.push('/export') }
onMounted(() => { if (route.query.risk_id) contextStore.patch({ selectedRiskId: String(route.query.risk_id) }) })
</script>
<style scoped>
.assistant-workspace { min-height: calc(100vh - 32px); display: grid; grid-template-columns: 190px minmax(0, 1fr) 280px; overflow: hidden; border: 1px solid var(--sf-line); border-radius: var(--sf-radius-lg); background: var(--sf-surface); box-shadow: var(--sf-shadow); }.sessions, .inspector { padding: 18px; background: var(--sf-surface-muted); }.inspector { background: var(--sf-surface); border-left: 1px solid var(--sf-line); }.conversation { display: flex; min-width: 0; flex-direction: column; padding: 20px; }.messages { flex: 1; overflow: auto; }.messages article { max-width: 82%; margin: 12px 0; padding: 12px; border-radius: 9px; background: #f3efe7; }.messages article[data-role="user"] { margin-left: auto; background: var(--sf-blue); color: white; }.messages span { font-size: 11px; font-weight: 800; }.messages p { white-space: pre-wrap; }.conversation form { display: grid; grid-template-columns: 1fr 88px; gap: 8px; }.inspector dl { display: grid; grid-template-columns: 1fr auto; gap: 8px; }.inspector article { margin-top: 8px; padding: 10px; border-radius: 6px; background: #f4f0e8; }.session { width: 100%; margin-top: 12px; padding: 10px; border: 0; border-radius: 6px; background: var(--sf-surface); text-align: left; }.session small { display: block; color: var(--sf-muted); } @media (max-width: 1100px) { .assistant-workspace { grid-template-columns: 150px 1fr; }.inspector { display: none; } }
</style>
```

Map assistant actions exactly:

```js
const actionHandlers = {
  open_risk: (action) => router.push(`/risks?risk_id=${action.payload.risk_id}`),
  navigate: (action) => router.push(action.payload.path),
  preview_recalculation: (action) => openPreview('recalculation', action),
  preview_report: (action) => openPreview('report', action),
}
```

The confirmation dialog for reports routes to `/export` after confirmation. Do not automatically download a file.

Replace the static insight panel in `MonitoringCockpit.vue` with `<ContextAssistantPanel :context="analysisContext.context" :provenance="snapshot.provenance" />`.

- [ ] **Step 9: Register the assistant route and verify**

Replace the assistant redirect with:

```js
{ path: '/assistant', name: 'AnalysisAssistant', component: () => import('../views/AnalysisAssistant.vue'), meta: { title: '智能决策问答' } },
```

Run: `npm test`  
Expected: PASS, 8 tests.

Run: `npm run build`  
Expected: exits 0.

Manual checks:
- ask “为什么模型比传统方法高”； answer includes `18.7%` and citation cards;
- turn off the DeepSeek key; the same request returns a rule fallback with a visible warning;
- “查看风险证据” opens the matching risk;
- report action opens a preview before routing;
- no message says “小融” and no emoji is rendered.

- [ ] **Step 10: Record checkpoint**

Suggested commit: `feat: add grounded analysis assistant`  
If Git is available: `git add backend frontend && git commit -m "feat: add grounded analysis assistant"`

---

### Task 6: Add the model evaluation page and run final acceptance

**Files:**
- Create: `frontend/src/views/ModelEvaluation.vue`
- Modify: `frontend/src/router/index.js`
- Modify: `frontend/src/views/ReportExport.vue`
- Modify: `README.md`

**Interfaces:**
- Consumes: `snapshot.model_metrics`.
- Produces: route `/model-evaluation`.
- Preserves: existing downloadable report URLs.

- [ ] **Step 1: Implement the model evaluation page**

Create `frontend/src/views/ModelEvaluation.vue`:

```vue
<template>
  <section class="page-shell evaluation-page">
    <header class="page-heading"><div><h1>模型性能评估</h1><p>准确性、异常输入表现与资源消耗</p></div><div><DataModeBadge :provenance="snapshot.provenance"/><el-button @click="router.push('/compare')">查看传统方法对比</el-button></div></header>
    <el-alert v-if="snapshot.provenance.mode === 'demo'" title="当前显示演示评测数据" type="info" :closable="false" show-icon/>
    <template v-if="hasEvaluation">
      <h2>识别效果</h2><div class="metric-grid"><MetricCard label="综合一致率" :value="rate(metrics.accuracy)" unit="%" note="当前结果为代理评估，不等同人工金标准准确率" tone="blue"/><MetricCard label="Precision" :value="rate(metrics.precision)" unit="%" note="模型识别结果与传统口径的交集比例" tone="teal"/><MetricCard label="Recall" :value="rate(metrics.recall)" unit="%" note="传统口径样本被模型覆盖的比例" tone="yellow"/><MetricCard label="MAE" :value="Number(metrics.mae || 0).toFixed(3)" unit="" note="经营比重差异的平均绝对误差" tone="red"/></div>
      <h2>异常输入测试</h2><div class="robust-grid"><article v-for="item in robustness" :key="item.label"><span>{{ item.label }}</span><strong>{{ rate(item.value) }}%</strong><el-progress :percentage="rate(item.value)" :show-text="false"/></article></div>
      <h2>运行效率</h2><div class="efficiency"><article><span>单万条记录耗时</span><strong>{{ metrics.runtime_seconds_per_10k }} 秒</strong></article><article><span>峰值内存</span><strong>{{ metrics.peak_memory_mb }} MB</strong></article><p>数据版本 {{ snapshot.provenance.data_version }} · 模型版本 {{ snapshot.provenance.model_version }}</p></div>
    </template>
    <el-empty v-else description="当前真实批次尚未生成模型评测与异常输入测试结果"><el-button type="primary" @click="router.push('/compare')">运行模型评估</el-button></el-empty>
  </section>
</template>
<script setup>
import { computed, onMounted } from 'vue'
import { storeToRefs } from 'pinia'
import { useRouter } from 'vue-router'
import DataModeBadge from '../components/common/DataModeBadge.vue'
import MetricCard from '../components/monitoring/MetricCard.vue'
import { useMonitoringStore } from '../store/monitoring'
import { useDataStore } from '../store/data'
const router = useRouter(); const monitoring = useMonitoringStore(); const dataStore = useDataStore(); const { snapshot } = storeToRefs(monitoring)
const metrics = computed(() => snapshot.value.model_metrics || {})
const hasEvaluation = computed(() => Object.keys(metrics.value).length > 0)
const rate = (value) => Number((Number(value || 0) * 100).toFixed(1))
const robustness = computed(() => [{ label: '正常样本', value: metrics.value.normal_input_pass_rate }, { label: '缺失文本', value: metrics.value.missing_text_pass_rate }, { label: '噪声输入', value: metrics.value.noise_input_pass_rate }])
onMounted(() => monitoring.refresh(dataStore.queryParams.fileId))
</script>
<style scoped>
.page-heading > div:last-child { display: flex; align-items: center; gap: 8px; }.metric-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }.evaluation-page h2 { margin: 22px 0 10px; font-size: 16px; }.robust-grid, .efficiency { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }.robust-grid article, .efficiency article { padding: 16px; border: 1px solid var(--sf-line); border-radius: var(--sf-radius-md); background: var(--sf-surface); }.robust-grid strong, .efficiency strong { display: block; margin: 8px 0; font-size: 24px; }.efficiency { grid-template-columns: 1fr 1fr; }.efficiency p { grid-column: 1 / -1; color: var(--sf-muted); } @media (max-width: 1000px) { .metric-grid { grid-template-columns: 1fr 1fr; }.robust-grid { grid-template-columns: 1fr; } }
</style>
```

Format rates with the `rate` helper; do not label `accuracy` as a human-labeled ground-truth score while the backend returns proxy evaluation.

- [ ] **Step 2: Register the model route**

Replace the model redirect with:

```js
{ path: '/model-evaluation', name: 'ModelEvaluation', component: () => import('../views/ModelEvaluation.vue'), meta: { title: '模型性能评估' } },
```

- [ ] **Step 3: Align the report center with the new shell**

Keep every existing export URL in `ReportExport.vue`. Change each template click handler from `downloadFile('<type>')` to `requestDownload('<type>')`, add `DataModeBadge` beside the page title, and insert this dialog immediately before the closing root `</div>`:

```vue
<el-dialog v-model="confirmVisible" title="确认生成并下载" width="480px">
  <el-descriptions :column="1" border>
    <el-descriptions-item label="成果类型">{{ reportLabels[pendingType] || pendingType }}</el-descriptions-item>
    <el-descriptions-item label="数据文件">{{ dataStore.queryParams.fileId || '未选择' }}</el-descriptions-item>
    <el-descriptions-item label="数据状态"><DataModeBadge :provenance="snapshot.provenance" /></el-descriptions-item>
    <el-descriptions-item label="数据版本">{{ snapshot.provenance.data_version }}</el-descriptions-item>
  </el-descriptions>
  <template #footer><el-button @click="confirmVisible = false">取消</el-button><el-button type="warning" @click="confirmDownload">确认下载</el-button></template>
</el-dialog>
```

Add these imports and state in `<script setup>`:

```js
import { storeToRefs } from 'pinia'
import DataModeBadge from '../components/common/DataModeBadge.vue'
import { useMonitoringStore } from '../store/monitoring'

const monitoring = useMonitoringStore()
const { snapshot } = storeToRefs(monitoring)
const confirmVisible = ref(false)
const pendingType = ref('')
const reportLabels = {
  enterprise_dataset: '完整企业数据集', sport_enterprises: '体育企业子集', features: '特征数据集',
  final_report: '完整研究报告', optimization: '统计方法优化方案', policy: '结构化政策建议',
  data_doc: '数据文档说明', industry_analysis: '产业分析报告', model_validation: '模型验证报告',
}
```

Replace the current `onMounted` callback and `downloadFile` entry with the confirmation boundary below. Keep the current `fileMap` and temporary-anchor code inside `downloadFile` unchanged.

```js
onMounted(async () => {
  await Promise.all([loadSummary(), monitoring.refresh(dataStore.queryParams.fileId)])
})

function requestDownload(type) {
  if (!dataStore.queryParams.fileId) {
    ElMessage.warning('请先在数据管理页面上传并处理数据')
    return
  }
  pendingType.value = type
  confirmVisible.value = true
}

function confirmDownload() {
  const type = pendingType.value
  confirmVisible.value = false
  pendingType.value = ''
  downloadFile(type)
}
```

Leave the existing `downloadFile(type)` implementation intact. Use `var(--sf-blue)`, `var(--sf-teal)`, `var(--sf-yellow)`, and `var(--sf-surface-muted)` for the four existing hard-coded card colors. Do not change paths or automatically start a download before `confirmDownload()`.

- [ ] **Step 4: Update operating documentation**

Add these sections to `README.md` in UTF-8:

```md
## 比赛演示入口

- `/monitoring`：统计监测驾驶舱
- `/risks`：风险事件中心
- `/assistant`：智能决策问答
- `/model-evaluation`：模型性能评估

## 数据状态

系统按真实数据、历史快照、演示数据保障三种模式运行。页面顶部和导出确认框会显示当前模式；不同模式的数据不会混合到同一份结果中。
```

- [ ] **Step 5: Run automated verification**

Run from `backend`:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m compileall main.py routers services
```

Expected: 4 tests pass; compileall exits 0.

Run from `frontend`:

```powershell
npm test
npm run build
```

Expected: 8 tests pass; Vite build exits 0.

- [ ] **Step 6: Run content and route checks**

Run from the project root:

```powershell
Select-String -Path '.\frontend\src\App.vue','.\frontend\src\views\MonitoringCockpit.vue','.\frontend\src\views\AnalysisAssistant.vue' -Pattern '小融|👋|💡|🤖'
```

Expected: no matches.

Run:

```powershell
Select-String -Path '.\frontend\src\router\index.js' -Pattern "'/monitoring'|'/risks'|'/assistant'|'/model-evaluation'"
```

Expected: all four routes are present.

- [ ] **Step 7: Run the end-to-end demo path**

Start the backend with `.\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000` from `backend` and the frontend with `npm run dev -- --host 127.0.0.1` from `frontend`.

Verify in this order:

1. `/monitoring` shows four score cards and explicit data mode.
2. Selecting `R-2025-071` opens `/risks` with evidence.
3. “进入智能研判” opens `/assistant` with the risk context.
4. The assistant returns citations and action buttons.
5. Report generation requires confirmation and routes to `/export`.
6. `/model-evaluation` shows accuracy, robustness, runtime, and memory.
7. At 1920×1080, the cockpit has no horizontal scroll and the core cockpit grid is visible before page scrolling.

- [ ] **Step 8: Record final checkpoint**

Suggested commit: `feat: complete competition monitoring experience`  
If Git is available: `git add README.md backend frontend docs && git commit -m "feat: complete competition monitoring experience"`

---

## Self-review record

- Spec coverage: cockpit, risk lifecycle, assistant, provenance, model evaluation, report confirmation, accessibility, and demo fallback all map to a task.
- Placeholder scan: all implementation steps include concrete paths, interfaces, commands, and expected outcomes.
- Type consistency: `RiskType`, `RiskLevel`, provenance modes, route names, and structured SSE event names match the approved design specification.
- Data isolation: demo risks, the 18.7% method gap, and demo model metrics can only enter a `demo` snapshot. Partial real snapshots retain empty fields plus `missing_fields`, and the UI renders unavailable states.
- Test accounting: the finished frontend suite contains 8 Node tests and the backend suite contains 4 `unittest` cases.
- Scope: the plan delivers the first-phase competition loop and reuses existing recognition, measurement, chart, and export logic rather than rewriting algorithms.
