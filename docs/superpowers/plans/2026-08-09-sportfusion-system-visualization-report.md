# SportFusion System Visualization Report Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the source report's Figure 4-2 placeholder with nine truthful, readable SportFusion system screenshots, add concise explanatory text, audit report-system consistency, and deliver a visually verified DOCX while preserving the source.

**Architecture:** Run the existing FastAPI and Vue applications without changing their source, capture nine fixed routes from one release and data context, create presentation-safe annotated copies, then patch only the Figure 4-2 block in a copied DOCX. Keep raw captures, processed images, audit evidence, build logic, rendered pages, and the final report in separate directories so every transformation remains traceable.

**Tech Stack:** Existing FastAPI/Vue application; Microsoft Edge headless capture; bundled Python 3 with Pillow, python-docx, and lxml; documents-skill `render_docx.py`; PowerShell process orchestration.

## Global Constraints

- Preserve the source DOCX and create a new output file under `formal_artifacts/system_visualization/`.
- Preserve the report's cover, contents, five chapters, appendices, existing figures, tables, and unified data definitions.
- Use only real system pages and real page states; image processing may not change values, charts, data mode, batch, model status, or conclusions.
- Use one code revision, one batch context, one data mode, and a 1920 x 1080 viewport for all screenshots.
- If a route cannot show a valid formal state, capture the truthful state and label it as a functional demonstration; do not fabricate successful output.
- Unsupported comparison, ablation, or performance evidence remains explicitly bounded and is never replaced with invented numbers.
- The final DOCX must render to page PNGs and every page must be visually inspected before delivery.

---

### Task 0: Repair Review API and Service Contract Drift

**Files:**
- Create: `tests/api/test_review_api_contract.py`
- Modify: `backend/api/review.py`
- Modify: `backend/models/schemas.py`

**Interfaces:**
- Consumes: `ReviewTask`, `create_review_tasks`, `submit_review`, `arbitrate`, and `get_review_stats` from `backend/services/review_workflow_service.py`.
- Produces: importable FastAPI application and frontend-compatible `/api/review` responses using stable string task IDs.

- [ ] **Step 1: RED — prove the application import fails because the API uses removed service names**

Add a test that imports `main.app` inside `try/except ImportError` and calls `pytest.fail` with the missing symbol. Run only that test and require an assertion failure naming `generate_review_tasks`.

- [ ] **Step 2: GREEN — align imports without changing behavior**

Replace removed imports with `create_review_tasks`, `submit_review`, `arbitrate`, and `get_review_stats`. Run the import test and require PASS.

- [ ] **Step 3: RED/GREEN — restore task generation and serialization**

Test `POST /api/review/tasks/generate` with two real recognition dictionaries. Require HTTP 200, string `id`, `sport_share`, flat frontend statistics, and P1—P4 counts. Implement `task_to_api`, `stats_to_api`, and generation through `create_review_tasks` until the test passes.

- [ ] **Step 4: RED/GREEN — restore list, assignment, and detail**

Test list filters, string-ID detail lookup, and assignment payloads. Widen `ReviewTaskAssignRequest.task_ids` to accept string IDs, set `reviewer_a`/`reviewer_b`, and serialize `assigned_to_a`/`assigned_to_b` plus Chinese status labels.

- [ ] **Step 5: RED/GREEN — restore dual review, consensus, and arbitration**

Test A/B agreement and disagreement through the real service. Widen review and arbitration request task IDs to strings, adapt request field names to service parameters, derive consensus from `a_result`/`b_result`, and expose arbitration as a locked API state without changing the service's domain tests.

- [ ] **Step 6: Verify the repaired backend baseline**

Run the focused API tests, `tests/api/test_api_smoke.py`, the three Phase 4 workflow suites, and then all 626 backend tests. Expected: no new failures; any pre-existing strict xfail remains xfailed.

---

### Task 1: Reproducible Capture Harness

**Files:**
- Create: `scripts/report_visualization/route_manifest.json`
- Create: `scripts/report_visualization/capture_system.ps1`
- Create at runtime: `formal_artifacts/system_visualization/raw/*.png`
- Create at runtime: `formal_artifacts/system_visualization/logs/*.log`

**Interfaces:**
- Consumes: the current repository, bundled Python runtime, existing `frontend/node_modules`, and Edge at `C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe`.
- Produces: nine raw PNGs keyed by `id`, plus service logs and a capture manifest.

