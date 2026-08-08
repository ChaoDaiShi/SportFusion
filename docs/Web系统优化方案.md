# Web端体育产业统计平台优化方案

## 文档信息

| 项目 | 内容 |
|------|------|
| 文档名称 | 多元经营背景下体育产业业务边界识别与规模测算平台 — Web端系统优化方案 |
| 版本 | v2.0 |
| 编制日期 | 2026-08-03 |
| 当前系统版本 | v1.0（企业体育属性识别与结果展示系统） |
| 目标系统版本 | v2.0（体育产业业务边界识别、经营活动比重估计、产业规模测算与统计复核平台） |

---

## 一、现状评估

### 1.1 现有系统已实现功能

**后端（FastAPI + SQLite）**
- [x] 数据上传（Excel/CSV）
- [x] 数据清洗（去重、缺失值处理）
- [x] NLP预处理（jieba分词、关键词提取、体育标签标注）
- [x] 单条/批量企业体育业务识别
- [x] 业务线拆分与分类（`parse_business_lines` / `classify_business_line`）
- [x] 四维度比重测算（W1-W4加权模型：业务范围40% + 关键词密度25% + 行业代码权重25% + 业态覆盖度10%）
- [x] 跨界经营判定（纯跨界 / 潜在跨界 / 多元经营）
- [x] 区域聚合、业态聚合、空间集中度分析
- [x] 产业结构分析（多样性指数、HHI、基尼系数）
- [x] 模型验证（Accuracy / Precision / Recall / F1 / MAE）
- [x] 图表数据接口（饼图、柱状图、折线图、地图热力图、雷达图、漏斗图、矩形树图）

**前端（Vue3 + Element Plus + ECharts）**
- [x] 数据管理页（上传、预览、清洗、NLP预处理）
- [x] 企业识别页（单条/批量识别）
- [x] 产业全景大屏（概览指标、业态分布、区域热力图、漏斗图、雷达图）
- [x] 测算对比页（传统方法 vs 模型方法）
- [x] 7种图表组件（Gauge / Line / Bar / Pie / Radar / Funnel / Treemap / Scatter）
- [x] Pinia状态管理（data / recognition / measure）

### 1.2 V1.0系统的主要差距

| 维度 | V1.0现状 | V2.0目标 | 差距等级 |
|------|----------|----------|----------|
| 系统定位 | 识别+展示工具 | 完整统计流程平台 | 🔴 核心 |
| SportShare比重估计 | W1-W4简单加权 | 机器学习回归+人工校准 | 🔴 核心 |
| 产业规模测算 | 产出指数（ratio×100） | 真实收入/从业人数/资产规模测算 | 🔴 核心 |
| 区域分析 | 通用热力图 | 四川21市州地图+下钻交互 | 🟡 重要 |
| 人工复核 | 无 | P1-P4分级复核+双人仲裁 | 🔴 核心 |
| 批次版本管理 | 无 | 完整数据/模型/词典版本追溯 | 🟡 重要 |
| 报告导出 | 无 | Word/PDF/Excel/PNG/JSON | 🟡 重要 |
| 权限管理 | 无 | JWT+RBAC+六角色 | 🟡 重要 |
| 数据库 | SQLite | PostgreSQL/MySQL | 🟡 重要 |
| 演示/正式模式 | 无 | 双模式隔离 | 🟢 增强 |

---

## 二、系统定位升级

### 2.1 定位变更

```
V1.0：企业体育属性识别与结果展示系统
  └── 功能：上传数据 → 识别体育企业 → 展示图表

V2.0：体育产业业务边界识别、经营活动比重估计、产业规模测算与统计复核平台
  └── 完整统计流程：数据导入 → 数据治理 → 边界识别 → 比重估计
                        → 规模测算 → 区域分析 → 人工复核 → 名录锁定 → 报告导出
```

### 2.2 统计业务流程

```
┌──────────┐    ┌──────────┐    ┌──────────┐
│ 数据导入  │───→│ 数据治理  │───→│ 边界识别  │
│ Excel/CSV │    │ 质量检查  │    │ SportScore│
└──────────┘    └──────────┘    └──────────┘
                                      │
                                      ▼
┌──────────┐    ┌──────────┐    ┌──────────┐
│ 报告导出  │←───│ 名录锁定  │←───│ 比重估计  │
│ 9种格式   │    │ 审核确认  │    │SportShare │
└──────────┘    └──────────┘    └──────────┘
      │                               │
      ▼                               ▼
┌──────────┐                     ┌──────────┐
│ 区域分析  │←───────────────────│ 规模测算  │
│ 21市州    │                     │ 融合算法  │
└──────────┘                     └──────────┘
```

---

## 三、核心模块重构方案

### 模块一：数据管理中心

#### 3.1 功能升级

| 功能 | V1.0 | V2.0 |
|------|------|------|
| 文件上传 | 基础拖拽上传 | 拖拽上传 + 批量导入 + 模板下载 |
| 字段识别 | 预设映射 | 智能列名匹配 + 手动映射 |
| 数据校验 | 去重 + 空值 | 缺失值/重复值/行业代码合法性/地址标准化/企业规模字段检查 |
| 批次管理 | 无 | 批量创建 + 数据版本 + 文件哈希 + 导入日志 |
| 数据模式 | 无 | 正式数据模式 / 演示数据模式 |
| 质量报告 | 简单统计 | 完整数据质量报告 |

