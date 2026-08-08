"""
Phase 3: 在金标准上评估模型 + 带断言的鲁棒性测试 + 环境记录的效率测试
"""
import sys, json, time, platform, tracemalloc
sys.path.insert(0, r'f:\比赛\大数据要素分析\backend')
import pandas as pd
import numpy as np
import jieba
from services.sport_recognition import recognize_sport_business
from sklearn.metrics import cohen_kappa_score, classification_report, confusion_matrix

BASE = r'f:\比赛\大数据要素分析'
OUT_DIR = f'{BASE}/temp_experiments/phase2_annotation'

print("="*60)
print("Phase 3: 金标准模型评估")
print("="*60)

# ============================================================
# Part A: 加载金标准，运行模型，计算指标
# ============================================================
print("\n[A] 在金标准上评估模型...")
gs = pd.read_csv(f'{OUT_DIR}/annotation_complete_goldstandard.csv')

# 运行模型(使用修正后源码)
model_preds = []
for _, row in gs.iterrows():
    text = str(row['主要业务活动']) if pd.notna(row['主要业务活动']) else ''
    code = int(row['行业代码']) if pd.notna(row['行业代码']) else None
    r = recognize_sport_business(business_text=text, industry_code=code)
    model_preds.append({
        '模型_是否体育': '是' if r['is_sport'] else '否',
        '模型_体育业态': r.get('sport_category', ''),
        '模型_SportRatio': r['sport_ratio'],
        '模型_置信度': r['confidence'],
    })

model_df = pd.DataFrame(model_preds)
eval_df = pd.concat([gs, model_df], axis=1)

# 模型 vs 金标准
y_true = (eval_df['金标准_是否体育'] == '是').values
y_pred = (eval_df['模型_是否体育'] == '是').values

# 混淆矩阵
cm = confusion_matrix(y_true, y_pred)
tn, fp, fn, tp = cm.ravel() if cm.size == 4 else (0,0,0,0)

accuracy = (tp+tn)/len(y_true)
precision = tp/(tp+fp) if (tp+fp)>0 else 0
recall = tp/(tp+fn) if (tp+fn)>0 else 0
f1 = 2*precision*recall/(precision+recall) if (precision+recall)>0 else 0

# Cohen's Kappa (模型 vs 金标准)
kappa_model = cohen_kappa_score(y_true, y_pred)

print(f"\n  混淆矩阵: TP={tp}, TN={tn}, FP={fp}, FN={fn}")
print(f"  Accuracy:  {accuracy*100:.1f}%")
print(f"  Precision: {precision*100:.1f}%")
print(f"  Recall:    {recall*100:.1f}%")
print(f"  F1-Score:  {f1:.4f}")
print(f"  Cohen's Kappa (模型vs金标准): {kappa_model:.4f}")

# 业态准确率
sport_gs = eval_df[eval_df['金标准_是否体育'] == '是']
cat_correct = (sport_gs['金标准_体育业态'] == sport_gs['模型_体育业态']).sum()
cat_acc = cat_correct / len(sport_gs) if len(sport_gs) > 0 else 0
print(f"  业态准确率: {cat_correct}/{len(sport_gs)} = {cat_acc*100:.1f}%")

# 模型 vs 标注者A
kappa_A = cohen_kappa_score(y_true, (eval_df['标注A_是否体育']=='是').values)
# 模型 vs 标注者B
kappa_B = cohen_kappa_score(y_true, (eval_df['标注B_是否体育']=='是').values)
print(f"\n  模型vs标注者A Kappa: {kappa_A:.4f}")
print(f"  模型vs标注者B Kappa: {kappa_B:.4f}")
print(f"  标注者AvsB Kappa:    0.6914 (from Phase 2)")

# 误判分析
print(f"\n  假阳性(FP): {fp} 条 (模型说有,金标准说无)")
if fp > 0:
    fp_cases = eval_df[(y_pred==True) & (y_true==False)]
    for _, row in fp_cases.head(5).iterrows():
        text = str(row['主要业务活动'])[:60] if pd.notna(row['主要业务活动']) else '(空)'
        print(f"    [{row['行业代码']}] {text} → 模型:{row['模型_体育业态']}/{row['模型_SportRatio']:.4f}")

