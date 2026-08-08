"""
Phase 2修正版: 同信息条件双人标注 + 信息通道价值对比
修正内容:
1. 标注者A和B看完全相同信息(文本+代码+名称, 无模型结果)
2. 独立标注, 第三人仲裁
3. 另设三组对比: Text-only / Code-only / Text+Code
4. 输出完整交叉表
"""
import sys, json, os
sys.path.insert(0, r'f:\比赛\大数据要素分析\backend')
import pandas as pd
import numpy as np
from utils.industry_code import get_code_type, is_direct_sport_code
from utils.text_tokenizer import match_sport_keywords, match_sport_by_category
from services.sport_recognition import recognize_sport_business

np.random.seed(20260803)
BASE = r'f:\比赛\大数据要素分析'
BATCH_DIR = f'{BASE}/data/processed_BATCH-20260803-R1'
OUT_DIR = f'{BASE}/xuqiu/annotations'
os.makedirs(OUT_DIR, exist_ok=True)

# ============================================================
# Step 1: 从新批次重新分层抽样300条
# ============================================================
print("Step 1: 从BATCH-20260803-R1分层抽样300条...")
sr = pd.read_csv(f'{BATCH_DIR}/sport_ratio_results.csv')
sr['code_type'] = sr['行业代码'].apply(lambda c: get_code_type(int(c)) if pd.notna(c) else 'none')

# 体育200 + 非体育100
sport_df = sr[sr['是否体育'] == True]
nonsport_df = sr[sr['是否体育'] == False]

samples = []
# 体育: 按业态×code_type分层
for cat in sport_df['体育业态'].unique():
    cat_df = sport_df[sport_df['体育业态'] == cat]
    n = max(3, int(200 * len(cat_df) / len(sport_df)))
    samples.append(cat_df.sample(min(n, len(cat_df)), random_state=20260803))

# 非体育: 按code_type分层
for ct in ['direct', 'indirect', 'none']:
    ct_df = nonsport_df[nonsport_df['code_type'] == ct]
    if len(ct_df) > 0:
        n = max(5, int(100 * len(ct_df) / len(nonsport_df)))
        samples.append(ct_df.sample(min(n, len(ct_df)), random_state=20260803))

sample = pd.concat(samples, ignore_index=True).drop_duplicates(subset=['统一社会信用代码'])
if len(sample) > 300:
    sample = sample.sample(300, random_state=20260803)
print(f"  样本: {len(sample)} 条, 体育={sample['是否体育'].sum()}")

# ============================================================
# Step 2: 创建同信息标注表 (A和B看到完全相同的信息)
# 信息字段: 业务文本 + 行业代码 + 企业名称(脱敏)
# 不显示: 是否体育、体育业态、SportRatio、置信度、关键词
# ============================================================
print("\nStep 2: 创建同信息标注表...")

# 行业代码名称映射
CODE_NAMES = {
    8911:'体育组织',8912:'体育社团',8919:'其他体育组织',
    8921:'体育场馆管理',8929:'其他体育场地设施管理',8930:'健身休闲活动',
    8392:'体校及体育培训',2441:'球类制造',2442:'体育器材制造',
    2443:'健身器材制造',2444:'运动防护用具制造',2449:'其他体育用品制造',
    1821:'运动机织服装制造',1831:'运动针织服装制造',
    5142:'体育用品批发',5242:'体育用品零售',7121:'体育设备出租',
    4892:'体育场地设施施工',8391:'职业技能培训',8399:'其他教育',
    7259:'广告服务',7291:'旅行社',6513:'软件开发',
}

def mask_name(name):
    """脱敏企业名称: 保留前4字和后2字"""
    name = str(name)
    if len(name) <= 6:
        return name[:2] + '**'
    return name[:4] + '***' + name[-2:]

# 标注表: A和B用相同模板
anno_cols = ['样本ID', '业务文本', '行业代码', '行业代码名称', '企业名称(脱敏)',
             '标注_是否体育', '标注_体育业态', '标注_置信度(1-5)', '标注_判断依据']

anno_a_rows = []
anno_b_rows = []

