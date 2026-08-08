# SportFusion 国赛级论文优化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在不覆盖原稿的前提下，生成一份数据可追溯、统计口径一致、图表与系统材料真实、中文学术格式规范的 SportFusion 国赛优化版 DOCX。

**Architecture:** 工作流分为“证据审计—数字台账—图形与截图—文档重构—渲染验收”五层。所有正文数字和图表先绑定到审计后的单一结果快照，再由文档构建脚本统一生成；无法复现的原稿结果在进入构建层前即被标记为删除或降格表述。

**Tech Stack:** bundled Python 3、python-docx、pandas/openpyxl、matplotlib/seaborn、OOXML、bundled Node.js、Playwright、Vue 3/FastAPI、LibreOffice 渲染工具。

## Global Constraints

- 原稿 `F:\比赛\大数据要素分析\体融识界·SportFusion——基于NLP文本识别与多维度加权的多元经营企业体育业务边界识别与产业规模测算.docx` 只读保留。
- 中文正文使用宋体小四；英文、数字和西文符号使用 Times New Roman 小四；正文 1.5 倍行距、两端对齐、首行缩进 2 字符。
- 表格采用无竖线三线表；表头可用浅蓝灰 `#E6EEF1`，主强调色为深蓝灰 `#355C6B`，不得使用高饱和大面积填色。
- 任何无法从原始数据、处理后明细、代码输出、实验记录或权威来源复核的数字不得作为确定性结论。
- “识别覆盖率提升”“准确率”“精确率”“召回率”“F1”“AUC”必须按各自定义使用，不得互换。
- 图表和系统截图只使用最终审计快照和真实运行界面。
- 工作区当前不是 Git 仓库，因此以输出清单、SHA-256 哈希和阶段性审计报告代替提交记录。

---

## File Map

- Create `paper_revision/audit_core.py`: 定义统一指标计算、批次识别和证据等级规则。
- Create `paper_revision/run_data_audit.py`: 读取原始 Excel、处理后 CSV/JSON 与项目代码输出，生成正式审计快照。
- Create `paper_revision/extract_docx_claims.py`: 提取原稿段落、表格、题注、数值和疑似预测/效益主张。
- Create `paper_revision/generate_visuals.py`: 从正式审计快照生成论文图表和架构/流程图。
- Create `paper_revision/capture_system.mjs`: 启动后对真实系统代表性页面进行一致尺寸截图。
- Create `paper_revision/build_competition_docx.py`: 以原稿为内容基础，完成数据纠错、章节重构、字体表格规范、图形与截图替换。
- Create `paper_revision/verify_docx.py`: 对最终 DOCX 执行结构、字体、表格、编号、图片和数字一致性审计。
- Create `paper_revision/tests/test_audit_core.py`: 测试核心指标定义和分母口径。
- Create `paper_revision/tests/test_docx_rules.py`: 测试三线表、字体和编号规则。
- Create `paper_revision/artifacts/`: 保存审计报告、正式快照、数字台账和最终验证结果。
- Create `paper_revision/assets/figures/`: 保存最终论文图表。
- Create `paper_revision/assets/system/`: 保存真实系统截图。
- Create `paper_revision/rendered/`: 保存逐页渲染 QA 图片，不作为最终交付物。
- Create `体融识界·SportFusion——国赛优化版.docx`: 最终交付文件。

---

### Task 1: 建立可复现的数据审计核心

**Files:**
- Create: `paper_revision/audit_core.py`
- Create: `paper_revision/tests/test_audit_core.py`
- Create: `paper_revision/run_data_audit.py`
- Create: `paper_revision/artifacts/data_audit.json`
- Create: `paper_revision/artifacts/data_audit.md`

**Interfaces:**
- Consumes: `submission/原始数据/企业原始数据.xlsx`、`data/processed/*.csv`、`data/processed/*.json`、`backend/scripts/*.py`。
- Produces: `compute_snapshot(frame, boundary_frame) -> dict`；`classify_evidence(source_kind, reproducible, conflict) -> str`；版本化的 `data_audit.json`。

- [ ] **Step 1: 写入核心口径测试**

```python
def test_snapshot_distinguishes_coverage_from_accuracy():
    snapshot = compute_snapshot_from_counts(total=100, traditional=10, fusion=12, crossover=3)
    assert snapshot["traditional_coverage_pct"] == 10.0
    assert snapshot["fusion_coverage_pct"] == 12.0
    assert snapshot["relative_identification_increase_pct"] == 20.0
    assert "accuracy" not in snapshot

def test_conflicting_unreproducible_claim_is_grade_d():
    assert classify_evidence("legacy_docx", reproducible=False, conflict=True) == "D"
```

- [ ] **Step 2: 运行测试并确认初始失败**

Run: `& 'C:\Users\25113\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m pytest paper_revision/tests/test_audit_core.py -v`