#### 3.2 页面输出指标

```
┌─────────────────────────────────────────┐
│              数据质量报告                 │
├─────────────────────────────────────────┤
│  总记录数：76,687                        │
│  字段完整率：94.2%                       │
│  异常记录：3,421（4.5%）                 │
│  地址识别率：87.3%                       │
│  可用于规模测算的企业比例：72.1%          │
│  数据批次号：BATCH-20260803-001           │
│  数据模式：正式 / 演示                   │
│  文件哈希：SHA256: a3f2b8...             │
│  导入时间：2026-08-03 14:30:00           │
│  操作人员：admin@stats.cn                │
└─────────────────────────────────────────┘
```

#### 3.3 必须增加的字段

- `data_mode`：`formal` / `demo`
- `data_version`：`v1.0` / `v1.1` ...
- `file_hash`：SHA256
- `import_log`：完整导入日志记录

---

### 模块二：体育业务边界识别

#### 4.1 功能升级

V2.0在V1.0基础上新增：
- **SportScore计算**：将现有W1-W4权重模型升级为SportScore（保留当前4维特征，增加文本语义特征、企业公开信息特征）
- **代码—文本一致性状态**：判断行业代码与业务文本描述是否一致
- **九类业态细分识别**：赛事运营/健身休闲/体育培训/体育用品/体育场馆/体育管理/电子竞技/体育传媒/运动康复

#### 4.2 企业详情页展示字段

```
┌──────────────────────────────────────────────────┐
│                 企业体育业务详情                    │
├──────────────────────────────────────────────────┤
│  企业名称：成都XX体育文化传播有限公司               │
│  统一社会信用代码：91510100XXXXXXXXXX              │
│  ─────────────────────────────────────────────── │
│  原始行业代码：R8890（文化艺术业）                 │
│  行业代码类型：间接体育相关（indirect）             │
│  代码—文本一致性：⚠️ 不一致（代码为文化，文本含赛事） │
│  ─────────────────────────────────────────────── │
│  原始主要业务活动：                                │
│  "体育赛事策划与执行，文化艺术交流，                  │
│   企业营销策划，展览展示服务"                        │
│  ─────────────────────────────────────────────── │
│  拆分业务线（4条）：                               │
│  ① 体育赛事策划与执行 ✅ 体育 → 赛事运营（0.85）    │
│  ② 文化艺术交流     ❌ 非体育                      │
│  ③ 企业营销策划     ❌ 非体育                      │
│  ④ 展览展示服务     ❌ 非体育                      │
│  ─────────────────────────────────────────────── │
│  命中关键词：赛事、策划、执行、体育                 │
│  ─────────────────────────────────────────────── │
│  W1（业务范围占比）：0.25                          │
│  W2（关键词密度）：  0.42                          │
│  W3（代码权重）：    0.30                          │
│  W4（业态覆盖度）：  0.11                          │
│  ─────────────────────────────────────────────── │
│  SportScore：0.31                                │
│  主体育业态：赛事运营                              │
│  跨界类型：潜在跨界（间接行业代码+文本有体育业务）    │
└──────────────────────────────────────────────────┘
```

---

### 模块三：SportShare比重估计（🔴 最核心新增模块）

#### 5.1 设计思路

V1.0的W1-W4加权模型是**规则驱动**，V2.0升级为**规则+机器学习混合模型**：

```
SportShare = f(SportScore, 业务线占比, 文本语义特征, 行业代码,
               企业公开经营信息, 企业规模, 人工比重样本)
```

#### 5.2 模型架构

```
输入层                    模型层                   输出层
┌──────────────┐     ┌─────────────┐     ┌─────────────────┐
│ SportScore   │────→│             │     │ 体育经营活动比重  │
│ 业务线占比    │────→│  XGBoost    │────→│ 比重档位(5档)    │
│ 文本语义向量  │────→│  回归模型   │────→│ 预测区间[L,U]    │
│ 行业代码特征  │────→│             │────→│ 模型置信范围      │
│ 企业规模等级  │────→│             │────→│ 主要影响因素      │
│ 公开经营信息  │────→│             │────→│ 人工修正值        │
└──────────────┘     └─────────────┘     └─────────────────┘
```

#### 5.3 页面展示

```
┌──────────────────────────────────────────────────────┐
│              SportShare 体育经营活动比重               │
├──────────────────────────────────────────────────────┤
│                                                      │
│   模型预测比重：62%                                    │
│   预测区间：[52% — 72%]（95%置信水平）                  │
│   人工核定比重：65%                                    │
│                                                      │
│   ┌─────────────────────────────────────┐            │
│   │  比重档位：中高比重（50%-75%）       │            │
│   └─────────────────────────────────────┘            │
│                                                      │
│   主要依据：                                          │
│   1. 三条业务线中两条为体育业务                        │
│   2. 主营项目以赛事执行为主                           │
│   3. 行业代码为文化传播（R8890），间接体育相关          │
│   4. 官网案例中体育项目占比较高                        │
│                                                      │
│   模型置信度：中等（0.72）                             │
│   建议复核等级：P2                                    │
└──────────────────────────────────────────────────────┘
```