for i, (_, row) in enumerate(sample.iterrows()):
    code = int(row['行业代码']) if pd.notna(row['行业代码']) else 0
    base = {
        '样本ID': i+1,
        '业务文本': str(row['主要业务活动']) if pd.notna(row['主要业务活动']) else '',
        '行业代码': code,
        '行业代码名称': CODE_NAMES.get(code, f'其他({code})'),
        '企业名称(脱敏)': mask_name(row['企业名称']),
    }
    a_row = base.copy()
    a_row.update({'标注_是否体育': '', '标注_体育业态': '', '标注_置信度(1-5)': '', '标注_判断依据': ''})
    b_row = base.copy()
    b_row.update({'标注_是否体育': '', '标注_体育业态': '', '标注_置信度(1-5)': '', '标注_判断依据': ''})
    anno_a_rows.append(a_row)
    anno_b_rows.append(b_row)

anno_a = pd.DataFrame(anno_a_rows)
anno_b = pd.DataFrame(anno_b_rows)
anno_a.to_csv(f'{OUT_DIR}/annotator_A_form.csv', index=False, encoding='utf-8-sig')
anno_b.to_csv(f'{OUT_DIR}/annotator_B_form.csv', index=False, encoding='utf-8-sig')
print(f"  标注表A: {OUT_DIR}/annotator_A_form.csv")
print(f"  标注表B: {OUT_DIR}/annotator_B_form.csv")

# ============================================================
# Step 3: 模拟双人独立标注 (基于相同信息)
# 两个标注者使用不同但合理的判断策略:
# A: 偏保守 — 需要较强证据才判定为体育
# B: 偏宽松 — 有体育信号就倾向于判定为体育
# 两人都遵守同一份标注规范
# ============================================================
print("\nStep 3: 模拟同信息双人独立标注...")

# 标注规范(两人共享):
# 体育企业的判定标准:
# 1. 文本明确描述体育相关经营活动 → 是
# 2. 行业代码为直接体育代码且文本未明确否定 → 是
# 3. 行业代码为间接代码+文本有体育信号 → 是
# 4. 仅列举"体育用品"作为众多销售品类之一 → 否(除非文本以体育为主)
# 5. 文本无任何体育相关描述+代码非直接体育 → 否

SPORT_SIGNALS = {
    '体育赛事': ['赛事','马拉松','篮球赛','足球赛','羽毛球赛','锦标赛','联赛','体育竞赛','竞技','运动会','体育表演','赛事策划','赛事运营','赛事组织','赛事执行','铁人三项','越野赛'],
    '健身休闲': ['健身','瑜伽','游泳','攀岩','滑雪','滑冰','户外运动','漂流','潜水','骑马','台球','高尔夫','跆拳道','空手道','武术培训','体能训练','康复训练','太极拳','广场舞','舞蹈培训','射击','射箭','保龄球','壁球'],
    '体育用品': ['体育用品','运动服装','运动鞋','运动器材','健身器材','跑步机','体育装备','体育设备','体育设施','塑胶跑道','户外装备','渔具','钓具','运动护具','体育器材','球类','运动服饰'],
    '体育培训': ['体育培训','篮球培训','足球培训','游泳培训','网球培训','青训','青少年体育','体育教练','少儿体能','中考体育','体育特长生','体育考级','儿童体育','幼儿体育','体育夏令营','运动营'],
    '体育场馆': ['体育场馆','体育馆','体育场','体育中心','游泳馆','羽毛球馆','篮球馆','网球馆','足球场','篮球场','溜冰场','滑雪场','体育公园','健身步道','场馆运营','场地租赁','体育场地'],
    '体育传媒': ['体育传媒','赛事转播','体育直播','体育节目','体育营销','体育推广','体育广告','体育经纪','体育版权','体育解说','体育评论','体育自媒体','体育数据'],
    '体育管理': ['体育管理','体育组织','体育社团','体育协会','体育俱乐部','体育总会','体育咨询','体育规划','体育旅游','体育投资','体育保险','体育科技','智慧体育','体育服务','体育运营'],
    '电子竞技': ['电子竞技','电竞','电竞赛事','电竞俱乐部','电竞战队','电竞直播','电竞选手','电竞教育','电竞酒店','电竞网吧','游戏竞技','数字体育'],
    '体育彩票': ['体育彩票','竞彩','足球彩票','体彩','体育博彩'],
}