Expected: FAIL，提示 `audit_core` 或被测函数尚不存在。

- [ ] **Step 3: 实现指标与证据等级函数**

```python
def pct(numerator: int | float, denominator: int | float) -> float:
    return round(numerator / denominator * 100, 2) if denominator else 0.0

def compute_snapshot_from_counts(total: int, traditional: int, fusion: int, crossover: int) -> dict:
    return {
        "total_enterprises": total,
        "traditional_sport_enterprises": traditional,
        "fusion_sport_enterprises": fusion,
        "crossover_enterprises": crossover,
        "traditional_coverage_pct": pct(traditional, total),
        "fusion_coverage_pct": pct(fusion, total),
        "incremental_enterprises": fusion - traditional,
        "relative_identification_increase_pct": pct(fusion - traditional, traditional),
    }

def classify_evidence(source_kind: str, reproducible: bool, conflict: bool) -> str:
    if conflict or not reproducible:
        return "D"
    return {"raw_data": "A", "derived_output": "B", "authority": "C"}.get(source_kind, "D")
```

- [ ] **Step 4: 读取真实数据并生成批次审计报告**

`run_data_audit.py` 必须记录每个输入文件的绝对路径、修改时间、SHA-256、行数、字段名和编码；重新计算企业总数、传统代码识别数、融合识别数、跨界企业数、各业态数量、业务比重分布、区域聚合、CR3、CR5、HHI 和基尼系数，并把不同历史批次并列写入冲突清单。

Run: `& 'C:\Users\25113\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' paper_revision/run_data_audit.py`

Expected: 生成 `data_audit.json` 和 `data_audit.md`，报告明确指出正式批次及每项冲突的处理结论。

- [ ] **Step 5: 复跑测试与审计脚本**

Run: `& 'C:\Users\25113\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m pytest paper_revision/tests/test_audit_core.py -v`

Expected: PASS，且审计 JSON 中不含 NaN、Infinity 或空分母结果。

---

### Task 2: 建立原稿数字台账和证据映射

**Files:**
- Create: `paper_revision/extract_docx_claims.py`
- Create: `paper_revision/artifacts/docx_claims.csv`
- Create: `paper_revision/artifacts/claim_decisions.csv`
- Create: `paper_revision/artifacts/structure_audit.md`

**Interfaces:**
- Consumes: 原稿 DOCX、Task 1 的 `data_audit.json`。
- Produces: 每项主张的 `location, claim_text, numeric_tokens, evidence_grade, decision, replacement`。

- [ ] **Step 1: 提取全部段落、表格和题注中的数字主张**

使用 `python-docx` 遍历 716 个正文段落和 23 个表格，正则提取百分数、整数、小数、年份、样本量及统计指标名称；同时识别“预测、预计、节省、提高效率、AUC、Kappa、Pearson、准确率、召回率、F1、CR3、CR5、HHI、基尼”等高风险上下文。

- [ ] **Step 2: 输出结构错误清单**

审计至少覆盖重复标题 `4.1.1`、第六章误标为 `图5-2`、图表重号、题注非 Caption 样式、表题位置、参考文献引用对应关系和目录字段状态。

- [ ] **Step 3: 按证据等级给出处理决定**

每条主张只能取以下决定之一：`keep`、`recalculate`、`rewrite_as_scope`、`remove`。A/B/C 级可保留，D 级必须为后三种之一；`replacement` 列必须给出正文替代表述，不允许空白。

- [ ] **Step 4: 运行提取器并人工抽查高风险结果**

Run: `& 'C:\Users\25113\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' paper_revision/extract_docx_claims.py`

Expected: `claim_decisions.csv` 覆盖原稿所有含数值段落和表格行，D 级主张没有 `keep` 决定。

---

### Task 3: 核验外部事实与参考文献

**Files:**
- Create: `paper_revision/artifacts/reference_audit.md`
- Create: `paper_revision/artifacts/verified_references.json`

**Interfaces:**
- Consumes: 原稿参考文献和正文外部事实主张。
- Produces: 可访问链接、标准号、出版信息、支持的正文主张和处理决定。

- [ ] **Step 1: 提取参考文献及正文引用**

按序号建立引用映射，记录无正文引用的文献、正文出现但参考文献缺失的来源以及题名/作者/年份不完整项。

- [ ] **Step 2: 仅用权威或原始来源核验**

国家标准使用全国标准信息公共服务平台或正式标准文本；政策、产业规模和统计制度使用国家统计局、国家体育总局及政府公报；算法定义使用原始论文或官方文档。

- [ ] **Step 3: 删除无法核实的外部事实**

`verified_references.json` 中每条记录包含 `claim_id, source_type, title, publisher, year, url_or_doi, verified, action`，未核实记录的 `action` 必须为 `remove` 或 `rewrite_without_claim`。

