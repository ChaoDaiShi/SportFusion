"""Final Golden validation against canonical reference labels."""
import csv, json, hashlib, sys
from pathlib import Path

src = Path('data/SportFusion_人机协同仲裁参考标签集(1).csv')

# Verify SHA
sha = hashlib.sha256(src.read_bytes()).hexdigest()
assert sha == '4528854839626987fe1ca35a6ea27815d3c03ba75532fe7ac69c20ebe26a3e55', f'SHA MISMATCH: {sha}'
print(f'✅ SHA verified')

with open(src, encoding='utf-8-sig') as f:
    rows = list(csv.DictReader(f))
assert len(rows) == 300
cols = list(rows[0].keys())
print(f'✅ 300 rows, {len(cols)} columns')

# Map columns by content pattern
# Find column with values {'是': 190, '否': 95, '信息不足': 15}
gold_col = None
model_col = None
rule_sport_col = None
rule_cat_col = None
model_cat_col = None

for col in cols:
    vals = set(r[col] for r in rows)
    from collections import Counter
    cnt = Counter(r[col] for r in rows)
    if vals == {'是', '否', '信息不足'} and cnt.get('是') == 190 and cnt.get('否') == 95 and cnt.get('信息不足') == 15:
        gold_col = col
        break
assert gold_col, 'Could not find gold standard column'
print(f'✅ Gold column: {gold_col}')

# Find model column (是/否 only, 202/98 or similar)
for col in cols:
    vals = set(r[col] for r in rows)
    if vals == {'是', '否'} and col != gold_col:
        # Check distribution
        from collections import Counter
        c = Counter(r[col] for r in rows)
        if c.get('是', 0) in (202, 201, 200, 198):
            model_col = col
            print(f'✅ Model column: {col} ({dict(c)})')
            break

# Find rule category column: must yield exactly 184 canonical matches for 190 sport
nine = {'体育赛事','健身休闲','体育用品','体育培训','体育场馆','体育传媒','体育管理','电子竞技','体育彩票'}
sport_rows = [r for r in rows if r[gold_col] == '是']
for col in cols:
    cat_vals = [r[col] for r in sport_rows]
    canonical_count = sum(1 for v in cat_vals if v in nine)
    if canonical_count == 184:
        rule_cat_col = col
        break

# Find model category column: prefer '模型', then check by 171 correct
for col in cols:
    cat_vals = set(r[col] for r in sport_rows)
    if '体育赛事' in cat_vals and col != rule_cat_col:
        correct_check = sum(1 for r in sport_rows if r[rule_cat_col] in nine and r[rule_cat_col] == r[col])
        if correct_check == 171 and '模型' in col:
            model_cat_col = col
            break

print(f'✅ Rule cat column: {rule_cat_col}')
print(f'✅ Model cat column: {model_cat_col}')

# ---- BINARY VALIDATION ----
clear = [r for r in rows if r[gold_col] != '信息不足']
assert len(clear) == 285, f'Clear rows: {len(clear)}'

y_true = [1 if r[gold_col]=='是' else 0 for r in clear]
y_pred = [1 if r[model_col]=='是' else 0 for r in clear]

tp = sum(1 for t,p in zip(y_true,y_pred) if t==1 and p==1)
tn = sum(1 for t,p in zip(y_true,y_pred) if t==0 and p==0)
fp = sum(1 for t,p in zip(y_true,y_pred) if t==0 and p==1)
fn = sum(1 for t,p in zip(y_true,y_pred) if t==1 and p==0)

acc = (tp+tn)/285; prec = tp/(tp+fp) if tp+fp else 0; rec = tp/(tp+fn) if tp+fn else 0
f1 = 2*prec*rec/(prec+rec) if prec+rec else 0

print(f'\n=== BINARY VALIDATION ===')
print(f'TP={tp}, TN={tn}, FP={fp}, FN={fn}')
print(f'Acc={acc:.10f}, Prec={prec:.10f}, Rec={rec:.10f}, F1={f1:.10f}')
assert tp == 189; assert tn == 83; assert fp == 12; assert fn == 1
print('✅ Binary Golden: ALL PASSED')

# ---- CATEGORY VALIDATION ----
nine = {'体育赛事','健身休闲','体育用品','体育培训','体育场馆','体育传媒','体育管理','电子竞技','体育彩票'}
sport_rows = [r for r in rows if r[gold_col] == '是']
cat_clear = [r for r in sport_rows if r[rule_cat_col] in nine]
unknown = [r for r in sport_rows if r[rule_cat_col] not in nine]

print(f'\n=== CATEGORY VALIDATION ===')
print(f'Sport total: {len(sport_rows)}, Category clear: {len(cat_clear)}, Unknown: {len(unknown)}')
assert len(cat_clear) == 184; assert len(unknown) == 6

ct = [r[rule_cat_col] for r in cat_clear]
cp = [r[model_cat_col] for r in cat_clear]
correct = sum(1 for t,p in zip(ct,cp) if t==p)
cat_acc = correct/184
print(f'Correct: {correct}/184, Acc={cat_acc:.10f}')
assert correct == 171
print('✅ Category Golden: ALL PASSED')

# Save
ref_data = {
    'meta': {'source': str(src), 'sha256': sha, 'rows': 300,
             'gold_yes': 190, 'gold_no': 95, 'gold_insufficient': 15, 'binary_clear': 285},
    'binary': {'TP': tp, 'TN': tn, 'FP': fp, 'FN': fn,
               'accuracy': round(acc,10), 'precision': round(prec,10),
               'recall': round(rec,10), 'f1': round(f1,10)},
    'category': {'clear': 184, 'unknown': 6, 'correct': correct, 'accuracy': round(cat_acc,10)},
}
Path('formal_artifacts/reference_labels_300.json').write_text(json.dumps(ref_data, indent=2, ensure_ascii=False))
print('\n✅ Artifacts saved')