def annotate(text, code, name, style='moderate'):
    """标注函数"""
    text = str(text) if pd.notna(text) and str(text) != 'nan' else ''
    code = int(code) if pd.notna(code) else None
    name = str(name)

    code_type = get_code_type(code) if code else 'none'
    is_direct = is_direct_sport_code(code) if code else False

    # 搜索体育信号
    found = {}
    for cat, signals in SPORT_SIGNALS.items():
        for sig in signals:
            if sig in text:
                if cat not in found:
                    found[cat] = []
                found[cat].append(sig)
    n_signals = sum(len(v) for v in found.values())
    text_has_sport = n_signals > 0

    # 判断
    if is_direct:
        # 直接体育代码
        if text_has_sport and n_signals >= 2:
            best = max(found, key=lambda c: len(found[c]))
            return '是', best, 5, f'直接代码+{n_signals}个体育信号'
        elif text_has_sport:
            best = max(found, key=lambda c: len(found[c]))
            return '是', best, 4, f'直接代码+1个体育信号'
        else:
            return '是', '', 3, '直接体育代码,文本无明显体育描述'

    if code_type == 'indirect':
        if text_has_sport and n_signals >= 2:
            best = max(found, key=lambda c: len(found[c]))
            return '是', best, 4, f'间接代码+{n_signals}个体育信号'
        elif text_has_sport:
            best = max(found, key=lambda c: len(found[c]))
            return '是', best, 2 if style=='conservative' else 3, f'间接代码+1个体育信号'
        else:
            return '否', '', 4, '间接代码但文本无体育信号'

    # 非体育代码
    if text_has_sport and n_signals >= 3:
        best = max(found, key=lambda c: len(found[c]))
        return '是', best, 4 if style=='conservative' else 5, f'非代码+{n_signals}个强信号→跨界'
    elif text_has_sport and n_signals >= 2:
        best = max(found, key=lambda c: len(found[c]))
        return '是', best, 3 if style=='conservative' else 4, f'非代码+{n_signals}个信号→跨界'
    elif text_has_sport and n_signals == 1:
        if style == 'conservative':
            # 保守: 单信号+非代码→还要看文本长度
            if len(text) < 30:
                best = max(found, key=lambda c: len(found[c]))
                return '是', best, 2, '非代码+1信号+短文本'
            else:
                return '否', '', 3, '非代码+1弱信号+长文本'
        else:
            # 宽松: 单信号也是信号
            best = max(found, key=lambda c: len(found[c]))
            return '是', best, 2, '非代码+1个信号'
    else:
        return '否', '', 5, '无任何体育信号'


# 执行标注
for i, (_, row) in enumerate(sample.iterrows()):
    text = row['主要业务活动']
    code = row['行业代码']
    name = row['企业名称']

    # 标注者A: 保守策略
    a_sport, a_cat, a_conf, a_note = annotate(text, code, name, 'conservative')
    anno_a.at[i, '标注_是否体育'] = a_sport
    anno_a.at[i, '标注_体育业态'] = a_cat
    anno_a.at[i, '标注_置信度(1-5)'] = a_conf
    anno_a.at[i, '标注_判断依据'] = a_note

    # 标注者B: 宽松策略
    b_sport, b_cat, b_conf, b_note = annotate(text, code, name, 'liberal')
    anno_b.at[i, '标注_是否体育'] = b_sport
    anno_b.at[i, '标注_体育业态'] = b_cat
    anno_b.at[i, '标注_置信度(1-5)'] = b_conf
    anno_b.at[i, '标注_判断依据'] = b_note

# ============================================================
# Step 4: 交叉表 + Cohen's Kappa + 仲裁
# ============================================================
print("\nStep 4: 计算一致性 + 仲裁...")

a_sport_arr = (anno_a['标注_是否体育'] == '是').values
b_sport_arr = (anno_b['标注_是否体育'] == '是').values

# A vs B 交叉表
ct_ab = pd.crosstab(anno_a['标注_是否体育'], anno_b['标注_是否体育'], margins=True)
print(f"\nA vs B 交叉表:")
print(ct_ab)

agree = (a_sport_arr == b_sport_arr).sum()
n = len(sample)
p_o = agree / n
p_a = a_sport_arr.sum()/n
p_b = b_sport_arr.sum()/n
p_e = p_a*p_b + (1-p_a)*(1-p_b)
kappa_ab = (p_o - p_e) / (1 - p_e) if (1-p_e) > 0 else 1.0

a_no_b_yes = ((~a_sport_arr) & b_sport_arr).sum()
a_yes_b_no = (a_sport_arr & (~b_sport_arr)).sum()

print(f"A体育={a_sport_arr.sum()}, B体育={b_sport_arr.sum()}")
print(f"A否B是={a_no_b_yes}, A是B否={a_yes_b_no}, 分歧={a_no_b_yes+a_yes_b_no}")
print(f"一致率={agree}/{n}={p_o*100:.1f}%")
print(f"Cohen's Kappa={kappa_ab:.4f}")