#### 5.4 比重档位定义

| 档位 | 范围 | 含义 |
|------|------|------|
| 极低比重 | 0% - 10% | 几乎不涉及体育业务 |
| 低比重 | 10% - 30% | 少量涉足体育 |
| 中等比重 | 30% - 50% | 体育为辅助业务 |
| 中高比重 | 50% - 75% | 体育为主要业务之一 |
| 高比重 | 75% - 100% | 以体育为核心业务 |

---

### 模块四：产业规模测算中心

#### 6.1 核心公式

\[
\text{企业体育业务规模} = \text{企业总体规模} \times \text{SportShare}
\]

#### 6.2 支持的企业规模字段

| 字段 | 类型 | 优先级 | 是否直接可用 |
|------|------|--------|-------------|
| 营业收入 | 连续值 | ⭐⭐⭐⭐⭐ | ✅ 正式收入测算 |
| 从业人数 | 连续值 | ⭐⭐⭐⭐ | ✅ 正式从业测算 |
| 资产总额 | 连续值 | ⭐⭐⭐ | ✅ 正式资产测算 |
| 注册资本 | 连续值 | ⭐⭐ | ⚠️ 代理规模估算 |
| 企业规模等级 | 分类值 | ⭐⭐ | ⚠️ 代理规模估算 |
| 其他代理指标 | - | ⭐ | ⚠️ 样本内相对指数 |

#### 6.3 页面输出

```
┌──────────────────────────────────────────────────┐
│              产业规模测算结果                       │
├──────────────────────────────────────────────────┤
│  当前测算口径：正式收入测算                         │
│  测算企业数：6,452家（覆盖率72.1%）                 │
│                                                   │
│  ┌─────────────────────────────────────────┐      │
│  │  四川省体育产业估算规模：1,285亿元        │      │
│  │  95%估计区间：[1,102亿 — 1,468亿]        │      │
│  └─────────────────────────────────────────┘      │
│                                                   │
│  方法对比：                                        │
│  ┌────────────┬──────────┬──────────┬────────┐   │
│  │  方法       │  规模     │  企业数   │  口径   │   │
│  ├────────────┼──────────┼──────────┼────────┤   │
│  │  传统代码法  │  892亿   │  4,210    │  行业代码│   │
│  │  SportFusion│  1,285亿 │  6,452    │  融合测算│   │
│  │  增量规模   │  +393亿  │  +2,242   │  跨界识别│   │
│  └────────────┴──────────┴──────────┴────────┘   │
│                                                   │
│  分业态规模：                                      │
│  赛事运营：356亿 (27.7%)                           │
│  健身休闲：298亿 (23.2%)                           │
│  体育用品：245亿 (19.1%)                           │
│  体育培训：186亿 (14.5%)                           │
│  ...                                              │
└──────────────────────────────────────────────────┘
```

#### 6.4 测算口径必须明确标注

系统必须在显著位置标注当前结果的统计口径：

- **正式收入测算**：基于企业营业收入 × SportShare（需营业收入字段完整）
- **代理规模估算**：基于注册资本/规模等级的推算（营业收入字段缺失时）
- **样本内相对指数**：仅可做排序/对比，不可加总为绝对规模

---

### 模块五：区域与空间分析

#### 7.1 新增功能

| 功能 | 状态 | 说明 |
|------|------|------|
| 地址标准化 | 🆕 新增 | 基于企业名称/注册地址提取省市区县 |
| 市州/区县识别 | 🆕 新增 | 四川21市州183区县自动匹配 |
| 经纬度匹配 | 🆕 新增 | 百度/高德地理编码API |
| 四川21市州地图 | 🆕 新增 | ECharts四川地图（GeoJSON） |
| 业态分布热力图 | 🆕 新增 | 按市州展示 |
| 企业数量+规模双指标 | 🆕 新增 | 气泡图/散点图 |
| 地区集中度 | ✅ 已有 | 升级展示 |
| 跨界经营空间分布 | 🆕 新增 | 跨界企业在各地的分布 |
| 地区对比 | 🆕 新增 | 多市州横向对比 |

#### 7.2 市州下钻交互

```
点击"成都市"后弹出：

┌──────────────────────────────────────┐
│  成都市体育产业概览                    │
├──────────────────────────────────────┤
│  候选企业数：2,230家                  │
│  体育业务估算规模：398亿元            │
│  主导业态：赛事运营（35.2%）          │
│  跨界率：12.8%                        │
│  新增候选数（相比传统代码法）：+520家  │
│  高风险复核企业数（P1）：87家         │
│                                      │
│  [查看企业列表] [导出明细] [分配复核]  │
└──────────────────────────────────────┘
```

---

### 模块六：人工复核工作台（🔴 核心新增）

#### 8.1 复核任务状态流转

