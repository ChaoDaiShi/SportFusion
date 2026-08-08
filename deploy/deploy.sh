#!/bin/bash
# ============================================================
# 体育产业测算平台 — 一键部署脚本
# 适用于: 腾讯云轻量应用服务器 (Ubuntu 20.04/22.04)
# 使用方法: chmod +x deploy.sh && sudo ./deploy.sh
# ============================================================

set -e

# ---- 配置变量 ----
PROJECT_DIR="/opt/sports-industry"
PYTHON_VERSION="python3"
NODE_VERSION="18"
SERVER_NAME="_"              # 改为你的域名，如 example.com
INSTALL_NODEJS=true          # 如果服务器已安装 Node.js，改为 false
INSTALL_PYTHON=true          # 如果服务器已安装 Python 3.10+，改为 false

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log()  { echo -e "${GREEN}[INFO]${NC}  $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC}  $1"; }
err()  { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }
step() { echo -e "\n${BLUE}==== $1 ====${NC}\n"; }

# ---- 检查 root ----
if [ "$EUID" -ne 0 ]; then
    err "请使用 sudo 运行: sudo ./deploy.sh"
fi

# ============================================================
# Step 1: 系统环境
# ============================================================
step "Step 1/6: 安装系统依赖"

apt-get update -qq

# 基础工具
apt-get install -y -qq curl wget git nginx certbot python3-certbot-nginx

# Python
if [ "$INSTALL_PYTHON" = true ]; then
    log "安装 Python 3.10+..."
    apt-get install -y -qq python3 python3-pip python3-venv python3-dev
fi

# Node.js
if [ "$INSTALL_NODEJS" = true ]; then
    log "安装 Node.js ${NODE_VERSION}..."
    if ! command -v node &>/dev/null; then
        curl -fsSL https://deb.nodesource.com/setup_${NODE_VERSION}.x | bash -
        apt-get install -y -qq nodejs
    fi
fi

log "Python: $($PYTHON_VERSION --version 2>&1)"
log "Node:   $(node --version 2>&1)"
log "Nginx:  $(nginx -v 2>&1)"

# ============================================================
# Step 2: 部署项目文件
# ============================================================
step "Step 2/6: 部署项目文件"

if [ -d "$PROJECT_DIR" ]; then
    warn "项目目录已存在: $PROJECT_DIR"
    read -p "是否覆盖? [y/N] " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        err "部署已取消"
    fi
    # 备份数据库
    if [ -f "$PROJECT_DIR/backend/sports_industry.db" ]; then
        cp "$PROJECT_DIR/backend/sports_industry.db" /tmp/sports_industry.db.bak
        log "数据库已备份到 /tmp/sports_industry.db.bak"
    fi
fi

# 创建目录
mkdir -p "$PROJECT_DIR"

# 复制项目文件（从当前 deploy.sh 所在项目的上级目录）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_DIR="$(dirname "$SCRIPT_DIR")"

log "从 $SOURCE_DIR 复制项目文件..."
cp -r "$SOURCE_DIR/backend" "$PROJECT_DIR/"
cp -r "$SOURCE_DIR/frontend" "$PROJECT_DIR/"
cp -r "$SOURCE_DIR/data" "$PROJECT_DIR/"

# 恢复数据库
if [ -f /tmp/sports_industry.db.bak ]; then
    cp /tmp/sports_industry.db.bak "$PROJECT_DIR/backend/sports_industry.db"
    rm /tmp/sports_industry.db.bak
    log "数据库已恢复"
fi

# 设置权限
chown -R www-data:www-data "$PROJECT_DIR"

# ============================================================
# Step 3: 后端环境
# ============================================================
step "Step 3/6: 配置后端 Python 环境"

cd "$PROJECT_DIR/backend"

# 创建虚拟环境
if [ ! -d ".venv" ]; then
    $PYTHON_VERSION -m venv .venv
    log "Python 虚拟环境已创建"
fi

# 安装依赖
.venv/bin/pip install --upgrade pip -q
.venv/bin/pip install -r requirements.txt -q
log "Python 依赖安装完成"

# 生产环境配置
if [ -f "$SOURCE_DIR/deploy/.env.production" ]; then
    cp "$SOURCE_DIR/deploy/.env.production" .env
    log "生产环境 .env 已配置"
fi

# 初始化数据库表
.venv/bin/python -c "
from models.database import engine, Base
from models.tables import *
Base.metadata.create_all(bind=engine)
print('数据库表初始化完成')
"

# ============================================================
# Step 4: 前端构建
# ============================================================
step "Step 4/6: 构建前端"

cd "$PROJECT_DIR/frontend"

# 安装依赖
if [ ! -d "node_modules" ]; then
    npm install --production=false
    log "前端依赖安装完成"
fi

# 生产构建
npm run build
log "前端生产构建完成 → $PROJECT_DIR/frontend/dist/"

# ============================================================
# Step 5: Nginx 配置
# ============================================================
step "Step 5/6: 配置 Nginx"

NGINX_CONF="$SOURCE_DIR/deploy/nginx/sports-industry.conf"
NGINX_AVAILABLE="/etc/nginx/sites-available/sports-industry"
NGINX_ENABLED="/etc/nginx/sites-enabled/sports-industry"

if [ -f "$NGINX_CONF" ]; then
    cp "$NGINX_CONF" "$NGINX_AVAILABLE"
    # 替换域名占位符
    sed -i "s/server_name _;/server_name ${SERVER_NAME};/g" "$NGINX_AVAILABLE"
    log "Nginx 配置已复制"

    # 禁用默认站点
    if [ -f /etc/nginx/sites-enabled/default ]; then
        rm -f /etc/nginx/sites-enabled/default
        log "默认站点已禁用"
    fi

    # 启用站点
    if [ ! -L "$NGINX_ENABLED" ]; then
        ln -sf "$NGINX_AVAILABLE" "$NGINX_ENABLED"
        log "站点已启用"
    fi

    # 测试配置
    nginx -t && log "Nginx 配置测试通过" || err "Nginx 配置测试失败"
    systemctl reload nginx
    log "Nginx 已重载"
else
    err "找不到 Nginx 配置文件: $NGINX_CONF"
fi

# ============================================================
# Step 6: 后端服务
# ============================================================
step "Step 6/6: 启动后端服务"

SERVICE_FILE="$SOURCE_DIR/deploy/systemd/sports-backend.service"
SYSTEMD_PATH="/etc/systemd/system/sports-backend.service"

if [ -f "$SERVICE_FILE" ]; then
    cp "$SERVICE_FILE" "$SYSTEMD_PATH"
    systemctl daemon-reload
    systemctl enable sports-backend
    systemctl restart sports-backend
    log "后端服务已启动"
    sleep 2
    systemctl status sports-backend --no-pager --lines=5
else
    err "找不到 systemd 服务文件: $SERVICE_FILE"
fi

# ============================================================
# 完成
# ============================================================
echo ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}  部署完成！${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo "  项目目录:  $PROJECT_DIR"
echo "  前端文件:  $PROJECT_DIR/frontend/dist/"
echo "  后端日志:  journalctl -u sports-backend -f"
echo "  Nginx日志: /var/log/nginx/sports-industry-error.log"
echo ""
echo "  后续步骤:"
echo "  1. 配置防火墙: sudo ufw allow 80/tcp"
echo "  2. 配置域名DNS解析到服务器IP"
echo "  3. (可选) 配置HTTPS: sudo certbot --nginx -d your-domain.com"
echo "  4. 访问 http://$(curl -s ifconfig.me 2>/dev/null || echo 'YOUR_IP')"
echo ""