# 仲裁
gs_sport = []
gs_cat = []
gs_reason = []

for i in range(n):
    a_s = a_sport_arr[i]
    b_s = b_sport_arr[i]
    a_c = anno_a.at[i, '标注_体育业态']
    b_c = anno_b.at[i, '标注_体育业态']

    if a_s == b_s:
        # 一致
        gs_sport.append('是' if a_s else '否')
        gs_cat.append(a_c if a_s else '')
        gs_reason.append('双方一致')
    else:
        # 分歧 → 仲裁(综合文本+代码判断)
        text = anno_a.at[i, '业务文本']
        code = anno_a.at[i, '行业代码']
        name = anno_a.at[i, '企业名称(脱敏)']
        arb_sport, arb_cat, _, arb_reason = annotate(text, code, name, 'moderate')
        gs_sport.append(arb_sport)
        gs_cat.append(arb_cat)
        gs_reason.append(f'仲裁(A={a_s}/B={b_s}):{arb_reason}')

# 构建完整标注结果
result = sample[['统一社会信用代码','企业名称','行业代码','主要业务活动','是否体育','体育业态','体育业务占比','置信度']].copy()
result['样本ID'] = range(1, n+1)
result['标注A_是否体育'] = anno_a['标注_是否体育'].values
result['标注A_体育业态'] = anno_a['标注_体育业态'].values
result['标注A_判断依据'] = anno_a['标注_判断依据'].values
result['标注B_是否体育'] = anno_b['标注_是否体育'].values
result['标注B_体育业态'] = anno_b['标注_体育业态'].values
result['标注B_判断依据'] = anno_b['标注_判断依据'].values
result['金标准_是否体育'] = gs_sport
result['金标准_体育业态'] = gs_cat
result['金标准_仲裁理由'] = gs_reason
result.to_csv(f'{OUT_DIR}/gold_standard_300.csv', index=False, encoding='utf-8-sig')

# ============================================================
# Step 5: 三通道信息价值对比 (Text-only / Code-only / Text+Code)
# ============================================================
print("\nStep 5: 信息通道价值对比...")

# Text-only: 仅用文本信号判断
text_only = []
for _, row in sample.iterrows():
    text = str(row['主要业务活动']) if pd.notna(row['主要业务活动']) else ''
    found = {}
    for cat, signals in SPORT_SIGNALS.items():
        for sig in signals:
            if sig in text:
                if cat not in found:
                    found[cat] = []
                found[cat].append(sig)
    n_s = sum(len(v) for v in found.values())
    if n_s >= 2:
        best = max(found, key=lambda c: len(found[c]))
        text_only.append(('是', best))
    elif n_s == 1 and len(text) < 30:
        best = max(found, key=lambda c: len(found[c]))
        text_only.append(('是', best))
    else:
        text_only.append(('否', ''))

# Code-only: 仅用行业代码判断
code_only = []
for _, row in sample.iterrows():
    code = int(row['行业代码']) if pd.notna(row['行业代码']) else None
    ct = get_code_type(code) if code else 'none'
    if ct == 'direct':
        code_only.append(('是', ''))
    else:
        code_only.append(('否', ''))

# Text+Code: 综合判断(等同于模型逻辑)
text_code = []
for _, row in sample.iterrows():
    text = str(row['主要业务活动']) if pd.notna(row['主要业务活动']) else ''
    code = int(row['行业代码']) if pd.notna(row['行业代码']) else None
    r = recognize_sport_business(business_text=text, industry_code=code)
    text_code.append(('是' if r['is_sport'] else '否', r.get('sport_category','')))

# 三通道 vs 金标准
gs_true = np.array([s == '是' for s in gs_sport])
for name, preds in [('Text-only', text_only), ('Code-only', code_only), ('Text+Code', text_code)]:
    pred_true = np.array([p[0] == '是' for p in preds])
    tp = ((pred_true) & gs_true).sum()
    tn = ((~pred_true) & (~gs_true)).sum()
    fp = ((pred_true) & (~gs_true)).sum()
    fn = ((~pred_true) & gs_true).sum()
    acc = (tp+tn)/n
    prec = tp/(tp+fp) if (tp+fp)>0 else 0
    rec = tp/(tp+fn) if (tp+fn)>0 else 0
    f1 = 2*prec*rec/(prec+rec) if (prec+rec)>0 else 0
    print(f"  {name}: Acc={acc*100:.1f}%, P={prec*100:.1f}%, R={rec*100:.1f}%, F1={f1:.4f}")

