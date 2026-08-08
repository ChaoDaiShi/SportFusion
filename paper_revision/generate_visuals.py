from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib import patches
from matplotlib.font_manager import FontProperties
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "paper_revision" / "artifacts"
OUT = ROOT / "paper_revision" / "assets" / "figures"

PALETTE = {
    "primary": "#355C6B",
    "secondary": "#6F8F99",
    "accent": "#8FB7B0",
    "light": "#E6EEF1",
    "very_light": "#F3F7F8",
    "text": "#222222",
    "muted": "#66747A",
    "warning": "#B0885A",
}

FONT = FontProperties(family="Microsoft YaHei")
plt.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": ["Microsoft YaHei"],
        "axes.unicode_minus": False,
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "axes.edgecolor": "#D5DEE1",
        "axes.labelcolor": PALETTE["text"],
        "xtick.color": PALETTE["muted"],
        "ytick.color": PALETTE["muted"],
    }
)


def build_figure_specs(audit: dict) -> list[dict]:
    return [
        {"file": "01_研究论证闭环.png", "title": "研究问题、方法与验证闭环", "source_keys": ["design_spec", "data_audit.conflicts"]},
        {"file": "02_数据处理流程.png", "title": "数据治理与可追溯处理流程", "source_keys": ["raw_data_quality", "sources"]},
        {"file": "03_双通道识别框架.png", "title": "文本与行业代码双通道识别框架", "source_keys": ["backend.utils.industry_code", "backend.services.sport_recognition"]},
        {"file": "04_SportRatio测算流程.png", "title": "SportRatio 四维加权测算流程", "source_keys": ["backend.services.sport_recognition.feature_weights"]},
        {"file": "05_识别范围对比.png", "title": "传统行业代码法与融合识别法的识别范围对比", "source_keys": ["snapshot.traditional_sport_enterprises", "snapshot.fusion_sport_enterprises"]},
        {"file": "06_体育业务占比分布.png", "title": "全样本体育业务占比分布", "source_keys": ["ratio_distribution"]},
        {"file": "07_业态结构与跨界率.png", "title": "体育业态相对产出结构与跨界经营率", "source_keys": ["category_distribution"]},
        {"file": "08_区域相对产出指数.png", "title": "地级市体育业务相对产出指数前十位", "source_keys": ["city_top10", "snapshot.region_source_limitation"]},
        {"file": "09_系统技术架构.png", "title": "SportFusion 系统技术架构", "source_keys": ["backend", "frontend", "README"]},
        {"file": "10_证据分级与处理规则.png", "title": "数字证据分级与处理规则", "source_keys": ["conflicts", "sources"]},
    ]


def save(fig: plt.Figure, filename: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / filename, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def add_box(ax, x, y, w, h, text, fill, edge=None, fontsize=12, bold=False, text_color=None):
    edge = edge or PALETTE["primary"]
    box = patches.FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.015,rounding_size=0.025",
        linewidth=1.4,
        edgecolor=edge,
        facecolor=fill,
    )
    ax.add_patch(box)
    ax.text(
        x + w / 2,
        y + h / 2,
        text,
        ha="center",
        va="center",
        color=text_color or PALETTE["text"],
        fontsize=fontsize,
        fontproperties=FONT,
        fontweight="bold" if bold else "normal",
        linespacing=1.45,
    )
    return box


def arrow(ax, start, end, color=None, style="-|>"):
    ax.annotate(
        "",
        xy=end,
        xytext=start,
        arrowprops=dict(arrowstyle=style, color=color or PALETTE["secondary"], lw=1.6),
    )


def diagram_canvas(title: str):
    fig, ax = plt.subplots(figsize=(11, 6.2))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.text(0.5, 0.965, title, ha="center", va="top", fontsize=18, fontproperties=FONT, fontweight="bold", color=PALETTE["primary"])
    return fig, ax


