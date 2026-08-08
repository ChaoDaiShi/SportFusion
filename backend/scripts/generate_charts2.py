# -*- coding: utf-8 -*-
"""Generate additional analysis charts for the SportFusion report."""
import json, os, sys, re
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np
import pandas as pd
from collections import Counter

# Find Chinese font
for fp in ["C:/Windows/Fonts/msyh.ttc", "C:/Windows/Fonts/simhei.ttf", "C:/Windows/Fonts/simsun.ttc"]:
    if os.path.exists(fp):
        zh_font = fm.FontProperties(fname=fp)
        plt.rcParams["font.family"] = zh_font.get_name()
        break
plt.rcParams["axes.unicode_minus"] = False

COLORS = ["#409eff", "#67c23a", "#e6a23c", "#f56c6c", "#909399", "#b37feb", "#5cdbd3", "#ff85c0", "#ffd666"]
OUT_DIR = Path("../../data/processed/charts")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Load data
ratio_files = sorted(Path("../../data/processed").glob("sport_ratio_results_*.csv"))
boundary_files = sorted(Path("../../data/processed").glob("enterprise_boundaries_*.csv"))
df = pd.read_csv(str(ratio_files[-1]), encoding="utf-8-sig")
sport = df[df["是否体育"] == "是"].copy()
all_ent = df.copy()

if boundary_files:
    bdf = pd.read_csv(str(boundary_files[-1]), encoding="utf-8-sig")
else:
    bdf = sport

# ============================================================
# Chart A: Industry Code Top 15 (sports enterprises)
# ============================================================
code_counts = sport["行业代码"].value_counts().head(15)
fig, ax = plt.subplots(figsize=(10, 5.5))
bars = ax.bar(range(len(code_counts)), code_counts.values, color=["#e74c3c" if i < 3 else "#409eff" for i in range(len(code_counts))])
for i, (bar, val) in enumerate(zip(bars, code_counts.values)):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 10, str(val), ha="center", fontsize=9, fontweight="bold")
ax.set_xticks(range(len(code_counts)))
ax.set_xticklabels([str(int(c)) for c in code_counts.index], rotation=45, ha="right", fontsize=9)
ax.set_ylabel("企业数量", fontsize=12)
ax.set_title("体育企业行业代码分布TOP15", fontsize=14, fontweight="bold")
# Add code description for top 3
top3_desc = {8930: "健身休闲活动", 5242: "体育用品零售", 8911: "体育组织"}
for i, (code, cnt) in enumerate(code_counts.head(3).items()):
    desc = top3_desc.get(int(code), "")
    if desc:
        ax.annotate(desc, (i, cnt), textcoords="offset points", xytext=(0, -20), ha="center", fontsize=8, color="#e74c3c")
fig.tight_layout()
fig.savefig(str(OUT_DIR / "chart_a_industry_codes.png"), dpi=150, bbox_inches="tight")
plt.close()
print("Chart A done: Industry Codes TOP15")

# ============================================================
# Chart B: Crossover Type Distribution
# ============================================================
cross_types = sport["跨界类型"].dropna()
# Simplify categories
def simplify_cross(t):
    if "纯跨界" in str(t): return "纯跨界(行业代码非体育)"
    if "潜在跨界" in str(t): return "潜在跨界(间接代码)"
    if "多元经营" in str(t): return "多元经营(直接代码+非体育业务线)"
    return "其他"
cross_simple = cross_types.apply(simplify_cross).value_counts()
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4.5))
# Pie
wedges, texts, autotexts = ax1.pie(cross_simple.values, labels=None, autopct="%1.1f%%",
                                     colors=COLORS[:len(cross_simple)], startangle=90,
                                     explode=[0.05]*len(cross_simple))
ax1.legend(wedges, [f"{l}\n({v}家)" for l, v in zip(cross_simple.index, cross_simple.values)],
           loc="center left", bbox_to_anchor=(1, 0.5), fontsize=8)
