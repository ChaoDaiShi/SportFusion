# 体融识界 · SportFusion

> 基于 NLP 文本识别与多维度加权的多元经营企业体育业务边界识别与产业规模测算可视化平台

---

## 项目简介

本平台面向体育产业统计与监测场景，针对多元经营企业（即同时从事体育与非体育业务的企业）的体育业务边界模糊、传统行业代码法存在偏差等问题，提出了一套基于 **NLP 文本识别 + 四维特征加权** 的企业体育业务边界识别方法，并实现了体育产业规模的精准测算与全景可视化。

### 核心能力

| 模块 | 说明 |
|------|------|
| **数据管理** | Excel/CSV 企业数据上传、数据清洗、NLP 文本预处理（分词、关键词提取、体育标签标注） |
| **企业业务识别** | 单条/批量企业体育业务边界识别，四维特征权重（业务范围 W1=0.40、关键词密度 W2=0.25、行业代码权重 W3=0.25、业态覆盖度 W4=0.10） |
| **测算对比验证** | 传统行业代码统计法 vs NLP 模型测算法的对比验证，含准确率/精确率/召回率/MAE 指标 |
| **产业全景大屏** | ECharts 可视化大屏（饼图、柱状图、热力地图、雷达图、漏斗图、矩形树图、趋势折线图），产业集中度 CRn/HHI/Gini 分析 |
| **报表导出** | 标准化数据集、体育企业子集、特征数据集（CSV/JSON 格式）导出 |
| **智能助手** | 基于 DeepSeek AI 的流式对话助手，三层防幻觉机制，仅回答项目相关问题 |

---

## 技术栈

### 前端
- **Vue 3.5** — Composition API + `<script setup>`
- **Element Plus 2.9** — UI 组件库
- **ECharts 5.5** — 数据可视化
- **Pinia 2.3** — 状态管理
- **Vue Router 4.5** — 路由
- **Vite 6** — 构建工具
- **Axios 1.7** — HTTP 请求

### 后端
- **FastAPI 0.115** — Web 框架
- **SQLAlchemy 2.0** — ORM
- **SQLite** — 数据库
- **jieba 0.42** — 中文分词
- **scikit-learn 1.6** — 机器学习指标
- **pandas 2.2** — 数据处理
- **OpenAI SDK** — DeepSeek AI 接入

### 部署
- **Nginx** — 静态文件服务 + 反向代理 + SSE 流式支持
- **Uvicorn** — ASGI 服务器
- **宝塔面板** / **Systemd** — 进程管理

---

## 项目结构

```
sports-industry/
├── backend/                    # FastAPI 后端
│   ├── main.py                 # 应用入口
│   ├── requirements.txt        # Python 依赖
│   ├── .env                    # 环境变量（API Key 等）
│   ├── sports_industry.db      # SQLite 数据库
│   ├── routers/                # API 路由
│   │   ├── data_preprocess.py  # 数据上传/清洗/预处理
│   │   ├── enterprise_recognition.py  # 企业业务识别
│   │   ├── output_calc.py      # 产值测算
│   │   ├── chart_data.py       # 图表数据
│   │   ├── model_validate.py   # 模型校验
│   │   └── chat.py             # AI 智能助手 (SSE 流式)
│   ├── services/               # 业务逻辑
│   │   ├── sport_recognition.py    # 识别核心算法
│   │   ├── industry_analysis.py    # 产业分析
│   │   ├── output_calc.py          # 产值计算
│   │   ├── nlp_preprocess.py       # NLP 预处理
│   │   ├── model_validate.py       # 模型验证
│   │   └── chat_service.py         # DeepSeek AI 服务
│   ├── models/                 # ORM 模型 + Pydantic Schema
│   └── utils/                  # 工具函数
│
├── frontend/                   # Vue 3 前端
│   ├── src/
│   │   ├── App.vue             # 主布局（侧边栏 + 路由视图）
│   │   ├── views/              # 页面组件
│   │   │   ├── DataManage.vue          # 数据管理
│   │   │   ├── EnterpriseRecognition.vue  # 企业识别
│   │   │   ├── MeasureCompare.vue      # 测算对比
│   │   │   ├── IndustryDashboard.vue   # 产业大屏
│   │   │   └── ReportExport.vue        # 报表导出
│   │   ├── components/         # 可复用组件
│   │   │   ├── ChatAssistant.vue   # AI 智能助手（流式对话）
│   │   │   ├── BarChart.vue / PieChart.vue / LineChart.vue
│   │   │   ├── MapHeatmap.vue / RadarChart.vue / GaugeChart.vue
│   │   │   ├── ScatterChart.vue / FunnelChart.vue / TreemapChart.vue
│   │   │   └── DataTable.vue / StatCard.vue
│   │   ├── api/                # API 请求模块
│   │   ├── store/              # Pinia 状态管理
│   │   ├── router/             # Vue Router 路由
│   │   └── utils/              # 工具（格式化、ECharts 封装）
│   ├── vite.config.js          # Vite 配置（含生产分包策略）
│   └── package.json
│
├── data/                       # 原始数据文件
├── deploy/                     # 部署配置
│   ├── nginx/                  # Nginx 站点配置
│   ├── systemd/                # 后端 Service
│   ├── deploy.sh               # 一键部署脚本
│   ├── package.ps1             # 本地打包脚本
│   ├── .env.production         # 生产环境变量
│   ├── DEPLOY.md               # 命令行部署指南
│   └── DEPLOY_BT.md            # 宝塔面板部署指南
│
├── sports-industry-analysis/   # 产业分析报告 (HTML)
├── start_backend.bat           # 后端开发启动脚本 (Windows)
├── start_frontend.bat          # 前端开发启动脚本 (Windows)
├── run_all.bat                 # 一键启动全部服务 (Windows)
└── README.md
```