def draw_research_loop():
    fig, ax = diagram_canvas("研究问题、方法与验证闭环")
    labels = [
        "问题提出\n行业代码无法完整反映\n多元经营企业的业务边界",
        "数据治理\n76,687条企业记录\n文本清洗与字段审计",
        "融合识别\n行业代码通道 +\n主要业务活动文本通道",
        "比重测算\n四维特征加权形成\nSportRatio相对指数",
        "实证输出\n业态结构、空间分布\n与跨界经营识别",
        "证据复核\n数据台账、口径一致性\n与适用边界说明",
    ]
    positions = [(0.07, 0.58), (0.36, 0.68), (0.67, 0.58), (0.67, 0.26), (0.36, 0.16), (0.07, 0.26)]
    fills = [PALETTE["light"], PALETTE["very_light"], "#E8F1EF", PALETTE["light"], PALETTE["very_light"], "#F3EEE8"]
    for (x, y), label, fill in zip(positions, labels, fills):
        add_box(ax, x, y, 0.25, 0.19, label, fill, fontsize=11)
    # Use a clockwise perimeter path so connectors never cut through box text.
    arrow(ax, (0.32, 0.675), (0.36, 0.775))
    arrow(ax, (0.61, 0.775), (0.67, 0.675))
    arrow(ax, (0.795, 0.58), (0.795, 0.45))
    arrow(ax, (0.67, 0.355), (0.61, 0.255))
    arrow(ax, (0.36, 0.255), (0.32, 0.355))
    arrow(ax, (0.195, 0.45), (0.195, 0.58))
    ax.text(0.5, 0.49, "可复现证据链", ha="center", va="center", fontsize=16, fontproperties=FONT, fontweight="bold", color=PALETTE["primary"])
    save(fig, "01_研究论证闭环.png")


def draw_data_flow(audit):
    fig, ax = diagram_canvas("数据治理与可追溯处理流程")
    xs = [0.03, 0.23, 0.43, 0.63, 0.82]
    labels = [
        "原始数据\nExcel 单表\n76,687条",
        "质量检查\n重复、缺失\n字段类型",
        "文本处理\n清洗、分词\n关键词匹配",
        "业务识别\n代码规则\n文本证据",
        "正式快照\n边界明细\n比重与聚合",
    ]
    for i, (x, label) in enumerate(zip(xs, labels)):
        add_box(ax, x, 0.58, 0.15, 0.21, label, PALETTE["light"] if i % 2 == 0 else PALETTE["very_light"], fontsize=11)
        if i < len(xs) - 1:
            arrow(ax, (x + 0.15, 0.685), (xs[i + 1], 0.685))
    checks = [
        f"重复记录：{audit['raw_data_quality']['duplicate_rows']}",
        f"业务活动缺失：{audit['raw_data_quality']['missing_business_activity']}",
        "文件哈希与批次时间",
        "冲突数字处理决定",
    ]
    for i, text in enumerate(checks):
        add_box(ax, 0.08 + i * 0.22, 0.25, 0.18, 0.12, text, "#F3EEE8", edge=PALETTE["warning"], fontsize=10)
        arrow(ax, (0.17 + i * 0.22, 0.37), (0.17 + i * 0.22, 0.55), color=PALETTE["warning"])
    ax.text(0.5, 0.11, "所有正文数字均绑定到 data_audit.json 的正式批次", ha="center", fontsize=12, fontproperties=FONT, color=PALETTE["muted"])
    save(fig, "02_数据处理流程.png")


def draw_dual_channel():
    fig, ax = diagram_canvas("文本与行业代码双通道识别框架")
    add_box(ax, 0.05, 0.42, 0.17, 0.20, "企业基础记录\n名称、行业代码\n主要业务活动", PALETTE["very_light"], fontsize=11)
    add_box(ax, 0.30, 0.63, 0.22, 0.17, "行业代码通道\n直接体育 / 间接相关 / 其他", PALETTE["light"], fontsize=11, bold=True)
    add_box(ax, 0.30, 0.25, 0.22, 0.17, "文本证据通道\n业务线切分、词典匹配\n业态归类", "#E8F1EF", fontsize=11, bold=True)
    add_box(ax, 0.62, 0.42, 0.19, 0.20, "规则融合\n代码强度 × 文本证据\n形成识别置信度", "#F3EEE8", fontsize=11)
    add_box(ax, 0.85, 0.42, 0.12, 0.20, "输出\n是否体育\n业态\n跨界类型", PALETTE["light"], fontsize=10)
    arrow(ax, (0.22, 0.52), (0.30, 0.715))
    arrow(ax, (0.22, 0.52), (0.30, 0.335))
    arrow(ax, (0.52, 0.715), (0.62, 0.56))
    arrow(ax, (0.52, 0.335), (0.62, 0.48))
    arrow(ax, (0.81, 0.52), (0.85, 0.52))
    ax.text(0.5, 0.12, "该框架是规则融合识别，不是已训练并通过人工金标准检验的监督分类器", ha="center", fontsize=11, fontproperties=FONT, color=PALETTE["warning"])
    save(fig, "03_双通道识别框架.png")