```
                    ┌─────────┐
                    │  待分配  │
                    └────┬────┘
                         │
              ┌──────────┼──────────┐
              ▼          ▼          ▼
         ┌────────┐ ┌────────┐ ┌────────┐
         │ 待复核  │ │ 复核中  │ │信息不足 │
         └───┬────┘ └───┬────┘ └───┬────┘
             │          │          │
    ┌────────┼──────────┘          │
    ▼        ▼                     │
┌───────┐ ┌───────┐               │
│已确认  │ │待仲裁  │←──────────────┘
└───┬───┘ └───┬───┘
    │         │
    │    ┌────┼────┐
    │    ▼    ▼    │
    │ ┌───┐ ┌───┐  │
    │ │A确│ │B确│  │
    │ │认 │ │认 │  │
    │ └─┬─┘ └─┬─┘  │
    │   └──┬──┘    │
    │      ▼       │
    │  ┌──────┐    │
    └──→ 已锁定 │←──┘
       └──────┘
```

#### 8.2 P1-P4复核优先级

| 等级 | 典型条件 | 预估占比 |
|------|----------|----------|
| **P1** | 代码与文本明显冲突、模型与人工差异大（差值>30%）、SportShare处于阈值边界 | ~5% |
| **P2** | 934家补充识别、潜在跨界企业、置信度中等（0.5-0.7） | ~15% |
| **P3** | 文本证据较弱、词典边界样本、单一关键词命中 | ~20% |
| **P4** | 代码与文本一致、直接体育代码+高置信度（>0.85）、证据充分 | ~60% |

#### 8.3 复核输入字段

每个复核任务包含：
- 体育属性判定（是/否/存疑）
- 体育业态修正（可覆盖模型结果）
- SportShare修正值
- 判断理由（文本输入）
- 证据附件（截图/PDF/网页链接）
- 是否需要补充调查（是/否）
- 复核人员
- 复核时间

#### 8.4 双人仲裁机制

```
┌─────────────────────────────────────────────┐
│                仲裁流程                       │
├─────────────────────────────────────────────┤
│  ① 任务同时分配给复核员A和复核员B              │
│  ② 两人独立完成复核，互不可见                 │
│  ③ 结果比较：                                │
│     • 一致 → 直接确认（已锁定）               │
│     • 不一致 → 自动进入仲裁                   │
│  ④ 仲裁员裁决，保留双方意见                   │
│  ⑤ 仲裁结果不覆盖原始模型输出                 │
│  ⑥ 形成完整审计记录（谁、何时、改了什么、为什么）│
└─────────────────────────────────────────────┘
```

---

### 模块七：模型验证中心

#### 9.1 展示内容

**分类模型指标（边界识别）**
- 混淆矩阵（热力图）
- Precision / Recall / F1（总体+九类业态）
- 消融实验（逐一移除W1/W2/W3/W4）
- 阈值曲线（不同SportScore阈值下的性能变化）

**回归模型指标（SportShare）**
- MAE / RMSE / R²
- 分业态误差分布（箱线图）
- 预测区间覆盖率（实际值落在预测区间内的比例）

**性能指标**
- 单条识别时间
- 全量76,687条总运行时间
- 峰值内存占用
- 异常输入测试（空文本/特殊字符/超长文本/无效行业代码）

#### 9.2 支持功能

- 上传自定义测试集
- 选择模型版本进行对比
- 一键运行验证
- 导出测试报告（PDF）
- 查看错误案例

---

### 模块八：批次与版本管理

#### 10.1 每个批次保存的版本信息

| 版本类型 | 字段 | 示例 |
|----------|------|------|
| 数据版本 | `data_version` | v1.0（原始上传） |
| 模型版本 | `model_version` | v2.1.0 |
| 词典版本 | `dictionary_version` | DICT-20260801 |
| 代码映射版本 | `code_map_version` | CODE-2025 |
| 比重模型版本 | `share_model_version` | SHARE-XGBoost-v1 |
| 参数版本 | `param_version` | THRESHOLD=0.10 |
| 运行环境 | `runtime_env` | Python 3.11 + FastAPI 0.110 |
| 文件哈希 | `file_hash` | SHA256: a3f2b8... |

#### 10.2 批次对比功能

| 对比维度 | 说明 |
|----------|------|
| 新增企业 | 新批次有、旧批次无的企业 |
| 删除企业 | 旧批次有、新批次无的企业 |
| 业态变化 | 同一企业体育业态被重新分类 |
| SportScore变化 | 分数上升/下降超过阈值 |
| SportShare变化 | 比重变化超过5个百分点 |
| 区域规模变化 | 各市州规模增/减 |

---

### 模块九：报告与数据导出

#### 11.1 导出类型

| 序号 | 导出类型 | 格式 | 说明 |
|------|----------|------|------|
| 1 | 全量候选企业 | Excel | 含所有识别字段 |
| 2 | 跨界经营企业 | Excel | 仅跨界企业明细 |
| 3 | P1-P4复核任务 | Excel | 按优先级排列 |
| 4 | 企业证据报告 | PDF/Word | 单企业完整证据链 |
| 5 | 分业态规模 | Excel | 九类业态各自规模 |
| 6 | 分区域规模 | Excel | 21市州各自规模 |
| 7 | 模型验证报告 | PDF | 完整指标+图表 |
| 8 | 批次审计报告 | PDF | 操作记录+变更追踪 |
| 9 | 论文图表数据 | PNG/SVG | 高清图表 |