---

## 快速开始（本地开发）

### 环境要求
- **Python** 3.10+
- **Node.js** 18+
- **npm** 9+

### 1. 克隆项目
```bash
git clone <repo-url>
cd sports-industry
```

### 2. 启动后端
```bash
cd backend

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp ../deploy/.env.production .env
# 编辑 .env，填入 DEEPSEEK_API_KEY

# 初始化数据库
python -c "from models.database import engine, Base; from models.tables import *; Base.metadata.create_all(bind=engine)"

# 启动
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

后端运行在 `http://localhost:8000`，API 文档在 `http://localhost:8000/docs`

### 3. 启动前端
```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

前端运行在 `http://localhost:5173`，自动代理 `/api` 到后端 `8000` 端口。

### 4. 一键启动 (Windows)
```cmd
run_all.bat
```

---

## 部署到生产环境

### 宝塔面板（推荐）

详见 [deploy/DEPLOY_BT.md](deploy/DEPLOY_BT.md)

核心步骤：
1. 宝塔创建 Python 项目 → FastAPI → 端口 8000
2. 终端构建前端：`cd frontend && npm install && npm run build`
3. 宝塔创建静态站点 → 根目录指向 `frontend/dist/`
4. 添加反向代理：`/api/` → `127.0.0.1:8000`
5. 配置 SSE 支持：`proxy_buffering off`

### 命令行部署

详见 [deploy/DEPLOY.md](deploy/DEPLOY.md)

```bash
cd /tmp && tar -xzf sports-industry-deploy.tar.gz
chmod +x deploy/deploy.sh && sudo ./deploy/deploy.sh
```

---

## API 接口

| 端点 | 说明 |
|------|------|
| `GET /api/data/preview/{file_id}` | 数据预览（分页） |
| `POST /api/data/upload` | 文件上传 |
| `POST /api/data/clean/{file_id}` | 数据清洗 |
| `POST /api/data/preprocess/{file_id}` | NLP 预处理 |
| `POST /api/recognition/single` | 单条企业识别 |
| `POST /api/recognition/batch` | 批量企业识别 |
| `POST /api/measure/single` | 单条产值测算 |
| `POST /api/measure/batch` | 批量产值测算 |
| `GET /api/chart/pie` | 饼图数据 |
| `GET /api/chart/map` | 热力地图数据 |
| `GET /api/chart/dashboard` | 大屏综合数据 |
| `GET /api/validate/summary` | 模型校验指标 |
| `GET /api/monitoring/overview` | 统计监测快照与数据来源 |
| `GET /api/monitoring/risks` | 风险事件列表 |
| `POST /api/assistant/stream` | 基于当前监测上下文的研判问答 |
| `GET /api/chat/presets` | 智能助手预设问题 |
| `POST /api/chat/stream` | 流式 AI 对话 (SSE) |

所有接口返回统一格式：`{"code": 200, "message": "...", "data": {...}}`

---

## 比赛演示入口

- `/monitoring`：统计监测驾驶舱
- `/risks`：风险事件中心
- `/assistant`：智能决策问答
- `/model-evaluation`：模型性能评估

## 数据状态

系统按真实数据、历史快照、演示数据保障三种模式运行。页面顶部和导出确认框会显示当前模式；不同模式的数据不会混合到同一份结果中。

智能决策问答会附带数据版本、模型版本和引用指标。未配置模型服务时，系统使用同一监测快照生成规则研判，并在页面中明确提示。部署 SSE 接口时仍需在 Nginx 中关闭 `proxy_buffering`。

---

## 成果文件

| 文件 | 说明 |
|------|------|
| `体融识界·SportFusion——基于NLP…docx` | 完整研究报告 |
| `体融识界·SportFusion——算法技术文档.docx` | 算法技术文档 |
| `体育产业大数据分析.pptx` | 项目展示 PPT |
| `sports-industry-analysis/` | 产业分析 HTML 报告 |

---

## License

本项目仅用于学术研究与竞赛目的。