def draw_ratio_flow():
    fig, ax = diagram_canvas("SportRatio 四维加权测算流程")
    labels = [
        ("W1 业务范围", "体育业务线数 / 总业务线数", "40%"),
        ("W2 关键词密度", "体育关键词命中 / 文本词数", "25%"),
        ("W3 代码权重", "直接0.85 / 间接0.30 / 其他0", "25%"),
        ("W4 业态覆盖", "命中业态数 / 业态总数", "10%"),
    ]
    for i, (name, desc, weight) in enumerate(labels):
        x = 0.04 + i * 0.24
        add_box(ax, x, 0.57, 0.20, 0.22, f"{name}\n{desc}\n权重 {weight}", PALETTE["light"] if i % 2 == 0 else "#E8F1EF", fontsize=10)
        arrow(ax, (x + 0.10, 0.57), (0.50, 0.38))
    add_box(ax, 0.27, 0.19, 0.46, 0.17, "SportRatio = 0.40W1 + 0.25W2 + 0.25W3 + 0.10W4", "#F3EEE8", edge=PALETTE["warning"], fontsize=13, bold=True)
    ax.text(0.5, 0.10, "输出为0—1之间的相对业务比重代理值；权重不是企业财务报表中的收入占比", ha="center", fontsize=11, fontproperties=FONT, color=PALETTE["muted"])
    save(fig, "04_SportRatio测算流程.png")


def draw_coverage(audit):
    snapshot = audit["snapshot"]
    labels = ["传统直接行业代码法", "文本—代码融合识别"]
    values = [snapshot["traditional_sport_enterprises"], snapshot["fusion_sport_enterprises"]]
    fig, ax = plt.subplots(figsize=(10, 5.8))
    bars = ax.barh(labels, values, color=[PALETTE["secondary"], PALETTE["primary"]], height=0.46)
    ax.set_title("传统行业代码法与融合识别法的识别范围对比", fontproperties=FONT, fontsize=18, fontweight="bold", color=PALETTE["primary"], pad=16)
    ax.set_xlabel("识别为体育相关的企业数量（家）", fontproperties=FONT, fontsize=11)
    ax.set_xlim(0, max(values) * 1.17)
    ax.grid(axis="x", color="#E3E8EA", linewidth=0.8)
    ax.spines[["top", "right", "left"]].set_visible(False)
    for bar, value in zip(bars, values):
        ax.text(value + 90, bar.get_y() + bar.get_height() / 2, f"{value:,} 家", va="center", fontsize=12, fontproperties=FONT, color=PALETTE["text"], fontweight="bold")
    delta = snapshot["incremental_enterprises"]
    relative = snapshot["relative_identification_increase_pct"]
    ax.text(0.98, 0.06, f"增量识别 {delta:,} 家\n相对传统识别数量增加 {relative:.2f}%", transform=ax.transAxes, ha="right", va="bottom", fontsize=12, fontproperties=FONT, color=PALETTE["primary"], bbox=dict(boxstyle="round,pad=0.5", facecolor=PALETTE["very_light"], edgecolor=PALETTE["secondary"]))
    fig.tight_layout()
    save(fig, "05_识别范围对比.png")