ax1.set_title("跨界经营类型分布", fontsize=13, fontweight="bold")
# Bar: crossover vs non-crossover
cross_count = sport["是否跨界"].value_counts()
labels_bi = ["非跨界体育企业", "跨界经营企业"]
vals_bi = [int(cross_count.get("否", 0)), int(cross_count.get("是", 0))]
ax2.bar(labels_bi, vals_bi, color=["#409eff", "#e6a23c"])
for i, v in enumerate(vals_bi):
    ax2.text(i, v + 50, f"{v}\n({v/len(sport)*100:.1f}%)", ha="center", fontsize=11, fontweight="bold")
ax2.set_title("跨界经营占比", fontsize=13, fontweight="bold")
fig.tight_layout()
fig.savefig(str(OUT_DIR / "chart_b_crossover_types.png"), dpi=150, bbox_inches="tight")
plt.close()
print("Chart B done: Crossover Types")

# ============================================================
# Chart C: Region Per-Enterprise Output
# ============================================================
if "区域" in sport.columns:
    region_stats = sport.groupby("区域").agg(
        count=("体育业务占比", "count"),
        total_output=("体育业务占比", lambda x: (x * 100).sum())
    ).reset_index()
    region_stats["per_enterprise"] = region_stats["total_output"] / region_stats["count"]
    region_stats = region_stats[region_stats["count"] >= 20].sort_values("per_enterprise", ascending=False).head(12)

    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.barh(range(len(region_stats)), region_stats["per_enterprise"].values,
                   color=["#e74c3c" if v > 70 else "#409eff" for v in region_stats["per_enterprise"].values])
    for i, (bar, val, cnt, outp) in enumerate(zip(bars, region_stats["per_enterprise"].values,
                                                    region_stats["count"].values, region_stats["total_output"].values)):
        ax.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height()/2,
                f"均值{val:.1f} | {cnt}家 | 总产出{outp:.0f}", va="center", fontsize=8)
    ax.set_yticks(range(len(region_stats)))
    ax.set_yticklabels(region_stats["区域"].values)
    ax.invert_yaxis()
    ax.set_xlabel("平均每企业产出指数", fontsize=12)
    ax.set_title("各区域体育企业平均产出效率对比", fontsize=14, fontweight="bold")
    fig.tight_layout()
    fig.savefig(str(OUT_DIR / "chart_c_region_efficiency.png"), dpi=150, bbox_inches="tight")
    plt.close()
    print("Chart C done: Region Efficiency")
else:
    print("Chart C SKIPPED: no region column")

# ============================================================
# Chart D: Business Line Structure (sport vs non-sport lines)
# ============================================================
if "业务总线数" in sport.columns and "体育业务线数" in sport.columns:
    total_lines = sport["业务总线数"].values
    sport_lines = sport["体育业务线数"].values
    non_sport_lines = total_lines - sport_lines

    # Group by total lines
    line_bins = [(1,), (2,), (3,), (4,5), (6,10), (11,37)]
    bin_labels = ["1条", "2条", "3条", "4-5条", "6-10条", "11+条"]
    sport_avg = []
    non_avg = []
    counts = []
    for indices in line_bins:
        if len(indices) == 1:
            mask = total_lines == indices[0]
        else:
            mask = (total_lines >= indices[0]) & (total_lines <= indices[1])
        if mask.sum() > 0:
            sport_avg.append(sport_lines[mask].mean())
            non_avg.append(non_sport_lines[mask].mean())
            counts.append(mask.sum())
        else:
            sport_avg.append(0)
            non_avg.append(0)
            counts.append(0)

    fig, ax = plt.subplots(figsize=(9, 5))
    x = np.arange(len(bin_labels))
    w = 0.35
    ax.bar(x - w/2, sport_avg, w, label="体育业务线数(均值)", color="#409eff")
    ax.bar(x + w/2, non_avg, w, label="非体育业务线数(均值)", color="#909399")
    for i in range(len(bin_labels)):
        if counts[i] > 0:
            ax.text(i, max(sport_avg[i], non_avg[i]) + 0.1, f"n={counts[i]}", ha="center", fontsize=8, color="gray")
    ax.set_xticks(x)
    ax.set_xticklabels(bin_labels)
    ax.set_ylabel("平均业务线数", fontsize=12)
    ax.set_title("体育企业业务线结构分析", fontsize=14, fontweight="bold")
    ax.legend()
    fig.tight_layout()
    fig.savefig(str(OUT_DIR / "chart_d_business_lines.png"), dpi=150, bbox_inches="tight")
    plt.close()
    print("Chart D done: Business Lines")