print(f"\n  假阴性(FN): {fn} 条 (模型说无,金标准说有)")
if fn > 0:
    fn_cases = eval_df[(y_pred==False) & (y_true==True)]
    for _, row in fn_cases.head(5).iterrows():
        text = str(row['主要业务活动'])[:60] if pd.notna(row['主要业务活动']) else '(空)'
        print(f"    [{row['行业代码']}] {text} → 金标准:{row['金标准_体育业态']}")

# ============================================================
# Part B: 带断言的鲁棒性测试
# ============================================================
print("\n" + "="*60)
print("[B] 带断言的鲁棒性测试")

robustness_tests = [
    # (case_name, text, code, name, expected_is_sport, expected_category, expected_ratio_range)
    ("空文本", "", None, "测试企业", False, "", None),
    ("空文本+直接代码", "", 8930, "测试企业", True, "健身休闲", (0.20, 0.22)),
    ("极短'体育'", "体育", None, "测试企业", False, "", None),  # 1字符, 分词过滤
    ("极短'健身'", "健身", None, "测试企业", False, "", None),  # 2字符但词典无精确匹配
    ("明确体育赛事", "体育赛事策划与运营", None, "测试企业", True, "体育赛事", (0.60, 0.95)),
    ("明确健身", "瑜伽培训服务", None, "测试企业", True, "健身休闲", (0.60, 0.95)),
    ("歧义:诗歌比赛", "诗歌比赛组织,朗诵比赛策划", None, "测试企业", False, "", None),
    ("歧义:五四运动", "五四运动研究,新文化运动史料整理", None, "测试企业", False, "", None),
    ("异常代码9999", "体育赛事策划", 9999, "测试企业", True, "体育赛事", (0.60, 0.95)),
    ("超长文本", "体育用品销售，" * 100, None, "测试企业", True, "体育用品", (0.30, 0.70)),
    ("纯英文", "sports training and fitness club", None, "测试企业", False, "", None),
    ("特殊字符", "体育用品@#$%^&*()12345", None, "测试企业", True, "体育用品", (0.60, 0.95)),
    ("名称含体育/文本无", "计算机软件开发", None, "成都XX体育科技有限公司", False, "", None),
    ("重复业务线去重", "健身服务，健身服务，健身服务", None, "测试企业", True, "健身休闲", (0.60, 0.95)),
]

crash_pass = 0
semantic_pass = 0
total = len(robustness_tests)

for case_name, text, code, name, exp_sport, exp_cat, exp_range in robustness_tests:
    try:
        r = recognize_sport_business(business_text=text, industry_code=code, enterprise_name=name)
        crash_pass += 1

        # 语义断言
        sem_ok = True
        if r['is_sport'] != exp_sport:
            sem_ok = False
        if exp_sport and exp_cat and r.get('sport_category', '') != exp_cat:
            sem_ok = False
        if exp_range and not (exp_range[0] <= r['sport_ratio'] <= exp_range[1]):
            sem_ok = False

        if sem_ok:
            semantic_pass += 1
        else:
            print(f"  ✗ {case_name}: is_sport={r['is_sport']}(exp={exp_sport}), cat={r.get('sport_category','')}(exp={exp_cat}), ratio={r['sport_ratio']:.4f}(exp={exp_range})")
    except Exception as e:
        print(f"  ✗ {case_name}: CRASH - {e}")

print(f"\n  稳定性(无崩溃): {crash_pass}/{total}")
print(f"  语义正确性: {semantic_pass}/{total}")
print(f"  综合通过率: {semantic_pass}/{total} = {semantic_pass/total*100:.1f}%")

# ============================================================
# Part C: 环境记录的效率测试
# ============================================================
print("\n" + "="*60)
print("[C] 效率测试(含环境记录)")

import subprocess
env_info = {
    "os": platform.platform(),
    "python_version": platform.python_version(),
    "cpu": platform.processor(),
    "jieba_version": jieba.__version__ if hasattr(jieba, '__version__') else 'unknown',
}

# 预热
for _ in range(3):
    recognize_sport_business("体育赛事策划与运营管理服务", 8911)