#### 11.2 导出文件元数据（必须携带）

每个导出文件必须包含：
- 数据批次号
- 模型版本
- 导出时间
- 统计口径（正式测算 / 代理估算 / 相对指数）
- 结果使用边界说明

---

## 四、技术架构升级

### 4.1 后端目录结构

```
backend/
├── api/                          # 路由层
│   ├── __init__.py
│   ├── data.py                   # 数据管理API
│   ├── recognition.py            # 边界识别API
│   ├── share.py                  # SportShare API（🆕）
│   ├── scale.py                  # 规模测算API（🆕）
│   ├── region.py                 # 区域分析API（🆕）
│   ├── review.py                 # 人工复核API（🆕）
│   ├── validation.py             # 模型验证API
│   ├── report.py                 # 报告导出API（🆕）
│   └── system.py                 # 系统管理API（🆕）
│
├── services/                     # 业务逻辑层
│   ├── __init__.py
│   ├── data_quality_service.py   # 数据质量检查（🆕）
│   ├── sport_score_service.py    # SportScore计算（升级）
│   ├── sport_share_service.py    # SportShare比重估计（🆕）
│   ├── scale_measure_service.py  # 产业规模测算（🆕）
│   ├── region_analysis_service.py# 区域空间分析（🆕）
│   ├── review_workflow_service.py# 复核工作流（🆕）
│   ├── report_service.py         # 报告生成（🆕）
│   ├── sport_recognition.py      # 已有（升级）
│   ├── industry_analysis.py      # 已有（升级）
│   ├── model_validate.py         # 已有（升级）
│   └── nlp_preprocess.py         # 已有（升级）
│
├── models/                       # 数据模型
│   ├── __init__.py
│   ├── database.py               # 数据库连接（升级为PostgreSQL）
│   ├── tables.py                 # SQLAlchemy表（大幅扩展）
│   └── schemas.py                # Pydantic入参出参（大幅扩展）
│
├── repositories/                 # 数据访问层（🆕）
│   ├── __init__.py
│   ├── enterprise_repo.py
│   ├── recognition_repo.py
│   ├── share_repo.py
│   ├── review_repo.py
│   └── batch_repo.py
│
├── tasks/                        # 异步任务（🆕）
│   ├── __init__.py
│   ├── batch_recognition_task.py
│   ├── report_generation_task.py
│   └── data_import_task.py
│
├── audit/                        # 审计日志（🆕）
│   ├── __init__.py
│   └── audit_logger.py
│
├── utils/                        # 工具函数
│   ├── __init__.py
│   ├── text_tokenizer.py         # 已有（升级）
│   ├── industry_code.py          # 已有（升级）
│   ├── data_cleaner.py           # 已有（升级）
│   ├── file_parser.py            # 已有（升级）
│   ├── geo_coder.py              # 地理编码（🆕）
│   └── security.py               # 安全工具（🆕）
│
├── migrations/                   # 数据库迁移（🆕）
└── config.py                     # 配置管理（升级）
```

### 4.2 数据库升级方案

#### 从SQLite迁移至PostgreSQL

**推荐PostgreSQL**，原因：
- 并发支持（SQLite不适合多用户Web系统）
- 全文搜索（PostgreSQL内置pg_trgm，支持中文分词索引）
- JSON字段（企业公开信息等半结构化数据）
- 地理坐标（PostGIS扩展，支持空间查询）
- 行级安全（RLS，支持多租户数据隔离）

#### 新增核心表

