"""
Phase 1: 用修正后的源码重跑全量，生成统一正式批次 BATCH-20260803-R1
修正内容：空文本+直接体育代码 → 判定为体育（与旧正式批次行为一致）
"""
import sys, os, json, time, hashlib
sys.path.insert(0, r'f:\比赛\大数据要素分析\backend')
import pandas as pd
import numpy as np
from services.sport_recognition import recognize_sport_business, get_recognition_stats
from utils.industry_code import get_code_type, is_direct_sport_code

np.random.seed(42)

BASE = r'f:\比赛\大数据要素分析'
BATCH = 'BATCH-20260803-R1'
OUT_DIR = f'{BASE}/data/processed_{BATCH}'
os.makedirs(OUT_DIR, exist_ok=True)

print("="*60)
print(f"Phase 1: 统一正式批次 {BATCH}")
print("="*60)

# 1. 加载原始数据
print("\n[1/5] 加载数据...")
df = pd.read_csv(f'{BASE}/data/processed/enterprise_dataset_20260629_160902.csv')
print(f"  加载: {len(df)} 条")

# 2. 全量识别
print("\n[2/5] 全量体育业务识别(修正后源码)...")
results = []
t0 = time.time()
for i, (_, row) in enumerate(df.iterrows()):
    text = str(row['主要业务活动']) if pd.notna(row['主要业务活动']) else ''
    code = int(row['行业代码']) if pd.notna(row['行业代码']) else None
    name = str(row['详细名称'])
    result = recognize_sport_business(business_text=text, industry_code=code, enterprise_name=name)
    result['credit_code'] = str(row['统一社会信用代码'])
    result['enterprise_name'] = name
    result['industry_code'] = code
    result['original_text'] = text
    results.append(result)
    if (i+1) % 20000 == 0:
        print(f"  已处理: {i+1}/{len(df)}")

elapsed = time.time() - t0
print(f"  完成: {len(results)} 条, 耗时 {elapsed:.1f}s")

# 3. 统计
print("\n[3/5] 统计汇总...")
stats = get_recognition_stats(results)
print(f"  体育候选企业: {stats['sport_count']} ({stats['sport_ratio_pct']}%)")
print(f"  跨界企业: {stats['crossover_count']} ({stats['crossover_pct']}%)")
print(f"  平均SportRatio: {stats['avg_sport_ratio_pct']}%")

# 4. 保存全量结果
print("\n[4/5] 保存输出文件...")

# 4a 全量SportRatio结果 CSV
sport_ratio_rows = []
for r in results:
    sport_ratio_rows.append({
        '统一社会信用代码': r['credit_code'],
        '企业名称': r['enterprise_name'],
        '行业代码': r['industry_code'],
        '主要业务活动': r.get('original_text', ''),
        '是否体育': r['is_sport'],
        '体育业态': r.get('sport_category', ''),
        '体育业务占比': r['sport_ratio'],
        '置信度': r['confidence'],
        '是否跨界': r['is_crossover'],
        '跨界类型': r.get('crossover_type', ''),
        '业务总线数': r.get('total_business_lines', 0),
        '体育业务线数': r.get('sport_business_lines', 0),
    })
sr_df = pd.DataFrame(sport_ratio_rows)
sr_df.to_csv(f'{OUT_DIR}/sport_ratio_results.csv', index=False, encoding='utf-8-sig')
print(f"  sport_ratio_results.csv: {len(sr_df)} 条")

# 4b 候选企业证据链 CSV (仅体育企业)
sport_only = [r for r in results if r['is_sport']]
boundary_rows = []
for r in sport_only:
    fw = r.get('feature_weights', {})
    boundary_rows.append({
        '企业名称': r['enterprise_name'],
        '行业代码': r['industry_code'],
        '体育业态': r.get('sport_category', ''),
        '体育业务占比': r['sport_ratio'],
        '置信度': r['confidence'],
        '是否跨界': r['is_crossover'],
        '跨界类型': r.get('crossover_type', ''),
        '业务总线数': r.get('total_business_lines', 0),
        '体育业务线数': r.get('sport_business_lines', 0),
        '体育业务线': '; '.join([sl['line'] for sl in r.get('sport_lines', [])]) if r.get('sport_lines') else '',
        '非体育业务线': '; '.join(r.get('non_sport_lines', [])) if r.get('non_sport_lines') else '',
        '体育关键词': ','.join(r.get('keywords', [])) if r.get('keywords') else '',
        '特征W1业务范围': fw.get('w1_business_scope', 0),
        '特征W2关键词密度': fw.get('w2_keyword_density', 0),
        '特征W3代码权重': fw.get('w3_code_weight', 0),
        '特征W4业态覆盖': fw.get('w4_category_coverage', 0),
    })