---

### Task 4: 生成统一视觉体系和真实结果图表

**Files:**
- Create: `paper_revision/generate_visuals.py`
- Create: `paper_revision/assets/figures/*.png`
- Create: `paper_revision/artifacts/figure_manifest.json`

**Interfaces:**
- Consumes: `data_audit.json`、正式明细 CSV、`claim_decisions.csv`。
- Produces: 300 DPI 论文图表和带源指标键的图形清单。

- [ ] **Step 1: 固定视觉 token**

```python
PALETTE = {
    "primary": "#355C6B",
    "secondary": "#6F8F99",
    "accent": "#8FB7B0",
    "light": "#E6EEF1",
    "very_light": "#F3F7F8",
    "text": "#222222",
}
```

- [ ] **Step 2: 从正式快照生成结果图**

生成覆盖范围对比、业态结构、跨界率、业务比重分布、区域 TOP10 和空间集中度图。只有当 Task 1 找到真实验证记录时，才生成 ROC、混淆矩阵、Kappa 或敏感性图；否则以“验证证据不足”文字框替代，不能模拟曲线。

- [ ] **Step 3: 绘制流程与架构图**

生成研究闭环、数据处理流、双通道模型、SportRatio 计算、验证流程、系统架构和应用闭环图。架构图组件必须对应 `backend` 路由/服务和 `frontend` 实际页面，不加入不存在的模型服务或数据库。

- [ ] **Step 4: 写出图形清单并验证**

`figure_manifest.json` 为每幅图记录 `file, title, source_keys, generated_at, dpi, width_px, height_px`。

Run: `& 'C:\Users\25113\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' paper_revision/generate_visuals.py`

Expected: 所有图片宽度至少 1800 px，图中数字与 `data_audit.json` 一致。

---

### Task 5: 采集真实系统原型截图

**Files:**
- Create: `paper_revision/capture_system.mjs`
- Create: `paper_revision/assets/system/*.png`
- Create: `paper_revision/artifacts/system_capture_manifest.json`

**Interfaces:**
- Consumes: `backend/main.py`、`frontend` 应用、实际 API 响应。
- Produces: 1600×1000 的代表性页面截图和页面/数据模式清单。

- [ ] **Step 1: 运行现有测试并启动系统**

Run backend: `& 'F:\比赛\大数据要素分析\backend\.venv\Scripts\python.exe' -m pytest backend/tests -v`

Run frontend: `& 'C:\Users\25113\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe' --test frontend/tests/*.test.js`

Expected: 测试通过；若失败，先按系统化调试流程修复或记录与论文截图无关的阻塞。

- [ ] **Step 2: 启动后端和前端开发服务器**

Run: `Start-Process -WindowStyle Hidden -FilePath 'F:\比赛\大数据要素分析\backend\.venv\Scripts\python.exe' -ArgumentList '-m','uvicorn','main:app','--host','127.0.0.1','--port','8000' -WorkingDirectory 'F:\比赛\大数据要素分析\backend'`

Run: `Start-Process -WindowStyle Hidden -FilePath 'C:\Users\25113\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe' -ArgumentList 'node_modules/vite/bin/vite.js','--host','127.0.0.1','--port','5173' -WorkingDirectory 'F:\比赛\大数据要素分析\frontend'`

Expected: `/api/health` 或根 API 可访问，前端页面返回 HTTP 200。

- [ ] **Step 3: 截取真实页面**

使用 Playwright 依次访问 `/monitoring`、`/risks`、`/model-evaluation`、`/recognition` 或现有等价路由、`/report-export`，等待网络空闲并隐藏开发提示；每张截图必须记录 URL、标题、数据模式和截图时间。

- [ ] **Step 4: 检查截图内容**

删除加载失败、空白、演示数据未标识或数值与正式快照冲突的截图。若页面使用历史快照，图注必须明确“系统历史快照展示”，不得与论文正式批次混称。

---

### Task 6: 重构并生成国赛优化版 DOCX

**Files:**
- Create: `paper_revision/build_competition_docx.py`
- Create: `体融识界·SportFusion——国赛优化版.docx`

**Interfaces:**
- Consumes: 原稿、正式审计快照、数字台账、已核验参考文献、最终图表和系统截图。
- Produces: 格式统一、数据一致、图文并茂的最终 DOCX。

- [ ] **Step 1: 固定页面、样式和字体规则**

构建脚本对 Normal、Title、Heading 1—3、Caption、表格正文和注释样式显式设置字体、字号、间距、缩进和中英文字体；通过 OOXML 同时设置 `w:eastAsia="宋体"` 和 `w:ascii/w:hAnsi="Times New Roman"`。

- [ ] **Step 2: 应用数据台账决定**

