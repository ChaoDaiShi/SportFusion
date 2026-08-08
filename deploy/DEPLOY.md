# 体育产业测算平台 — 腾讯云轻量服务器部署指南

## 架构概览

```
浏览器
  │
  ▼
┌────────────────────────────────────────┐
│  Nginx (:80)                           │
│  ├─ /          → frontend/dist/ (静态)  │
│  ├─ /api/*     → 127.0.0.1:8000 (代理) │
│  └─ /docs      → 127.0.0.1:8000 (API文档)│
└────────────┬───────────────────────────┘
             │
             ▼
┌────────────────────────────────────────┐
│  Uvicorn (systemd)                     │
│  FastAPI :8000                         │
│  ├─ /api/data/*     数据管理            │
│  ├─ /api/recognition/*  企业识别        │
│  ├─ /api/measure/*   产值测算           │
│  ├─ /api/chart/*     图表数据           │
│  ├─ /api/validate/*  模型校验           │
│  └─ /api/chat/*      智能助手(SSE流式)   │
└────────────┬───────────────────────────┘
             │
             ▼
┌────────────────────────────────────────┐
│  SQLite (sports_industry.db)           │
└────────────────────────────────────────┘
```

---

## 前置要求

### 服务器配置建议

| 项目 | 最低配置 | 推荐配置 |
|------|---------|---------|
| CPU | 2 核 | 4 核 |
| 内存 | 2 GB | 4 GB |
| 系统 | Ubuntu 20.04/22.04 | Ubuntu 22.04 |
| 磁盘 | 20 GB | 40 GB+ |
| 带宽 | 3 Mbps | 5 Mbps+ |

### 需要的腾讯云服务

1. **轻量应用服务器** — 选择 Ubuntu 22.04 镜像
2. **防火墙规则** — 开放 80 (HTTP)、443 (HTTPS)、22 (SSH) 端口
3. **(可选) 域名** — 并配置 DNS 解析到服务器 IP

---

## 部署方式一：一键脚本部署（推荐）

### 1. 上传项目到服务器

```bash
# 在本地打包项目（不含 node_modules、.venv、.uploads）
cd f:/比赛/大数据要素分析
tar --exclude='frontend/node_modules' \
    --exclude='backend/.venv' \
    --exclude='backend/__pycache__' \
    --exclude='.uploads' \
    --exclude='*.zip' \
    --exclude='项目 (2)*' \
    -czf deploy-package.tar.gz \
    backend/ frontend/ deploy/ data/

# 上传到服务器
scp deploy-package.tar.gz root@YOUR_SERVER_IP:/tmp/
```

### 2. 登录服务器并部署

```bash
ssh root@YOUR_SERVER_IP

# 解压
cd /tmp
tar -xzf deploy-package.tar.gz
mkdir -p /opt/sports-industry

# 运行部署脚本
cd /tmp
chmod +x deploy/deploy.sh
sudo ./deploy/deploy.sh
```

---

## 部署方式二：分步手动部署

### Step 1: 基础环境

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装基础工具
sudo apt install -y nginx python3 python3-pip python3-venv curl git

# 安装 Node.js 18.x
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs

# 验证
node --version   # v18.x
python3 --version # 3.10+
nginx -v
```

### Step 2: 部署项目

```bash
# 创建目录
sudo mkdir -p /opt/sports-industry
sudo chown $USER:$USER /opt/sports-industry

# 上传/解压项目文件到 /opt/sports-industry/
# (包含 backend/ frontend/ data/ deploy/ 四个目录)

# 创建上传目录
mkdir -p /opt/sports-industry/.uploads
```

### Step 3: 配置后端

```bash
cd /opt/sports-industry/backend

# 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate

# 安装依赖
pip install --upgrade pip
pip install -r requirements.txt

# 配置生产环境变量
cp ../deploy/.env.production .env
# 编辑 .env，修改 DEEPSEEK_API_KEY 等实际值
nano .env

# 初始化数据库
python -c "
from models.database import engine, Base
from models.tables import *
Base.metadata.create_all(bind=engine)
print('数据库表初始化完成')
"

# 测试启动
.venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000 &
# Ctrl+C 停止测试
```

### Step 4: 构建前端

```bash
cd /opt/sports-industry/frontend

npm install
npm run build
# 输出: dist/ 目录