else:
    print("Chart D SKIPPED")

# ============================================================
# Chart E: Confidence vs Ratio Scatter
# ============================================================
if "置信度" in sport.columns and "体育业务占比" in sport.columns:
    conf = sport["置信度"].values
    ratio = sport["体育业务占比"].values * 100
    # Color by crossover
    colors_list = ["#e6a23c" if c == "是" else "#409eff" for c in sport["是否跨界"].values]

    fig, ax = plt.subplots(figsize=(8, 6))
    scatter = ax.scatter(ratio, conf, c=colors_list, alpha=0.7, s=30, edgecolors="white", linewidth=0.5, rasterized=True)
    ax.axhline(y=0.9, color="green", linestyle="--", alpha=0.7, linewidth=1.5, label="高置信度线(0.90)")
    ax.axhline(y=0.7, color="orange", linestyle="--", alpha=0.7, linewidth=1.5, label="中置信度线(0.70)")
    ax.axvline(x=50, color="red", linestyle="--", alpha=0.6, linewidth=1.5, label="占比50%线")
    ax.set_xlabel("体育业务占比 (%)", fontsize=12)
    ax.set_ylabel("识别置信度", fontsize=12)
    ax.set_title("体育企业置信度-占比关系图", fontsize=14, fontweight="bold")
    # Legend manually
    from matplotlib.patches import Patch
    legend_elements = [Patch(facecolor="#409eff", label="非跨界体育企业"),
                       Patch(facecolor="#e6a23c", label="跨界经营企业")]
    ax.legend(handles=legend_elements, loc="lower right")
    # Add quadrant counts
    q1 = ((ratio > 50) & (conf > 0.7)).sum()
    q2 = ((ratio <= 50) & (conf > 0.7)).sum()
    q3 = ((ratio <= 50) & (conf <= 0.7)).sum()
    q4 = ((ratio > 50) & (conf <= 0.7)).sum()
    ax.text(90, 0.95, f"高占比高置信: {q1}", fontsize=8, color="green")
    ax.text(20, 0.95, f"低占比高置信: {q2}", fontsize=8, color="orange")
    ax.text(20, 0.55, f"低占比低置信: {q3}", fontsize=8, color="gray")
    ax.text(90, 0.55, f"高占比低置信: {q4}", fontsize=8, color="red")
    fig.tight_layout()
    fig.savefig(str(OUT_DIR / "chart_e_confidence_ratio.png"), dpi=200, bbox_inches="tight")
    plt.close()
    print("Chart E done: Confidence vs Ratio")
else:
    print("Chart E SKIPPED")

# ============================================================
# Chart F: Top Sport Keywords (from boundary data)
# ============================================================
if "体育关键词" in bdf.columns:
    all_kw = []
    for kw_str in bdf["体育关键词"].dropna():
        for kw in str(kw_str).split(";"):
            kw = kw.strip()
            if kw and len(kw) >= 2:
                all_kw.append(kw)
    kw_counts = Counter(all_kw).most_common(20)

    fig, ax = plt.subplots(figsize=(10, 5.5))
    kw_names = [k for k, v in kw_counts]
    kw_vals = [v for k, v in kw_counts]
    bars = ax.barh(range(len(kw_names)), kw_vals, color=["#e74c3c" if i < 3 else "#409eff" for i in range(len(kw_names))])
    for i, (bar, val) in enumerate(zip(bars, kw_vals)):
        ax.text(bar.get_width() + 5, bar.get_y() + bar.get_height()/2, str(val), va="center", fontsize=9)
    ax.set_yticks(range(len(kw_names)))
    ax.set_yticklabels(kw_names)
    ax.invert_yaxis()
    ax.set_xlabel("命中次数", fontsize=12)
    ax.set_title("体育关键词命中频次TOP20", fontsize=14, fontweight="bold")
    fig.tight_layout()
    fig.savefig(str(OUT_DIR / "chart_f_top_keywords.png"), dpi=150, bbox_inches="tight")
    plt.close()
    print("Chart F done: Top Keywords")
else:
    print("Chart F SKIPPED: no keyword column")

print("\nAll charts generated in:", str(OUT_DIR))
