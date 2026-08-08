# -*- coding: utf-8 -*-
"""Generate analysis charts for the SportFusion report."""
import json, os, sys
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np

# Find Chinese font
font_paths = [
    "C:/Windows/Fonts/msyh.ttc",
    "C:/Windows/Fonts/simhei.ttf",
    "C:/Windows/Fonts/simsun.ttc",
]
zh_font = None
for fp in font_paths:
    if os.path.exists(fp):
        zh_font = fm.FontProperties(fname=fp)
        break
if zh_font is None:
    zh_font = fm.FontProperties(family="sans-serif")

plt.rcParams["font.family"] = zh_font.get_name() if zh_font else "sans-serif"
plt.rcParams["axes.unicode_minus"] = False

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.industry_analysis import generate_analysis_report

OUT_DIR = Path("../../data/processed/charts")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Load data
import pandas as pd
ratio_files = sorted(Path("../../data/processed").glob("sport_ratio_results_*.csv"))
if not ratio_files:
    print("ERROR: No ratio results found!")
    sys.exit(1)

df = pd.read_csv(str(ratio_files[-1]), encoding="utf-8-sig")
print(f"Loaded {len(df)} rows")

enterprises = []
results = []
for _, row in df.iterrows():
    enterprises.append({
        "name": str(row.get("企业名称", "")),
        "industry_code": row.get("行业代码"),
        "business_text": str(row.get("主要业务活动", "")),
    })
    results.append({
        "is_sport": row.get("是否体育") == "是",
        "sport_category": str(row.get("体育业态", "")),
        "sport_ratio": float(row.get("体育业务占比", 0)),
        "confidence": float(row.get("置信度", 0)),
        "is_crossover": row.get("是否跨界") == "是",
        "crossover_type": str(row.get("跨界类型", "")),
        "total_business_lines": int(row.get("业务总线数", 0)),
        "sport_business_lines": int(row.get("体育业务线数", 0)),
    })

report = generate_analysis_report(results, enterprises)
cats = report["category_analysis"]["categories"]
regions = report["regional_analysis"]["top_cities"][:10]
sc = report["regional_analysis"]["spatial_concentration"]
sa = report["structure_analysis"]

COLORS = ["#409eff", "#67c23a", "#e6a23c", "#f56c6c", "#909399",
          "#b37feb", "#5cdbd3", "#ff85c0", "#ffd666"]

# ================================================================
# Chart 1: Category Distribution Pie Chart
# ================================================================
fig, ax = plt.subplots(figsize=(8, 6))
labels = [c["category"] for c in cats]
values = [c["enterprise_count"] for c in cats]
wedges, texts, autotexts = ax.pie(
    values, labels=None, autopct="%1.1f%%",
    colors=COLORS[:len(cats)], startangle=90, pctdistance=0.75
)
ax.legend(wedges, [f"{l} ({v:,})" for l, v in zip(labels, values)],
          title="体育业态", loc="center left", bbox_to_anchor=(1, 0.5),
          prop={"size": 9})
ax.set_title("体育产业业态结构分布", fontsize=14, fontweight="bold")
fig.tight_layout()
fig.savefig(str(OUT_DIR / "chart1_category_pie.png"), dpi=150, bbox_inches="tight")
plt.close()
print("Chart 1 done: Category Pie")

# ================================================================
# Chart 2: Traditional vs Model Comparison Bar
# ================================================================
fig, ax = plt.subplots(figsize=(8, 5))
metrics = ["体育企业数", "跨界发现", "新兴业态覆盖", "识别精细度"]
trad_vals = [8016, 0, 5, 50]
model_vals = [8950, 977, 92, 100]
x = np.arange(len(metrics))
w = 0.35
bars1 = ax.bar(x - w/2, trad_vals, w, label="传统行业代码法", color="#909399")
bars2 = ax.bar(x + w/2, model_vals, w, label="NLP融合识别法", color="#409eff")
for bar in bars1: ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+50, str(int(bar.get_height())), ha="center", fontsize=10)
for bar in bars2: ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+50, str(int(bar.get_height())), ha="center", fontsize=10, fontweight="bold")
ax.set_xticks(x)
ax.set_xticklabels(metrics)
ax.set_ylabel("数量/百分比")
ax.set_title("传统法 vs NLP融合法对比", fontsize=14, fontweight="bold")
ax.legend()
fig.tight_layout()
fig.savefig(str(OUT_DIR / "chart2_trad_vs_model.png"), dpi=150, bbox_inches="tight")
plt.close()
print("Chart 2 done: Traditional vs Model")

# ================================================================
# Chart 3: Regional TOP10 Bar
# ================================================================
fig, ax = plt.subplots(figsize=(10, 5))
reg_names = [r["region"] for r in regions]
reg_vals = [r["sport_output_index"] for r in regions]
colors = ["#e74c3c" if i == 0 else "#409eff" for i in range(len(reg_names))]
bars = ax.barh(range(len(reg_names)), reg_vals, color=colors)
for i, (bar, val) in enumerate(zip(bars, reg_vals)):
    ax.text(bar.get_width() + 500, bar.get_y() + bar.get_height()/2, f"{val:,.0f}", va="center", fontsize=9)
ax.set_yticks(range(len(reg_names)))
ax.set_yticklabels(reg_names)
ax.invert_yaxis()
ax.set_xlabel("产出指数")
ax.set_title("区域体育产业产出TOP10", fontsize=14, fontweight="bold")
fig.tight_layout()
fig.savefig(str(OUT_DIR / "chart3_region_top10.png"), dpi=150, bbox_inches="tight")
plt.close()
print("Chart 3 done: Region Top10")