```sql
-- 企业基础信息（扩展）
CREATE TABLE enterprise (
    id SERIAL PRIMARY KEY,
    credit_code VARCHAR(50) UNIQUE,           -- 统一社会信用代码
    name VARCHAR(300) NOT NULL,               -- 企业详细名称
    region VARCHAR(100),                      -- 所在区域
    city VARCHAR(50),                         -- 市州
    district VARCHAR(50),                     -- 区县
    industry_code VARCHAR(20),                -- 行业代码
    industry_code_type VARCHAR(20),           -- direct/indirect/none
    main_business TEXT,                       -- 主要业务活动
    total_revenue DECIMAL(18,2),              -- 营业收入
    employee_count INTEGER,                   -- 从业人数
    total_assets DECIMAL(18,2),               -- 资产总额
    registered_capital DECIMAL(18,2),          -- 注册资本
    scale_level VARCHAR(20),                  -- 企业规模等级
    longitude DECIMAL(10,6),                  -- 经度
    latitude DECIMAL(10,6),                   -- 纬度
    batch_id INTEGER REFERENCES batch(id),
    data_version VARCHAR(20),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 业务线信息
CREATE TABLE enterprise_business (
    id SERIAL PRIMARY KEY,
    enterprise_id INTEGER REFERENCES enterprise(id),
    line_index INTEGER,                       -- 第几条业务线
    business_text TEXT,                       -- 业务描述
    is_sport BOOLEAN DEFAULT FALSE,           -- 是否体育业务
    sport_category VARCHAR(50),               -- 体育业态
    keywords TEXT[],                          -- 命中关键词
    score DECIMAL(3,2),                       -- 匹配得分
    created_at TIMESTAMP DEFAULT NOW()
);

-- 边界识别结果（升级）
CREATE TABLE recognition_result (
    id SERIAL PRIMARY KEY,
    enterprise_id INTEGER REFERENCES enterprise(id),
    credit_code VARCHAR(50),
    sport_category VARCHAR(50),               -- 体育业态
    is_sport BOOLEAN,
    is_crossover BOOLEAN,
    crossover_type VARCHAR(100),
    code_type VARCHAR(20),
    code_text_consistency VARCHAR(20),        -- 代码-文本一致性 🆕
    sport_score DECIMAL(5,4),                 -- 🆕
    w1_business_scope DECIMAL(5,4),
    w2_keyword_density DECIMAL(5,4),
    w3_code_weight DECIMAL(5,4),
    w4_category_coverage DECIMAL(5,4),
    confidence DECIMAL(5,4),
    total_business_lines INTEGER,
    sport_business_lines INTEGER,
    keywords TEXT[],
    model_version VARCHAR(20),
    batch_id INTEGER REFERENCES batch(id),
    created_at TIMESTAMP DEFAULT NOW()
);

-- SportShare比重结果（🆕 核心）
CREATE TABLE sport_share_result (
    id SERIAL PRIMARY KEY,
    enterprise_id INTEGER REFERENCES enterprise(id),
    model_share DECIMAL(5,4),                 -- 模型预测比重
    share_band VARCHAR(20),                   -- 比重档位
    lower_bound DECIMAL(5,4),                 -- 预测下限
    upper_bound DECIMAL(5,4),                 -- 预测上限
    confidence DECIMAL(5,4),
    main_factors TEXT[],                      -- 主要影响因素
    manual_share DECIMAL(5,4),                -- 人工核定比重
    is_manual_adjusted BOOLEAN DEFAULT FALSE,
    share_model_version VARCHAR(20),
    batch_id INTEGER REFERENCES batch(id),
    created_at TIMESTAMP DEFAULT NOW()
);

-- 企业规模字段（🆕）
CREATE TABLE enterprise_scale (
    id SERIAL PRIMARY KEY,
    enterprise_id INTEGER REFERENCES enterprise(id),
    scale_field_type VARCHAR(30),             -- revenue/employee/asset/capital
    scale_field_value DECIMAL(18,2),
    sport_scale DECIMAL(18,2),                -- 企业体育业务规模
    measurement_type VARCHAR(30),             -- formal/proxy/relative_index
    batch_id INTEGER REFERENCES batch(id),
    created_at TIMESTAMP DEFAULT NOW()
);

-- 区域规模结果（🆕）
CREATE TABLE regional_scale_result (
    id SERIAL PRIMARY KEY,
    region VARCHAR(100),                      -- 区域名称
    region_type VARCHAR(20),                  -- city/district
    total_enterprises INTEGER,
    sport_enterprises INTEGER,
    estimated_scale DECIMAL(18,2),
    dominant_category VARCHAR(50),
    crossover_rate DECIMAL(5,4),
    new_candidates INTEGER,                   -- 相比传统方法新增候选
    high_risk_review_count INTEGER,           -- 高风险复核数
    batch_id INTEGER REFERENCES batch(id),
    created_at TIMESTAMP DEFAULT NOW()
);

-- 人工复核任务（🆕）
CREATE TABLE review_task (
    id SERIAL PRIMARY KEY,
    enterprise_id INTEGER REFERENCES enterprise(id),
    priority VARCHAR(5),                      -- P1/P2/P3/P4
    status VARCHAR(20) DEFAULT 'pending',     -- pending/assigned/reviewing/disputed/confirmed/info_insufficient/locked
    assigned_to_a INTEGER REFERENCES user(id),-- 复核员A
    assigned_to_b INTEGER REFERENCES user(id),-- 复核员B
    arbitration_id INTEGER REFERENCES user(id),-- 仲裁员
    batch_id INTEGER REFERENCES batch(id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 复核意见记录（🆕）
CREATE TABLE review_record (
    id SERIAL PRIMARY KEY,
    review_task_id INTEGER REFERENCES review_task(id),
    reviewer_id INTEGER REFERENCES user(id),
    sport_attribute VARCHAR(20),              -- yes/no/uncertain
    sport_category_override VARCHAR(50),      -- 修正后的体育业态
    sport_share_override DECIMAL(5,4),        -- 修正后的比重
    reason TEXT,                              -- 判断理由
    evidence_attachment TEXT,                 -- 证据附件路径
    need_further_investigation BOOLEAN DEFAULT FALSE,
    reviewed_at TIMESTAMP DEFAULT NOW()
);

-- 仲裁记录（🆕）
CREATE TABLE arbitration_record (
    id SERIAL PRIMARY KEY,
    review_task_id INTEGER REFERENCES review_task(id),
    arbiter_id INTEGER REFERENCES user(id),
    reviewer_a_opinion TEXT,                  -- A方意见
    reviewer_b_opinion TEXT,                  -- B方意见
    final_decision TEXT,                      -- 最终裁决
    reason TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 模型版本（🆕）
CREATE TABLE model_version (
    id SERIAL PRIMARY KEY,
    model_type VARCHAR(50),                   -- recognition/share/scale
    version VARCHAR(20),
    description TEXT,
    parameters JSONB,
    metrics JSONB,                            -- 模型评估指标
    file_path VARCHAR(500),
    is_active BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 词典版本（🆕）
CREATE TABLE dictionary_version (
    id SERIAL PRIMARY KEY,
    version VARCHAR(20),
    description TEXT,
    keyword_count INTEGER,
    category_count INTEGER,
    file_path VARCHAR(500),
    is_active BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 数据批次（🆕 升级）
CREATE TABLE batch (
    id SERIAL PRIMARY KEY,
    batch_number VARCHAR(50) UNIQUE,          -- BATCH-YYYYMMDD-NNN
    data_mode VARCHAR(10) DEFAULT 'formal',   -- formal/demo
    data_version VARCHAR(20),
    model_version VARCHAR(20),
    dictionary_version VARCHAR(20),
    code_map_version VARCHAR(20),
    share_model_version VARCHAR(20),
    param_version VARCHAR(50),
    runtime_env TEXT,
    file_hash VARCHAR(64),                    -- SHA256
    file_name VARCHAR(300),
    total_rows INTEGER,
    operator_id INTEGER REFERENCES user(id),
    status VARCHAR(20),                       -- importing/processing/completed/locked/archived
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 操作审计日志（🆕）
CREATE TABLE operation_log (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES user(id),
    action VARCHAR(50),                       -- CREATE/UPDATE/DELETE/EXPORT/REVIEW
    target_type VARCHAR(50),
    target_id INTEGER,
    detail JSONB,
    ip_address VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW()
);

-- 报告导出记录（🆕）
CREATE TABLE report_export (
    id SERIAL PRIMARY KEY,
    export_type VARCHAR(50),
    batch_id INTEGER REFERENCES batch(id),
    user_id INTEGER REFERENCES user(id),
    file_path VARCHAR(500),
    file_format VARCHAR(20),
    file_size_bytes INTEGER,
    statistical_scope VARCHAR(50),           -- formal/proxy/relative_index
    usage_boundary TEXT,                      -- 结果使用边界
    exported_at TIMESTAMP DEFAULT NOW()
);

-- 用户表（🆕）
CREATE TABLE "user" (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    display_name VARCHAR(100),
    role VARCHAR(30) NOT NULL,               -- admin/data_admin/model_admin/reviewer/arbiter/viewer
    is_active BOOLEAN DEFAULT TRUE,
    last_login TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### 4.3 前端页面结构

```
前端首页（导航布局）
├── 工作台 Dashboard
│   ├── 批次概览卡片
│   ├── 待处理复核数
│   ├── 最近批次列表
│   └── 快捷操作入口
│
├── 数据管理 DataCenter
│   ├── 文件上传（拖拽+模板下载+批量导入）
│   ├── 数据质量报告
│   └── 批次管理（批次列表/对比/归档）
│
├── 智能识别 Recognition
│   ├── 单条识别（输入查询）
│   ├── 批量识别（触发全量处理）
│   ├── 候选企业列表（分页/筛选/排序）
│   └── 企业详情（完整证据链展示）
│
├── 比重测算 SportShare  🆕
│   ├── SportShare结果列表
│   ├── 人工校准（修改比重+记录理由）
│   └── 误差分析（分业态/分档位MAE）
│
├── 规模分析 ScaleAnalysis
│   ├── 总体规模面板
│   ├── 分业态规模（表格+图表）
│   ├── 区域分析（地图+下钻）
│   └── 传统方法对比（代码法 vs SportFusion）
│
├── 人工复核 ReviewWorkbench  🆕
│   ├── 任务池（所有待分配任务）
│   ├── 我的任务（当前登录用户）
│   ├── 仲裁中心（分歧任务）
│   └── 动态名录（已锁定企业）
│
├── 模型验证 ModelValidation
│   ├── 分类指标（混淆矩阵/PR曲线）
│   ├── 回归指标（MAE/RMSE/R²）
│   ├── 消融实验
│   ├── 版本对比
│   └── 错误案例分析
│
├── 报告中心 ReportCenter  🆕
│   ├── 报告模板选择
│   ├── 一键生成
│   ├── 导出历史
│   └── 下载/预览
│
└── 系统管理 SystemAdmin  🆕
    ├── 用户管理
    ├── 角色权限
    ├── 模型版本管理
    ├── 词典版本管理
    ├── 操作日志
    └── 系统配置