def draw_ratio_distribution(audit):
    distribution = audit["ratio_distribution"]
    labels = ["0", "(0, 0.2]", "(0.2, 0.5]", "(0.5, 0.8]", "(0.8, 1.0]"]
    keys = ["0", "0-0.2", "0.2-0.5", "0.5-0.8", "0.8-1.0"]
    values = [distribution[key] for key in keys]
    fig, ax = plt.subplots(figsize=(10, 5.8))
    bars = ax.bar(labels, values, color=[PALETTE["secondary"], PALETTE["light"], PALETTE["accent"], PALETTE["warning"], PALETTE["primary"]], width=0.68)
    ax.set_title("全样本体育业务占比分布", fontproperties=FONT, fontsize=18, fontweight="bold", color=PALETTE["primary"], pad=16)
    ax.set_xlabel("SportRatio 区间", fontproperties=FONT)
    ax.set_ylabel("企业数量（家）", fontproperties=FONT)
    ax.grid(axis="y", color="#E3E8EA", linewidth=0.8)
    ax.spines[["top", "right"]].set_visible(False)
    for bar, value in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, value + max(values) * 0.015, f"{value:,}", ha="center", fontsize=10, fontproperties=FONT, color=PALETTE["text"])
    ax.text(0.99, 0.96, "注：该分布覆盖全部76,687家企业，非体育企业及低比重企业均保留。", transform=ax.transAxes, ha="right", va="top", fontsize=10, fontproperties=FONT, color=PALETTE["muted"])
    fig.tight_layout()
    save(fig, "06_体育业务占比分布.png")


def draw_categories(audit):
    records = sorted(audit["category_distribution"], key=lambda item: item["output_index"])
    names = [item["category"] for item in records]
    outputs = [item["output_index"] for item in records]
    crossover = [item["crossover_pct"] for item in records]
    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(12, 7), sharey=True, gridspec_kw={"width_ratios": [2.4, 1]})
    bars = ax.barh(names, outputs, color=PALETTE["primary"], alpha=0.9, height=0.55)
    ax.set_xlabel("相对产出指数", fontproperties=FONT)
    fig.suptitle("体育业态相对产出结构与跨界经营率", fontproperties=FONT, fontsize=18, fontweight="bold", color=PALETTE["primary"], y=0.98)
    ax.grid(axis="x", color="#E3E8EA", linewidth=0.8)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax2.hlines(names, 0, crossover, color=PALETTE["light"], linewidth=3)
    ax2.scatter(crossover, names, color=PALETTE["warning"], s=70, zorder=3)
    ax2.set_xlim(0, 110)
    ax2.set_xlabel("跨界经营率（%）", fontproperties=FONT, color=PALETTE["warning"])
    ax2.tick_params(axis="x", colors=PALETTE["warning"])
    ax2.tick_params(axis="y", left=False, labelleft=False)
    ax2.grid(axis="x", color="#E3E8EA", linewidth=0.8)
    ax2.spines[["top", "right", "left"]].set_visible(False)
    for bar, value in zip(bars, outputs):
        ax.text(value + max(outputs) * 0.012, bar.get_y() + bar.get_height() / 2, f"{value:,.0f}", va="center", fontsize=9, fontproperties=FONT)
    for rate, name in zip(crossover, names):
        ax2.text(min(rate + 3, 104), name, f"{rate:.0f}%", va="center", fontsize=9, fontproperties=FONT, color=PALETTE["warning"])
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    save(fig, "07_业态结构与跨界率.png")


def draw_regions(audit):
    records = list(reversed(audit["city_top10"]))
    names = [item["区域"] for item in records]
    values = [item["产出指数"] for item in records]
    fig, ax = plt.subplots(figsize=(10.5, 6.5))
    bars = ax.barh(names, values, color=[PALETTE["secondary"]] * 9 + [PALETTE["primary"]], height=0.56)
    ax.set_title("地级市体育业务相对产出指数前十位", fontproperties=FONT, fontsize=18, fontweight="bold", color=PALETTE["primary"], pad=16)
    ax.set_xlabel("相对产出指数（非货币单位）", fontproperties=FONT)
    ax.grid(axis="x", color="#E3E8EA", linewidth=0.8)
    ax.spines[["top", "right", "left"]].set_visible(False)
    for bar, value in zip(bars, values):
        ax.text(value + max(values) * 0.012, bar.get_y() + bar.get_height() / 2, f"{value:,.0f}", va="center", fontsize=9, fontproperties=FONT)
    ax.text(0.99, 0.03, "区域由企业名称字符串抽取；四川省本级未列入地级市排名。", transform=ax.transAxes, ha="right", fontsize=10, fontproperties=FONT, color=PALETTE["warning"])
    fig.tight_layout()
    save(fig, "08_区域相对产出指数.png")