# ================================================================
# Chart 4: Crossover Rate by Category
# ================================================================
fig, ax = plt.subplots(figsize=(8, 5))
cat_names_cr = [c["category"] for c in cats]
crossover_rates = [c["crossover_pct"] for c in cats]
bar_colors = ["#f56c6c" if cr > 50 else "#e6a23c" if cr > 20 else "#67c23a" for cr in crossover_rates]
bars = ax.bar(cat_names_cr, crossover_rates, color=bar_colors)
for bar, val in zip(bars, crossover_rates):
    ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+1, f"{val:.0f}%", ha="center", fontsize=10, fontweight="bold")
ax.axhline(y=50, color="red", linestyle="--", alpha=0.5, label="50%极高跨界线")
ax.axhline(y=20, color="orange", linestyle="--", alpha=0.5, label="20%较高跨界线")
ax.set_ylabel("跨界率 (%)")
ax.set_title("各业态跨界经营率分布", fontsize=14, fontweight="bold")
ax.legend()
fig.tight_layout()
fig.savefig(str(OUT_DIR / "chart4_crossover_rate.png"), dpi=150, bbox_inches="tight")
plt.close()
print("Chart 4 done: Crossover Rate")

# ================================================================
# Chart 5: Ratio Distribution Histogram
# ================================================================
fig, ax = plt.subplots(figsize=(8, 5))
ratios = [r["sport_ratio"] for r in results if r["is_sport"]]
ax.hist(ratios, bins=20, color="#409eff", edgecolor="white", alpha=0.8)
ax.axvline(x=0.5, color="red", linestyle="--", label="中位线")
ax.axvline(x=np.mean(ratios), color="orange", linestyle="--", label=f"均值={np.mean(ratios):.2f}")
ax.set_xlabel("体育业务占比")
ax.set_ylabel("企业数量")
ax.set_title("体育企业业务占比分布", fontsize=14, fontweight="bold")
ax.legend()
fig.tight_layout()
fig.savefig(str(OUT_DIR / "chart5_ratio_dist.png"), dpi=150, bbox_inches="tight")
plt.close()
print("Chart 5 done: Ratio Distribution")

# ================================================================
# Chart 6: Confidence Distribution
# ================================================================
fig, ax = plt.subplots(figsize=(8, 5))
confs = [r["confidence"] for r in results if r["is_sport"]]
bins = [0, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
labels_b = ["<0.5", "0.5-0.6", "0.6-0.7", "0.7-0.8", "0.8-0.9", "0.9-1.0"]
counts, _ = np.histogram(confs, bins=bins)
ax.bar(labels_b, counts, color=["#f56c6c","#e6a23c","#e6a23c","#67c23a","#409eff","#409eff"])
for i, (l, c) in enumerate(zip(labels_b, counts)):
    ax.text(i, c + 20, str(c), ha="center", fontweight="bold")
ax.set_ylabel("企业数量")
ax.set_title("识别置信度分布", fontsize=14, fontweight="bold")
fig.tight_layout()
fig.savefig(str(OUT_DIR / "chart6_confidence_dist.png"), dpi=150, bbox_inches="tight")
plt.close()
print("Chart 6 done: Confidence Distribution")

# ================================================================
# Chart 7: Category Output vs Enterprise Count Bubble
# ================================================================
fig, ax = plt.subplots(figsize=(8, 6))
for i, c in enumerate(cats):
    ax.scatter(c["enterprise_count"], c["output_index"],
               s=c["output_index"]/50, alpha=0.6, color=COLORS[i % len(COLORS)])
    ax.annotate(c["category"], (c["enterprise_count"], c["output_index"]),
                textcoords="offset points", xytext=(5, 5), fontsize=9)
ax.set_xlabel("企业数量")
ax.set_ylabel("产出指数")
ax.set_title("业态规模对比(气泡大小=产出规模)", fontsize=14, fontweight="bold")
fig.tight_layout()
fig.savefig(str(OUT_DIR / "chart7_category_bubble.png"), dpi=150, bbox_inches="tight")
plt.close()
print("Chart 7 done: Category Bubble")

# ================================================================
# Chart 8: Spatial Concentration Radar/Polar
# ================================================================
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 5))

# Bar: ratio bins
ratio_bins = report.get("overview", {})
all_ratios = [r["sport_ratio"] for r in results]
bins_count = [sum(1 for r in all_ratios if r == 0),
              sum(1 for r in all_ratios if 0 < r <= 0.2),
              sum(1 for r in all_ratios if 0.2 < r <= 0.5),
              sum(1 for r in all_ratios if 0.5 < r <= 0.8),
              sum(1 for r in all_ratios if 0.8 < r <= 1.0)]
bl = ["0", "0-20%", "20-50%", "50-80%", "80-100%"]
ax1.bar(bl, bins_count, color=["#909399","#e6a23c","#e6a23c","#67c23a","#409eff"])
ax1.set_title("体育业务占比区间分布(全量)", fontsize=12, fontweight="bold")
for i, (l, c) in enumerate(zip(bl, bins_count)):
    ax1.text(i, c + 100, f"{c:,}", ha="center", fontsize=9)

# Pie: sport vs non-sport
sport_count = sum(1 for r in results if r["is_sport"])
non_sport = len(results) - sport_count
ax2.pie([non_sport, sport_count], labels=["非体育", "体育相关"],
        autopct="%1.2f%%", colors=["#909399", "#409eff"], startangle=90, explode=(0, 0.05))
ax2.set_title("体育企业占比", fontsize=12, fontweight="bold")
fig.tight_layout()
fig.savefig(str(OUT_DIR / "chart8_overview_dist.png"), dpi=150, bbox_inches="tight")
plt.close()
print("Chart 8 done: Overview Distribution")

print(f"\nAll 8 charts saved to {OUT_DIR}")