- [ ] **Step 1: Define the route manifest**

Create a JSON array with these exact route records:

```json
[
  {"id":"a-monitoring","route":"/monitoring","title":"统计监测驾驶舱","focus":"批次口径、五步工作流与区域风险"},
  {"id":"b-data","route":"/data","title":"企业数据治理","focus":"数据导入、清洗、解析与过程追踪"},
  {"id":"c-recognition","route":"/recognition","title":"企业边界识别","focus":"文本—代码双通道证据与SportScore"},
  {"id":"d-share","route":"/compare","title":"经营比重测算","focus":"SportShare来源、区间与结构权重"},
  {"id":"e-scale","route":"/industry-analysis","title":"产业规模分析","focus":"区域与九类业态规模结构"},
  {"id":"f-evaluation","route":"/model-evaluation","title":"模型性能评估","focus":"可复算指标、边界与异常状态"},
  {"id":"g-review","route":"/review","title":"人工复核工作台","focus":"P1—P4优先级、双人复核与仲裁"},
  {"id":"h-directory","route":"/directory","title":"动态企业名录","focus":"finalized过滤、状态与证据追溯"},
  {"id":"i-export","route":"/export","title":"报告与成果导出","focus":"批次锁定、版本信息与结构化输出"}
]
```

- [ ] **Step 2: Implement hidden service startup and capture**

The PowerShell script must:

```powershell
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$python = 'C:\Users\25113\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$node = 'C:\Users\25113\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe'
$edge = 'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
$artifact = Join-Path $root 'formal_artifacts\system_visualization'
$raw = Join-Path $artifact 'raw'
$logs = Join-Path $artifact 'logs'
New-Item -ItemType Directory -Force -Path $raw,$logs | Out-Null

$backend = Start-Process -FilePath $python -ArgumentList '-m','uvicorn','main:app','--host','127.0.0.1','--port','8000' -WorkingDirectory (Join-Path $root 'backend') -WindowStyle Hidden -RedirectStandardOutput (Join-Path $logs 'backend.out.log') -RedirectStandardError (Join-Path $logs 'backend.err.log') -PassThru
$frontend = Start-Process -FilePath $node -ArgumentList (Join-Path $root 'frontend\node_modules\vite\bin\vite.js'),'--host','127.0.0.1','--port','5173' -WorkingDirectory (Join-Path $root 'frontend') -WindowStyle Hidden -RedirectStandardOutput (Join-Path $logs 'frontend.out.log') -RedirectStandardError (Join-Path $logs 'frontend.err.log') -PassThru
try {
  foreach ($uri in 'http://127.0.0.1:8000/','http://127.0.0.1:5173/monitoring') {
    $ready = $false
    for ($i=0; $i -lt 30 -and -not $ready; $i++) {
      try { $ready = (Invoke-WebRequest -UseBasicParsing -TimeoutSec 2 -Uri $uri).StatusCode -eq 200 } catch { Start-Sleep -Milliseconds 500 }
    }
    if (-not $ready) { throw "Service did not become ready: $uri" }
  }
  $manifest = Get-Content (Join-Path $PSScriptRoot 'route_manifest.json') -Raw -Encoding UTF8 | ConvertFrom-Json
  foreach ($item in $manifest) {
    $target = Join-Path $raw ($item.id + '.png')
    & $edge '--headless=new' '--disable-gpu' '--hide-scrollbars' '--window-size=1920,1080' '--virtual-time-budget=10000' ("--screenshot=$target") ("http://127.0.0.1:5173" + $item.route)
    if (-not (Test-Path -LiteralPath $target)) { throw "Missing screenshot: $target" }
  }
} finally {
  Stop-Process -Id $frontend.Id,$backend.Id -Force -ErrorAction SilentlyContinue
}
```

- [ ] **Step 3: Run the capture harness**