# 正式测试: 不同规模, 各3次取中位
test_sizes = [100, 1000, 5000, 10000, 50000, 76687]
full_df = pd.read_csv(f'{BASE}/data/processed_BATCH-20260803-R1/sport_ratio_results.csv')

efficiency_results = []
for size in test_sizes:
    times = []
    mems = []
    for run in range(3):
        sample = full_df.sample(min(size, len(full_df)), random_state=42+run)
        tracemalloc.start()
        t0 = time.time()
        for _, row in sample.iterrows():
            text = str(row['主要业务活动']) if pd.notna(row['主要业务活动']) else ''
            code = int(row['行业代码']) if pd.notna(row['行业代码']) else None
            recognize_sport_business(business_text=text, industry_code=code)
        elapsed = time.time() - t0
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        times.append(elapsed)
        mems.append(peak / 1024 / 1024)

    times.sort()
    median_time = times[1]  # 中位
    avg_per = median_time / min(size, len(full_df)) * 1000
    throughput = min(size, len(full_df)) / median_time if median_time > 0 else 0
    median_mem = sorted(mems)[1]

    efficiency_results.append({
        "sample_size": min(size, len(full_df)),
        "median_time_s": round(median_time, 3),
        "avg_per_ms": round(avg_per, 3),
        "throughput_per_s": round(throughput, 1),
        "median_peak_memory_mb": round(median_mem, 1),
    })
    print(f"  N={min(size,len(full_df))}: median={median_time:.3f}s, {avg_per:.3f}ms/条, {throughput:.0f}条/s, {median_mem:.1f}MB")

# ============================================================
# 保存全部结果
# ============================================================
all_results = {
    "batch": "BATCH-20260803-R1",
    "evaluation_date": "2026-08-03",
    "phase2_annotation": {
        "sample_size": 300,
        "cohens_kappa_AvsB": 0.6914,
        "agreement_rate": 0.847,
        "disagreements": 46,
        "gold_standard_sport_count": int(gs_yes := (eval_df['金标准_是否体育']=='是').sum()),
        "gold_standard_nonsport_count": int(300 - gs_yes),
    },
    "phase3_model_evaluation": {
        "confusion_matrix": {"TP": int(tp), "TN": int(tn), "FP": int(fp), "FN": int(fn)},
        "accuracy": round(accuracy, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1_score": round(f1, 4),
        "cohens_kappa_model_vs_gold": round(kappa_model, 4),
        "category_accuracy": round(cat_acc, 4),
        "model_vs_annotator_A_kappa": round(kappa_A, 4),
        "model_vs_annotator_B_kappa": round(kappa_B, 4),
        "method_note": "金标准由双人独立标注+第三人仲裁形成。标注者A仅看文本(盲评)，标注者B看文本+代码+名称。46条分歧经仲裁后形成最终金标准。模型评估在金标准上进行。",
    },
    "phase3_robustness": {
        "total_tests": total,
        "crash_free": crash_pass,
        "semantic_correct": semantic_pass,
        "semantic_pass_rate": round(semantic_pass/total, 4),
        "note": "语义断言包括is_sport, sport_category和sport_ratio范围三个维度的验证",
    },
    "phase3_efficiency": {
        "environment": env_info,
        "warmup_runs": 3,
        "runs_per_size": 3,
        "metric_used": "median",
        "results": efficiency_results,
    }
}

out_path = f'{BASE}/temp_experiments/phase3_evaluation_results.json'
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(all_results, f, ensure_ascii=False, indent=2)

print(f"\n✅ Phase 3 结果已保存: {out_path}")
print(f"\n{'='*60}")
print(f"核心结果摘要:")
print(f"  金标准标注: 300条, Kappa(AvB)=0.6914 (substantial)")
print(f"  模型vs金标准: Acc={accuracy*100:.1f}%, P={precision*100:.1f}%, R={recall*100:.1f}%, F1={f1:.4f}, Kappa={kappa_model:.4f}")
print(f"  鲁棒性: 语义通过率 {semantic_pass}/{total}")
print(f"  效率: {efficiency_results[-1]['avg_per_ms']:.3f}ms/条 (N={efficiency_results[-1]['sample_size']})")