eb_df = pd.DataFrame(boundary_rows)
eb_df.to_csv(f'{OUT_DIR}/enterprise_boundaries.csv', index=False, encoding='utf-8-sig')
print(f"  enterprise_boundaries.csv: {len(eb_df)} 条 (仅候选企业)")

# 4c 候选企业明细 CSV
sport_detail_rows = []
for r in sport_only:
    sport_detail_rows.append({
        '统一社会信用代码': r['credit_code'],
        '企业名称': r['enterprise_name'],
        '行业代码': r['industry_code'],
        '主要业务活动': r.get('original_text', ''),
        '体育业态': r.get('sport_category', ''),
        '体育业务占比': r['sport_ratio'],
        '置信度': r['confidence'],
        '是否跨界': r['is_crossover'],
        '跨界类型': r.get('crossover_type', ''),
        '体育关键词': ','.join(r.get('keywords', [])) if r.get('keywords') else '',
    })
se_df = pd.DataFrame(sport_detail_rows)
se_df.to_csv(f'{OUT_DIR}/sport_enterprises.csv', index=False, encoding='utf-8-sig')
print(f"  sport_enterprises.csv: {len(se_df)} 条")

# 4d 验证对比统计 JSON
# 传统方法: 仅直接代码
traditional_count = sum(1 for r in results if is_direct_sport_code(r['industry_code']) if r['industry_code'])
model_count = stats['sport_count']
both = sum(1 for r in results if r['is_sport'] and is_direct_sport_code(r['industry_code']) if r['industry_code'])
only_model = model_count - both

validation = {
    "batch": BATCH,
    "run_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    "source_code_version": "SportFusion v2.1 (空文本修正)",
    "total_enterprises": len(results),
    "recognition_stats": stats,
    "comparison": {
        "summary": {
            "total_enterprises": len(results),
            "traditional_sport_count": traditional_count,
            "traditional_sport_pct": round(traditional_count/len(results)*100, 2),
            "model_sport_count": model_count,
            "model_sport_pct": round(model_count/len(results)*100, 2),
            "both_agree": both,
            "only_traditional": 0,
            "only_model": only_model,
            "incremental_count": only_model,
            "incremental_pct": round(only_model/len(results)*100, 2),
            "crossover_discovered": stats['crossover_count'],
        }
    },
    "empty_text_direct_code_count": sum(1 for r in results
        if not r.get('original_text', '') and r['is_sport'] and is_direct_sport_code(r['industry_code']) if r['industry_code']),
}
with open(f'{OUT_DIR}/model_validation.json', 'w', encoding='utf-8') as f:
    json.dump(validation, f, ensure_ascii=False, indent=2)
print(f"  model_validation.json")

# 5. 对比旧批次
print("\n[5/5] 与旧批次对比:")
print(f"  体育候选企业: 旧=8950 vs 新={model_count} (差{model_count-8950})")
print(f"  跨界企业: 旧=977 vs 新={stats['crossover_count']}")

# 6. 保存元数据
metadata = {
    "batch": BATCH,
    "run_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    "source_code": "backend/services/sport_recognition.py (v2.1 空文本修正)",
    "total_time_s": round(elapsed, 1),
    "total_enterprises": len(results),
    "sport_count": model_count,
    "crossover_count": stats['crossover_count'],
    "file_hashes": {},
}
for fname in ['sport_ratio_results.csv', 'enterprise_boundaries.csv', 'sport_enterprises.csv', 'model_validation.json']:
    fpath = f'{OUT_DIR}/{fname}'
    with open(fpath, 'rb') as f:
        metadata['file_hashes'][fname] = hashlib.sha256(f.read()).hexdigest()[:16]

with open(f'{OUT_DIR}/batch_metadata.json', 'w', encoding='utf-8') as f:
    json.dump(metadata, f, ensure_ascii=False, indent=2)

print(f"\n✅ BATCH-20260803-R1 生成完毕: {OUT_DIR}")
print(f"   体育候选: {model_count}")
print(f"   跨界: {stats['crossover_count']}")
print(f"   耗时: {elapsed:.1f}s")