def draw_system_architecture():
    fig, ax = diagram_canvas("SportFusion 系统技术架构")
    layers = [
        (0.08, 0.70, "交互层", "Vue 3 / Element Plus\n监测驾驶舱、风险中心、企业识别、报表导出", PALETTE["light"]),
        (0.08, 0.50, "接口层", "FastAPI 路由\n数据预处理、识别、测算、图表、监测、问答", "#E8F1EF"),
        (0.08, 0.30, "服务层", "NLP预处理 / 规则融合识别 / 产出指数聚合\n行业分析、风险快照与证据引用", PALETTE["very_light"]),
        (0.08, 0.10, "数据层", "原始Excel、处理后CSV/JSON、SQLite\n正式批次与数据来源标识", "#F3EEE8"),
    ]
    for x, y, label, desc, fill in layers:
        add_box(ax, x, y, 0.14, 0.13, label, PALETTE["primary"], edge=PALETTE["primary"], fontsize=12, bold=True, text_color="white")
        add_box(ax, x + 0.18, y, 0.68, 0.13, desc, fill, fontsize=11)
    for y in [0.70, 0.50, 0.30]:
        arrow(ax, (0.5, y), (0.5, y - 0.07))
        arrow(ax, (0.56, y - 0.07), (0.56, y), style="<|-")
    save(fig, "09_系统技术架构.png")


def draw_evidence_rules():
    fig, ax = diagram_canvas("数字证据分级与处理规则")
    levels = [
        ("A级", "原始数据可直接复算", "保留并标注口径", 0.73, PALETTE["primary"]),
        ("B级", "处理后明细或代码输出可交叉验证", "保留并绑定批次", 0.55, PALETTE["secondary"]),
        ("C级", "政府、标准或原始论文可核验", "规范引用后保留", 0.37, PALETTE["accent"]),
        ("D级", "来源不明、批次冲突或无法复算", "删除、重算或降格", 0.19, PALETTE["warning"]),
    ]
    widths = [0.42, 0.54, 0.66, 0.78]
    for (level, source, action, y, color), width in zip(levels, widths):
        x = 0.5 - width / 2
        add_box(ax, x, y, width, 0.13, f"{level}  {source}  →  {action}", color, edge=color, fontsize=11, bold=True, text_color="white")
    ax.text(0.5, 0.08, "D级示例：AUC=0.91、Kappa=0.86、2028年预测值、经济效益金额", ha="center", fontsize=10.5, fontproperties=FONT, color=PALETTE["warning"])
    save(fig, "10_证据分级与处理规则.png")


def main() -> None:
    audit = json.loads((ARTIFACTS / "data_audit.json").read_text(encoding="utf-8"))
    draw_research_loop()
    draw_data_flow(audit)
    draw_dual_channel()
    draw_ratio_flow()
    draw_coverage(audit)
    draw_ratio_distribution(audit)
    draw_categories(audit)
    draw_regions(audit)
    draw_system_architecture()
    draw_evidence_rules()

    specs = build_figure_specs(audit)
    manifest = []
    for spec in specs:
        path = OUT / spec["file"]
        with Image.open(path) as image:
            width, height = image.size
            dpi = image.info.get("dpi", (300, 300))
        manifest.append(
            {
                **spec,
                "path": str(path.resolve()),
                "generated_at": datetime.now().astimezone().isoformat(),
                "width_px": width,
                "height_px": height,
                "dpi": [round(float(dpi[0]), 1), round(float(dpi[1]), 1)],
            }
        )
    (ARTIFACTS / "figure_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"figures": len(manifest), "min_width": min(item["width_px"] for item in manifest)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