对所有 `recalculate` 主张使用 Task 1 正式快照替换；对 `rewrite_as_scope` 主张改写为证据边界说明；删除 `remove` 主张及依赖它们的图表。摘要、正文、表格、图题和结论必须引用同一指标键。

- [ ] **Step 3: 修复章节和编号**

采用章—节—条三级编号，修正 `4.1.1` 重复、图号跨章错误、图表重号和附录编号；使用 Word 标题样式、题注样式和可更新目录字段，不用手工空格模拟层级。

- [ ] **Step 4: 规范所有表格为美观三线表**

对每个表设置无竖线、顶线 1.5 pt、表头下线 0.75 pt、底线 1.5 pt；表头填充 `#E6EEF1`，表头文字 `#355C6B`，仅对确有比较意义的重点行使用 `#F3F7F8`；单元格垂直居中并设置一致内边距，不固定行高。

- [ ] **Step 5: 插入真实图形和系统截图**

每幅图前加入分析目的，图后加入结论与局限；图片与题注尽量同页，截图图注标明页面功能和数据模式。删除低清、重复或与正文无直接关系的原图。

- [ ] **Step 6: 完成书面化重写**

每段围绕一个判断展开，区分事实、解释、推断和建议；删除“巨大价值、精准识别、显著提升”等无证据措辞。创新点压缩为 3—4 项，每项包含方法缺口、具体做法、技术支撑和真实验证。

- [ ] **Step 7: 保存为新文件并保留原稿**

Run: `& 'C:\Users\25113\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' paper_revision/build_competition_docx.py`

Expected: 生成 `体融识界·SportFusion——国赛优化版.docx`，原稿修改时间和 SHA-256 均未变化。

---

### Task 7: 执行结构、数据和格式自动验证

**Files:**
- Create: `paper_revision/verify_docx.py`
- Create: `paper_revision/tests/test_docx_rules.py`
- Create: `paper_revision/artifacts/final_verification.json`
- Create: `paper_revision/artifacts/final_verification.md`

**Interfaces:**
- Consumes: 最终 DOCX、`data_audit.json`、`claim_decisions.csv`、图形清单。
- Produces: 机器可读和人工可读验证报告。

- [ ] **Step 1: 写入格式与编号测试**

```python
def test_no_duplicate_numbered_headings(report):
    assert report["duplicate_headings"] == []

def test_tables_have_no_vertical_borders(report):
    assert report["tables_with_vertical_borders"] == []

def test_unsupported_numeric_claims_absent(report):
    assert report["unsupported_claims"] == []
```

- [ ] **Step 2: 实现文档验证器**

检查标题、图题、表题、字体、字号、表格边框/填色、目录字段、页眉页脚、图片分辨率、交叉引用、参考文献映射和正文数字。验证器必须把原稿 D 级数字与最终文档逐一比对，确保没有误保留。

- [ ] **Step 3: 运行自动验证**

Run: `& 'C:\Users\25113\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' paper_revision/verify_docx.py`

Expected: `unsupported_claims`、`duplicate_headings`、`duplicate_captions`、`tables_with_vertical_borders` 均为空。

---

### Task 8: 渲染、逐页检查和最终交付

**Files:**
- Create: `paper_revision/rendered/page-*.png`
- Modify: `体融识界·SportFusion——国赛优化版.docx`（仅修复渲染发现的问题）

**Interfaces:**
- Consumes: 自动验证通过的最终 DOCX。
- Produces: 逐页 QA 图像和最终交付文件。

- [ ] **Step 1: 渲染 DOCX**

Run: `& 'C:\Users\25113\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' 'C:\Users\25113\.codex\plugins\cache\openai-primary-runtime\documents\26.731.11130\skills\documents\render_docx.py' 'F:\比赛\大数据要素分析\体融识界·SportFusion——国赛优化版.docx' --output_dir 'F:\比赛\大数据要素分析\paper_revision\rendered' --emit_pdf`

Expected: 生成连续编号的逐页 PNG，转换日志无字体缺失或页面失败。

- [ ] **Step 2: 逐页视觉检查**

检查封面、目录、标题层级、图表清晰度、题注位置、三线表跨页、孤行、空白页、文字溢出、图片拉伸、页眉页脚和参考文献换页。发现问题后只修改构建脚本，不直接手工改最终 DOCX。

- [ ] **Step 3: 重建、重验和重渲染**

重复 Task 6—8，直至自动验证全部通过且逐页 PNG 无明显版式缺陷。

- [ ] **Step 4: 生成最终哈希和交付清单**

Run: `Get-FileHash 'F:\比赛\大数据要素分析\体融识界·SportFusion——国赛优化版.docx' -Algorithm SHA256`

Expected: 记录最终文件大小、页数、SHA-256；只向用户交付优化版 DOCX，不交付内部 QA 图片。

