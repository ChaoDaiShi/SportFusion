# 宝塔面板部署指南

## 一、项目结构

确认服务器上项目目录（以下以 `/www/wwwroot/sports-industry` 为例）：

```
/www/wwwroot/sports-industry/
├── backend/          # FastAPI 后端
│   ├── main.py
│   ├── requirements.txt
│   ├── .env
│   └── .venv/        # Python 虚拟环境（部署时创建）
├── frontend/         # Vue 前端
│   └── dist/         # 构建产物（部署时生成）
├── data/             # Excel 数据文件
└── deploy/           # 部署配置
    ├── .env.production
    └── nginx/
        └── sports-industry.conf
```

---

## 二、后端部署（4 步）

### Step 1: 创建 Python 项目

在宝塔面板 → **网站** → **Python项目** → 点击 **添加Python项目**

填写：

| 选项 | 值 |
|------|-----|
| 项目名称 | `sports-backend` |
| Python版本 | 选择已安装的版本（如 3.10+） |
| 项目路径 | `/www/wwwroot/sports-industry/backend` |
| 启动文件 | `main.py` |
| 运行端口 | `8000` |
| 框架 | `FastAPI` |
| 启动方式 | `uvicorn` |

**启动命令**（在下方命令框中修改为）：
```
.venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000 --workers 4
```

点击 **确定**，宝塔会自动创建虚拟环境并尝试启动。

### Step 2: 安装依赖

在宝塔面板 → **网站** → **Python项目** → 找到 `sports-backend` → 点击 **进入**

切到 **模块** 标签页，确认 `requirements.txt` 中的依赖已全部安装。如果没有：

在服务器终端中：
```bash
cd /www/wwwroot/sports-industry/backend
source .venv/bin/activate
pip install -r requirements.txt
```

或直接在宝塔 Python 项目面板的 **终端** 按钮中执行。

### Step 3: 配置环境变量

在宝塔 Python 项目面板 → 找到 `sports-backend` → 点击 **配置**

在 **环境变量** 区域添加：

```
DEEPSEEK_API_KEY=sk-你的真实key
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
```

或者直接将 `deploy/.env.production` 复制到 backend 目录：
```bash
cp /www/wwwroot/sports-industry/deploy/.env.production /www/wwwroot/sports-industry/backend/.env
```

### Step 4: 初始化数据库

在宝塔 Python 项目面板 → **终端**，执行：
```bash
python -c "
from models.database import engine, Base
from models.tables import *
Base.metadata.create_all(bind=engine)
print('数据库表创建成功')
"
```

回到项目面板，点击 **重启** 按钮。

验证：`http://服务器IP:8000/docs` 能打开 API 文档 = 后端 OK。

---

## 三、前端部署（3 步）

### Step 1: 安装 Node.js（如果还没装）

宝塔面板 → **软件商店** → 搜索 `Node.js` → 安装 → 选择 v18.x

### Step 2: 构建前端

在服务器终端中：
```bash
cd /www/wwwroot/sports-industry/frontend
npm install
npm run build
# 完成后在 dist/ 目录生成静态文件
```

### Step 3: 创建纯静态站点

宝塔面板 → **网站** → **添加站点**

| 选项 | 值 |
|------|-----|
| 域名 | 服务器IP 或 你的域名 |
| 根目录 | `/www/wwwroot/sports-industry/frontend/dist` |
| 网站类型 | `静态网站`（或 PHP，都会选） |
| PHP版本 | `纯静态` |

点击 **确定**。

---

## 四、配置反向代理（关键步骤）

在宝塔面板 → **网站** → 找到刚创建的站点 → 点击 **设置**

### 4.1 URL 重写（SPA 路由支持）

切到 **伪静态** 标签，粘贴以下内容并保存：

```nginx
# SPA 路由回退 — 非 API 路径、非静态文件 → index.html
location / {
    try_files $uri $uri/ /index.html;
}
```

### 4.2 反向代理（API 转发到后端）

切到 **反向代理** 标签 → 点击 **添加反向代理**

| 选项 | 值 |
|------|-----|
| 代理名称 | `api-proxy` |
| 目标URL | `http://127.0.0.1:8000` |
| 发送域名 | `$host` |
| 内容替换 | 留空 |

**高级配置**（点开高级选项）：

```
# SSE 流式支持（智能助手需要，非常重要！）
proxy_buffering off;
proxy_cache off;
proxy_read_timeout 120s;
proxy_send_timeout 120s;
```

### 4.3 补充配置文件（手动添加 SSE 支持和安全头）

宝塔 → 网站 → 设置 → **配置文件**，在 `server {}` 块内，找到反向代理自动生成的 `location /` 块附近，**确认以下内容存在**：

```nginx
# 在 location / 块中（SPA路由）
location / {
    try_files $uri $uri/ /index.html;
}

# API 反向代理（宝塔会自动生成类似配置，确认包含以下内容）
location ^~ /api/ {
    proxy_pass http://127.0.0.1:8000/api/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;

    # SSE 流式支持（智能助手必需）
    proxy_buffering off;
    proxy_cache off;
    proxy_read_timeout 120s;
    proxy_send_timeout 120s;
}

# 静态资源缓存
location /assets/ {
    expires 1y;
    add_header Cache-Control "public, immutable";
}
```

修改后 → 点击 **保存** → 宝塔会自动重载 Nginx。

---

## 五、开通端口

宝塔面板 → **安全** → 添加端口规则：

| 端口 | 说明 |
|------|------|
| 80 | HTTP Web |
| 443 | HTTPS（可选） |
| 8000 | 后端 API（调试用，生产建议关闭） |

**腾讯云轻量服务器防火墙也要同步放行** → 腾讯云控制台 → 轻量服务器 → 防火墙 → 添加 80/443。

---

## 六、验证部署

### 6.1 后端
```bash
# 浏览器访问
http://你的IP:8000/docs        # API文档
http://你的IP/api/chat/presets # 智能助手预设问题
```

### 6.2 前端
```bash
# 浏览器访问
http://你的IP/
# 应看到完整的平台界面，左下角有"小融"吉祥物
```

### 6.3 功能测试

1. 上传 Excel → 数据管理页面上传测试文件
2. 企业识别 → 单条/批量识别功能
3. 产业大屏 → 图表正常加载
4. 智能助手 → 点击左下角吉祥物 → 流式对话

---

## 七、HTTPS（可选）

宝塔面板 → 网站 → 设置 → **SSL** → 选择 **Let's Encrypt** → 勾选域名 → 申请。

---

## 八、常见问题

| 问题 | 解决 |
|------|------|
| 后端启动失败 | 宝塔 Python 项目面板看日志；检查 `.env` 是否配置 |
| 前端 502 | 确认后端正常运行 → `http://127.0.0.1:8000/docs` |
| 智能助手无响应 | 检查 `proxy_buffering off` 是否在 Nginx 配置中 |
| 页面刷新后 404 | 检查伪静态规则 `try_files` 是否生效 |
| 上传失败 | 初始化数据库表（见二-Step 4）|
| 图表不显示 | 确认 echarts 版本为 5.x（package.json 中检查）|