ls -la dist/
# index.html  assets/  ...
```

### Step 5: 配置 Nginx

```bash
# 安装站点配置
sudo cp /opt/sports-industry/deploy/nginx/sports-industry.conf \
    /etc/nginx/sites-available/sports-industry

# 编辑配置（设置 server_name 为你的域名）
sudo nano /etc/nginx/sites-available/sports-industry

# 启用站点
sudo rm -f /etc/nginx/sites-enabled/default
sudo ln -s /etc/nginx/sites-available/sports-industry /etc/nginx/sites-enabled/

# 检查配置
sudo nginx -t

# 重载
sudo systemctl reload nginx
```

### Step 6: 配置后端服务

```bash
# 安装 systemd 服务
sudo cp /opt/sports-industry/deploy/systemd/sports-backend.service \
    /etc/systemd/system/

# 启动 + 开机自启
sudo systemctl daemon-reload
sudo systemctl enable sports-backend
sudo systemctl start sports-backend

# 检查状态
sudo systemctl status sports-backend
```

---

## 验证部署

```bash
# 1. 检查 Nginx
curl -I http://localhost/
# 应返回 200 OK

# 2. 检查 API
curl http://localhost/api/
# 应返回: {"message":"体育产业规模测算可视化平台 API",...}

# 3. 检查后端服务
sudo systemctl status sports-backend
# 应显示 active (running)

# 4. 检查智能助手预设
curl http://localhost/api/chat/presets
# 应返回预设问题列表

# 5. 浏览器访问
# http://YOUR_SERVER_IP
```

---

## 日常运维

### 查看日志

```bash
# 后端日志
sudo journalctl -u sports-backend -f

# Nginx 访问日志
sudo tail -f /var/log/nginx/sports-industry-access.log

# Nginx 错误日志
sudo tail -f /var/log/nginx/sports-industry-error.log
```

### 更新代码

```bash
# 1. 上传新代码
cd /opt/sports-industry

# 2. 更新前端
cd frontend
npm install
npm run build

# 3. 更新后端
cd ../backend
source .venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart sports-backend

# 4. 重载 Nginx（如果配置有改动）
sudo nginx -t && sudo systemctl reload nginx
```

### 数据库管理

```bash
# 备份 SQLite 数据库
cp /opt/sports-industry/backend/sports_industry.db \
   /opt/backups/sports_industry_$(date +%Y%m%d).db

# 恢复
cp /opt/backups/sports_industry_20260101.db \
   /opt/sports-industry/backend/sports_industry.db
sudo systemctl restart sports-backend
```

---

## 配置 HTTPS（推荐）

```bash
# 1. 确保域名 DNS 已解析到服务器 IP
# 2. 修改 Nginx 配置中的 server_name
sudo nano /etc/nginx/sites-available/sports-industry
# server_name your-domain.com;

# 3. 申请证书
sudo certbot --nginx -d your-domain.com

# 4. 证书会自动续期（certbot timer）
sudo systemctl status certbot.timer
```

---

## 故障排查

### 502 Bad Gateway

```bash
# 后端可能未启动
sudo systemctl status sports-backend
sudo systemctl restart sports-backend
```

### 前端页面空白

```bash
# 检查 dist 目录是否存在
ls /opt/sports-industry/frontend/dist/
# 如不存在，重新构建
cd /opt/sports-industry/frontend && npm run build
```

### 上传文件 500 错误

```bash
# 检查数据库表是否存在
cd /opt/sports-industry/backend
.venv/bin/python -c "
from models.database import engine, Base
from models.tables import *
Base.metadata.create_all(bind=engine)
"
```

### 智能助手无响应

```bash
# 检查 DEEPSEEK_API_KEY 配置
cat /opt/sports-industry/backend/.env | grep DEEPSEEK

# 检查后端日志
sudo journalctl -u sports-backend -f | grep -i error
```

---

## 安全建议

1. ✅ 使用 HTTPS (Let's Encrypt 免费证书)
2. ✅ 配置防火墙: `sudo ufw allow 22 && sudo ufw allow 80 && sudo ufw allow 443 && sudo ufw enable`
3. ✅ 定期备份数据库
4. ✅ 定期更新系统: `sudo apt update && sudo apt upgrade`
5. ✅ 不要将 `.env` 中的 API Key 提交到 Git
6. ✅ 建议开启腾讯云轻量服务器的"快照"功能做系统级备份