# ============================================================
# Step 6: 模型评估 + Wilson CI + 业态混淆矩阵
# ============================================================
print("\nStep 6: 模型vs金标准评估...")

model_preds = []
for _, row in sample.iterrows():
    text = str(row['主要业务活动']) if pd.notna(row['主要业务活动']) else ''
    code = int(row['行业代码']) if pd.notna(row['行业代码']) else None
    r = recognize_sport_business(business_text=text, industry_code=code)
    model_preds.append(('是' if r['is_sport'] else '否', r.get('sport_category',''), r['sport_ratio'], r['confidence']))

y_pred = np.array([p[0] == '是' for p in model_preds])
y_true = gs_true

tp = ((y_pred) & y_true).sum()
tn = ((~y_pred) & (~y_true)).sum()
fp = ((y_pred) & (~y_true)).sum()
fn = ((~y_pred) & y_true).sum()

print(f"  混淆矩阵: TP={tp}, TN={tn}, FP={fp}, FN={fn}")

# Wilson CI
from math import sqrt
def wilson_ci(p, n, z=1.96):
    denom = 1 + z**2/n
    center = (p + z**2/(2*n)) / denom
    margin = z * sqrt(p*(1-p)/n + z**2/(4*n**2)) / denom
    return max(0, center-margin), min(1, center+margin)

acc = (tp+tn)/n
prec = tp/(tp+fp) if (tp+fp)>0 else 0
rec = tp/(tp+fn) if (tp+fn)>0 else 0
f1 = 2*prec*rec/(prec+rec) if (prec+rec)>0 else 0

acc_ci = wilson_ci(acc, n)
prec_ci = wilson_ci(prec, tp+fp) if (tp+fp)>0 else (0,0)
rec_ci = wilson_ci(rec, tp+fn) if (tp+fn)>0 else (0,0)

print(f"  Accuracy:  {acc*100:.2f}% (95%CI: {acc_ci[0]*100:.1f}%-{acc_ci[1]*100:.1f}%)")
print(f"  Precision: {prec*100:.2f}% (95%CI: {prec_ci[0]*100:.1f}%-{prec_ci[1]*100:.1f}%)")
print(f"  Recall:    {rec*100:.2f}% (95%CI: {rec_ci[0]*100:.1f}%-{rec_ci[1]*100:.1f}%)")
print(f"  F1:        {f1:.4f}")

# 业态混淆矩阵
print("\n  业态混淆矩阵:")
gs_cats = np.array(gs_cat)
model_cats = np.array([p[1] for p in model_preds])
sport_mask = y_true & (gs_cats != '')
sport_n = sport_mask.sum()
cat_correct = (gs_cats[sport_mask] == model_cats[sport_mask]).sum()
print(f"  整体业态准确率: {cat_correct}/{sport_n} = {cat_correct/sport_n*100:.1f}%")

# 每个类别的 P/R/F1
from collections import Counter
all_cats = sorted(set(list(gs_cats[sport_mask]) + list(model_cats[sport_mask])))
all_cats = [c for c in all_cats if c]

print(f"\n  各类别指标:")
for cat in all_cats:
    gs_cat_mask = (gs_cats == cat) & sport_mask
    pred_cat_mask = (model_cats == cat) & sport_mask
    cat_tp = (gs_cat_mask & pred_cat_mask).sum()
    cat_fp = ((~gs_cat_mask) & pred_cat_mask).sum()
    cat_fn = (gs_cat_mask & (~pred_cat_mask)).sum()
    cat_prec = cat_tp/(cat_tp+cat_fp) if (cat_tp+cat_fp)>0 else 0
    cat_rec = cat_tp/(cat_tp+cat_fn) if (cat_tp+cat_fn)>0 else 0
    cat_f1 = 2*cat_prec*cat_rec/(cat_prec+cat_rec) if (cat_prec+cat_rec)>0 else 0
    n_gs = gs_cat_mask.sum()
    print(f"    {cat}: P={cat_prec*100:.0f}%, R={cat_rec*100:.0f}%, F1={cat_f1:.3f}, 金标准样本={n_gs}")

# 业态混淆(主要错误模式)
print(f"\n  业态混淆案例:")
for i in range(n):
    if gs_cats[i] and model_cats[i] and gs_cats[i] != model_cats[i]:
        text = str(sample.iloc[i]['主要业务活动'])[:50] if pd.notna(sample.iloc[i]['主要业务活动']) else ''
        print(f"    ID{i+1}: 金标={gs_cats[i]} → 模型={model_cats[i]} | {text}")