Run:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\report_visualization\capture_system.ps1
```

Expected: nine non-empty PNGs under `formal_artifacts/system_visualization/raw/`; both services terminate after capture.

- [ ] **Step 4: Verify image geometry and route coverage**

Run:

```powershell
& 'C:\Users\25113\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -X utf8 -c "from pathlib import Path; from PIL import Image; p=Path('formal_artifacts/system_visualization/raw'); f=sorted(p.glob('*.png')); assert len(f)==9, len(f); [(lambda im,n: (print(n, im.size), (_ for _ in ()).throw(AssertionError(n)) if im.width<1800 or im.height<900 else None))(Image.open(x),x.name) for x in f]"
```

Expected: nine filenames and dimensions at least 1800 x 900.

---

### Task 2: Data-Mode and Content Audit

**Files:**
- Create: `formal_artifacts/system_visualization/audit.md`
- Read: `data/batches/batch_index.json`
- Read: `frontend/src/config/navigation.js`
- Read: `frontend/src/router/index.js`
- Read: current system API responses.

**Interfaces:**
- Consumes: raw screenshots, route manifest, report core figures, batch metadata, and live API responses.
- Produces: a written accept/reject decision for each screenshot and a list of report-safe claims.

- [ ] **Step 1: Record the repository and batch identity**

Run `git rev-parse HEAD`, inspect `data/batches/batch_index.json`, and query `GET /api/system/batches`; record the exact commit, selected batch, data mode, lock state, and source timestamps in `audit.md`.

- [ ] **Step 2: Check report-system terminology and core sets**

Compare page labels and visible values against the report's fixed relationships: 8,950 candidates, 8,016 traditional direct-code coverage, 934 added candidates, 2022 Sichuan total output of 2,170.80 亿元, and the separation of SportScore from SportShare. Record every screenshot as `accepted`, `accepted-as-functional-demo`, or `rejected` with a one-sentence reason.

- [ ] **Step 3: Inspect all raw screenshots visually**

Open each PNG at original resolution. Reject images with load failures, skeleton screens, clipped navigation, illegible charts, contradictory data-mode badges, or modal overlays. Re-capture only the affected route after correcting legitimate page state; do not retouch a failure into success.

- [ ] **Step 4: Verify no unsupported evidence is introduced**

Search the candidate captions and analysis text for comparison, ablation, MAE, RMSE, R², Spearman, F1, and AUC claims. Keep only values already supported by the current report and audit trail; otherwise retain the report's explicit evidence boundary or the phrase `待补真实实验数据`.

---

### Task 3: Presentation-Safe Screenshot Processing

**Files:**
- Create: `scripts/report_visualization/annotate_screenshots.py`
- Create at runtime: `formal_artifacts/system_visualization/processed/*.png`
- Read: `scripts/report_visualization/route_manifest.json`

**Interfaces:**
- Consumes: nine accepted raw PNGs and each route's `title` and `focus`.
- Produces: nine processed 1920 x 1080 PNGs without changing the screenshot's data region.

- [ ] **Step 1: Implement deterministic annotation**

Implement `annotate(source: Path, target: Path, title: str, focus: str) -> None` with Pillow. It must preserve the full screenshot pixels inside a new canvas, add a 10-pixel navy border outside the raw-image rectangle, and add a bottom caption strip containing `系统实景｜title` and `focus`. Load a Chinese font from `C:\Windows\Fonts\msyh.ttc`; use 30 pt for the title and 22 pt for the focus text. The script must never draw over the raw screenshot.

- [ ] **Step 2: Generate all processed images**

Run:

```powershell
& 'C:\Users\25113\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -X utf8 scripts\report_visualization\annotate_screenshots.py
```

Expected: nine processed PNGs and an error if any raw source is missing.

- [ ] **Step 3: Prove screenshot pixels were not altered**

For every pair, crop the processed image to the embedded raw-image rectangle and compare it byte-for-byte with the raw image using `ImageChops.difference(...).getbbox() is None`. Expected: `PASS` for all nine images.

- [ ] **Step 4: Visually inspect all processed images**

Open every processed PNG at original resolution and confirm labels are legible, nothing is covered, no value is changed, and the presentation treatment is consistent.

---

### Task 4: Patch the Report's Figure 4-2 Block

**Files:**
- Create: `scripts/report_visualization/build_visual_report.py`
- Read: `C:\Users\25113\Downloads\体融识界·SportFusion——多元经营背景下企业体育业务识别与区域产业规模估算（基于文本—代码双通道与可解释证据融合技术）_系统口径同步.docx`
- Create: `formal_artifacts/system_visualization/体融识界·SportFusion_系统可视化完善版.docx`

**Interfaces:**
- Consumes: source DOCX, processed screenshots, route manifest, and accepted claims in `audit.md`.
- Produces: a copied DOCX whose Figure 4-2 placeholder is replaced by nine subfigures plus one audit-bounded analysis paragraph.

- [ ] **Step 1: Locate the exact insertion block and fail closed**

Implement `find_unique_paragraph(document, text)` and require exactly one paragraph whose text is `图4-2 SportFusion Web系统演示路径与截图预留`. Require the following note to start with `数据来源：本项目当前系统功能结构整理`. Abort if either anchor is absent or duplicated.

- [ ] **Step 2: Remove only the placeholder visual**

Walk backward from the Figure 4-2 caption to the nearest preceding body paragraph containing `w:drawing`; require that no non-empty narrative paragraph lies between it and the caption. Remove that drawing paragraph and the old placeholder caption/note, leaving all other paragraphs, tables, styles, headers, footers, and section properties untouched.

- [ ] **Step 3: Insert nine subfigures with stable formatting**

Insert each processed PNG before the original Figure 4-2 position at 15.4 cm width, centered. Add a caption using the source document's `图表题注` style with text `图4-2（a）统计监测驾驶舱` through `图4-2（i）报告与成果导出`; add a short `图表注释` paragraph describing the visible function and data-mode boundary. Set `keep_with_next` on each image paragraph and `keep_together` on each caption. Insert a page break after every second subfigure so the screenshots remain readable.

- [ ] **Step 4: Insert the integrated analysis paragraph**

Add one body paragraph after Figure 4-2（i） that states, without new unsupported numbers: the innovation is one-batch evidence fusion and closed-loop statistics; the implementation uses Vue 3, ECharts, FastAPI, repository persistence, batch IDs, provenance, and locked exports; the pain point addressed is fragmented code/text evidence and weak reproducibility; the verifiable effect is that the same batch can be traced from governance through recognition, SportShare, scale, review, directory, and export. Explicitly state that functional-demonstration screenshots do not replace Chapter 3 empirical evidence.

- [ ] **Step 5: Save and run structural assertions**

Open the output again with python-docx and assert: nine `图4-2（` captions, at least 27 inline shapes, exactly one integrated analysis paragraph, unchanged section count, and unchanged counts/text for all pre-existing table captions. Expected: all assertions pass and the output file is non-empty.

---

### Task 5: Render, Inspect, Correct, and Deliver

**Files:**
- Read: `formal_artifacts/system_visualization/体融识界·SportFusion_系统可视化完善版.docx`
- Create at runtime: `formal_artifacts/system_visualization/rendered/page-*.png`
- Create at runtime: `formal_artifacts/system_visualization/rendered/*.pdf`

**Interfaces:**
- Consumes: patched DOCX and the documents-skill renderer.
- Produces: a visually verified final DOCX and internal QA renders.

- [ ] **Step 1: Render the DOCX**

Run:

```powershell
& 'C:\Users\25113\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -X utf8 'C:\Users\25113\.codex\plugins\cache\openai-primary-runtime\documents\26.805.11740\skills\documents\render_docx.py' 'formal_artifacts\system_visualization\体融识界·SportFusion_系统可视化完善版.docx' --output_dir 'formal_artifacts\system_visualization\rendered' --emit_pdf
```

Expected: one or more `page-*.png` files and a non-empty PDF.

- [ ] **Step 2: Inspect every rendered page at 100 percent**

Check every page, with special attention to the five or more Figure 4-2 pages, for screenshot readability, distortion, caption separation, clipping, large blank gaps, broken tables, missing Chinese glyphs, headers, footers, and page numbers.

- [ ] **Step 3: Correct and re-render until clean**

Fix only the build script or inserted block, regenerate the DOCX, delete no source file, and re-render after every layout-sensitive change. Repeat until every page passes.

- [ ] **Step 4: Run final content and file checks**

Re-run structural assertions, open the final DOCX with python-docx, confirm the source DOCX timestamp and size are unchanged, confirm the final file exists and is non-empty, and compare the audit's accepted claims with the inserted paragraph and captions.

- [ ] **Step 5: Commit reproducibility files and report completion**

Stage only the plan, capture manifest, scripts, and audit text that are appropriate for source control; do not stage large raw screenshots, rendered PNGs, PDFs, or the final user DOCX unless repository policy already tracks formal artifacts. Run `git diff --cached --check`, commit with `docs: add SportFusion visualization report workflow`, and deliver only the final DOCX to the user.