```

### 4.4 权限与安全

#### 角色定义（6角色）

| 角色 | 权限范围 |
|------|----------|
| **系统管理员** | 全部权限：用户管理、角色分配、系统配置、数据删除 |
| **数据管理员** | 数据上传/导入/清洗/导出、批次管理、词典管理 |
| **模型管理员** | 模型版本管理、参数配置、模型验证、阈值调整 |
| **统计复核人员** | 复核任务执行、复核意见提交、比重人工校准 |
| **仲裁人员** | 分歧仲裁、最终裁定、审计记录查看 |
| **只读分析人员** | 查看所有结果、下载报告、不可修改任何数据 |

#### 安全措施

- JWT Token 登录认证（access_token + refresh_token）
- RBAC 角色权限控制（中间件拦截）
- 操作日志（所有写操作记录到 `operation_log`）
- 文件访问控制（用户只能访问授权批次的文件）
- 企业信息脱敏（演示模式下隐藏统一社会信用代码和联系方式）
- 导出审批（P1/P2数据导出需管理员审批）
- CORS 白名单
- 数据库定期备份
- 正式环境与演示环境数据物理隔离

---

## 五、系统展示优化

### 5.1 视觉风格定位

**专业统计工作台**，非炫技大屏。设计原则：
- 以白色/浅灰为主色调，蓝色为功能色
- 信息密度适中，避免过度留白
- 表格为主要展示载体，图表为辅助
- 操作路径清晰，每步有明确反馈

### 5.2 完整案例展示链（论文配图）

#### 场景一：数据导入

展示：上传文件 → 字段匹配 → 数据质量 → 创建批次

#### 场景二：全量识别

展示：76,687家企业 → 8,950家候选 → 934家补充识别 → 九类业态分布

#### 场景三：单企业证据下钻

展示：行业代码 → 业务文本 → 业务线拆分 → 关键词 → W1-W4 → SportScore → SportShare → 跨界类型

#### 场景四：人工复核

展示：模型结论 → 风险等级 → 人工结论 → 复核依据 → 仲裁状态

#### 场景五：规模与区域分析

展示：传统法与融合测算法差异 → 分业态规模 → 市州地图 → 增量规模来源

---

## 六、实施路径

### 6.1 分阶段实施计划

| 阶段 | 内容 | 预计工期 | 优先级 |
|------|------|----------|--------|
| **Phase 1** | 数据库迁移（SQLite→PostgreSQL）+ 核心表创建 | 1周 | 🔴 必须 |
| **Phase 2** | SportShare比重测算模块（模型+API+页面） | 2周 | 🔴 必须 |
| **Phase 3** | 产业规模测算模块（多字段+口径标注） | 1周 | 🔴 必须 |
| **Phase 4** | 人工复核工作台（任务分配+双人复核+仲裁） | 2周 | 🔴 必须 |
| **Phase 5** | 批次版本管理 + 正式/演示数据隔离 | 1周 | 🟡 重要 |
| **Phase 6** | 区域地图（四川21市州GeoJSON）+ 下钻交互 | 1周 | 🟡 重要 |
| **Phase 7** | 模型验证中心升级 | 1周 | 🟡 重要 |
| **Phase 8** | 报告自动导出（Word/PDF/Excel/JSON） | 1周 | 🟡 重要 |
| **Phase 9** | 角色权限 + 安全加固 | 1周 | 🟡 重要 |

### 6.2 论文展示优先级

对于比赛论文配图，按重要性排序：

1. 🥇 **SportShare结果页** — 核心算法创新的可视化
2. 🥈 **规模测算对比** — 传统方法 vs SportFusion的差异
3. 🥉 **人工复核工作台** — P1-P4机制落地
4. **单企业证据下钻** — 方法可解释性
5. **区域地图+下钻** — 应用价值展示

---

## 七、关键技术决策

| 决策项 | V1.0 | V2.0建议 | 理由 |
|--------|------|----------|------|
| 数据库 | SQLite | PostgreSQL | 并发+全文搜索+地理扩展 |
| 比重模型 | W1-W4规则加权 | XGBoost回归 | 可拟合非线性 + 特征重要性可解释 |
| 前端框架 | Vue3 + Element Plus | 保持不变 | 现有基础好，扩展即可 |
| 图表库 | ECharts | 保持不变 | 支持四川地图GeoJSON |
| 异步任务 | 同步 | Celery / FastAPI BackgroundTasks | 全量识别需异步处理 |
| 缓存 | 内存字典 | Redis | 多用户场景 |
| 部署 | 本地启动脚本 | Docker Compose | 环境一致性 |

---

## 附录

### A. 现有代码复用评估

| 模块 | 复用率 | 说明 |
|------|--------|------|
| `text_tokenizer.py` | 90% | 保留核心分词+关键词匹配，微调词典 |
| `sport_recognition.py` | 70% | 保留W1-W4计算逻辑，升级为SportScore |
| `industry_analysis.py` | 60% | 保留聚合逻辑，升级为PostGIS空间查询 |
| `data_cleaner.py` | 80% | 保留清洗逻辑，增加更多检查项 |
| 前端图表组件 | 100% | 全部保留复用 |
| 前端页面 | 40% | DataManage页保留升级，其余重构 |
| Pinia Store | 60% | 保留结构，扩展数据模型 |

### B. 数据库迁移注意事项

- SQLite → PostgreSQL：注意自增主键语法差异（AUTOINCREMENT → SERIAL）
- 日期类型：DATETIME → TIMESTAMP
- JSON类型：TEXT → JSONB（支持索引和查询）
- 布尔类型：INTEGER(0/1) → BOOLEAN
- 为已有数据编写完整迁移脚本，保证数据不丢失

---

> **文档结束**
>
> 本方案覆盖了系统定位升级、9大模块重构、技术架构升级、权限安全、展示优化和分阶段实施路径。核心新增模块为SportShare比重估计、产业规模测算中心、人工复核工作台和批次版本管理，这四项是实现"完整统计流程平台"定位的关键。