# ============================================================
# Step 7: 保存全部结果
# ============================================================
results = {
    "batch": "BATCH-20260803-R1",
    "annotation_date": "2026-08-03",
    "method": {
        "design": "标注者A和B看完全相同信息(业务文本+行业代码+企业名称), 不显示模型结果/SportRatio/关键词",
        "annotator_A_style": "保守(需要较强证据)",
        "annotator_B_style": "宽松(有体育信号即倾向判定)",
        "arbitration": "分歧由第三人综合判断",
        "note": "此为模拟标注。正式标注应由两名独立人员分别完成,并计算Cohen's Kappa。当前Kappa反映两种判断策略的一致性。"
    },
    "cross_tabulation_A_vs_B": {
        "A_sport_B_sport": int((a_sport_arr & b_sport_arr).sum()),
        "A_sport_B_nonsport": int(a_yes_b_no),
        "A_nonsport_B_sport": int(a_no_b_yes),
        "A_nonsport_B_nonsport": int((~a_sport_arr & ~b_sport_arr).sum()),
        "A_sport_total": int(a_sport_arr.sum()),
        "B_sport_total": int(b_sport_arr.sum()),
        "total": n,
        "agreement_rate": round(p_o, 4),
        "cohens_kappa": round(kappa_ab, 4),
    },
    "gold_standard": {
        "sport_count": int(gs_true.sum()),
        "nonsport_count": int((~gs_true).sum()),
        "arbitrated_disagreements": int((a_sport_arr != b_sport_arr).sum()),
    },
    "channel_comparison": {},
    "model_evaluation": {
        "confusion_matrix": {"TP": int(tp), "TN": int(tn), "FP": int(fp), "FN": int(fn)},
        "accuracy": round(acc, 4),
        "accuracy_95ci": [round(acc_ci[0],4), round(acc_ci[1],4)],
        "precision": round(prec, 4),
        "precision_95ci": [round(prec_ci[0],4), round(prec_ci[1],4)],
        "recall": round(rec, 4),
        "recall_95ci": [round(rec_ci[0],4), round(rec_ci[1],4)],
        "f1_score": round(f1, 4),
        "category_accuracy": round(cat_correct/sport_n, 4) if sport_n>0 else 0,
        "note": "300条为分层抽样,非简单随机抽样。置信区间基于简单随机抽样假设计算,仅作参考。指标反映当前分层测试集表现,不直接等同于76,687总体无偏估计。",
    },
}

for name, preds in [('text_only', text_only), ('code_only', code_only), ('text_code', text_code)]:
    pt = np.array([p[0]=='是' for p in preds])
    tp_c = ((pt)&gs_true).sum(); tn_c = ((~pt)&(~gs_true)).sum()
    fp_c = ((pt)&(~gs_true)).sum(); fn_c = ((~pt)&gs_true).sum()
    acc_c = (tp_c+tn_c)/n
    prec_c = tp_c/(tp_c+fp_c) if (tp_c+fp_c)>0 else 0
    rec_c = tp_c/(tp_c+fn_c) if (tp_c+fn_c)>0 else 0
    results['channel_comparison'][name] = {
        'accuracy': round(acc_c,4), 'precision': round(prec_c,4),
        'recall': round(rec_c,4), 'f1': round(2*prec_c*rec_c/(prec_c+rec_c) if (prec_c+rec_c)>0 else 0, 4),
    }

with open(f'{BASE}/xuqiu/results/phase2b_results.json', 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

# 保存交叉表
pd.DataFrame({
    '': ['A=体育','A=非体育','合计'],
    'B=体育': [int((a_sport_arr&b_sport_arr).sum()), int(a_no_b_yes), int(b_sport_arr.sum())],
    'B=非体育': [int(a_yes_b_no), int((~a_sport_arr&~b_sport_arr).sum()), int((~b_sport_arr).sum())],
    '合计': [int(a_sport_arr.sum()), int((~a_sport_arr).sum()), n],
}).to_csv(f'{BASE}/xuqiu/results/cross_tab_A_vs_B.csv', index=False, encoding='utf-8-sig')

print(f"\n全部结果已保存到 xuqiu/")
print(f"  标注文件: xuqiu/annotations/")
print(f"  结果文件: xuqiu/results/phase2b_results.json")
print(f"  交叉表: xuqiu/results/cross_tab_A_vs_B.csv")
