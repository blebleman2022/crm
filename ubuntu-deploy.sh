#!/bin/bash

# ============================================
# Ubuntu服务器直接部署脚本
# ============================================
# 
# 功能：
# 1. 在Ubuntu上直接部署Flask应用
# 2. 使用systemd管理服务
# 3. 代码更新后自动重启
# 4. Nginx反向代理
#
# 使用方法：
#   sudo bash ubuntu-deploy.sh
#
# ============================================

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

log_error() {
    echo -e "${RED}[✗]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

log_step() {
    echo -e "${CYAN}[STEP]${NC} $1"
}

# 检查是否以root运行
if [ "$EUID" -ne 0 ]; then 
    log_error "请使用sudo运行此脚本"
    exit 1
fi

echo ""
echo "========================================="
echo "  🚀 CRM系统Ubuntu直接部署"
echo "========================================="
echo ""
echo "📋 本脚本将："
echo "  ✅ 安装Python虚拟环境"
echo "  ✅ 安装项目依赖"
echo "  ✅ 配置systemd服务"
echo "  ✅ 配置Nginx反向代理"
echo "  ✅ 设置开机自启动"
echo ""
echo "⚠️  注意："
echo "  - 这将停止并移除Docker容器"
echo "  - 数据库文件会被保留"
echo ""

read -p "是否继续？(y/N) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    log_info "部署已取消"
    exit 0
fi

echo ""

# 获取项目路径
PROJECT_DIR=$(pwd)
log_info "项目目录: $PROJECT_DIR"

# 获取当前用户（实际执行sudo的用户）
ACTUAL_USER=${SUDO_USER:-$USER}
log_info "运行用户: $ACTUAL_USER"

echo ""

# ============================================
# 步骤1: 停止并移除Docker容器
# ============================================
log_step "步骤1/8: 停止Docker容器"

if command -v docker &> /dev/null; then
    if docker compose ps | grep -q "crm-app"; then
        log_info "停止Docker容器..."
        docker compose down
        log_success "Docker容器已停止"
    else
        log_info "没有运行中的Docker容器"
    fi
else
    log_info "Docker未安装，跳过"
fi

echo ""

# ============================================
# 步骤2: 安装系统依赖
# ============================================
log_step "步骤2/8: 安装系统依赖"

log_info "更新软件包列表..."
apt update -qq

log_info "安装Python和相关工具..."
apt install -y python3 python3-pip python3-venv nginx supervisor sqlite3

log_success "系统依赖安装完成"

echo ""

# ============================================
# 步骤3: 创建Python虚拟环境
# ============================================
log_step "步骤3/8: 创建Python虚拟环境"

if [ -d "$PROJECT_DIR/venv" ]; then
    log_warning "虚拟环境已存在，跳过创建"
else
    log_info "创建虚拟环境..."
    sudo -u $ACTUAL_USER python3 -m venv $PROJECT_DIR/venv
    log_success "虚拟环境创建完成"
fi

echo ""

# ============================================
# 步骤4: 安装Python依赖
# ============================================
log_step "步骤4/8: 安装Python依赖"

log_info "安装项目依赖..."
sudo -u $ACTUAL_USER $PROJECT_DIR/venv/bin/pip install -r $PROJECT_DIR/requirements.txt -q

log_success "Python依赖安装完成"

echo ""

# ============================================
# 步骤5: 创建systemd服务
# ============================================
log_step "步骤5/8: 创建systemd服务"

log_info "创建systemd服务文件..."

cat > /etc/systemd/system/crm.service <<EOF
[Unit]
Description=CRM Flask Application
After=network.target

[Service]
Type=simple
User=$ACTUAL_USER
WorkingDirectory=$PROJECT_DIR
Environment="PATH=$PROJECT_DIR/venv/bin"
ExecStart=$PROJECT_DIR/venv/bin/python $PROJECT_DIR/run.py
Restart=always
RestartSec=3

# 日志配置
StandardOutput=append:/var/log/crm/app.log
StandardError=append:/var/log/crm/error.log

[Install]
WantedBy=multi-user.target
EOF

log_success "systemd服务文件已创建"

# 创建日志目录
mkdir -p /var/log/crm
chown $ACTUAL_USER:$ACTUAL_USER /var/log/crm
log_success "日志目录已创建"

# 重新加载systemd
systemctl daemon-reload
log_success "systemd已重新加载"

echo ""

# ============================================
# 步骤6: 配置Nginx
# ============================================
log_step "步骤6/8: 配置Nginx"

log_info "创建Nginx配置..."

cat > /etc/nginx/sites-available/crm <<EOF
server {
    listen 80;
    server_name _;

    # 日志配置
    access_log /var/log/nginx/crm-access.log;
    error_log /var/log/nginx/crm-error.log;

    # 客户端上传大小限制
    client_max_body_size 10M;

    # 反向代理到Flask应用
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # WebSocket支持
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # 超时设置
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # 静态文件直接由Nginx处理
    location /static/ {
        alias $PROJECT_DIR/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Favicon
    location = /favicon.ico {
        alias $PROJECT_DIR/static/images/logo1.png;
        expires 30d;
    }

    # Gzip压缩
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript application/x-javascript application/xml+rss application/json;
}
EOF

log_success "Nginx配置文件已创建"

# 启用站点
if [ -f /etc/nginx/sites-enabled/crm ]; then
    rm /etc/nginx/sites-enabled/crm
fi
ln -s /etc/nginx/sites-available/crm /etc/nginx/sites-enabled/crm
log_success "Nginx站点已启用"

# 删除默认站点
if [ -f /etc/nginx/sites-enabled/default ]; then
    rm /etc/nginx/sites-enabled/default
    log_info "已删除Nginx默认站点"
fi

# 测试Nginx配置
nginx -t
if [ $? -eq 0 ]; then
    log_success "Nginx配置测试通过"
else
    log_error "Nginx配置测试失败"
    exit 1
fi

echo ""

# ============================================
# 步骤7: 设置文件权限
# ============================================
log_step "步骤7/8: 设置文件权限"

# 设置项目目录权限
chown -R $ACTUAL_USER:$ACTUAL_USER $PROJECT_DIR
chmod -R 755 $PROJECT_DIR

# 设置静态文件权限
chmod -R 755 $PROJECT_DIR/static
find $PROJECT_DIR/static -type f -exec chmod 644 {} \;

# 设置instance目录权限
mkdir -p $PROJECT_DIR/instance
chown -R $ACTUAL_USER:$ACTUAL_USER $PROJECT_DIR/instance
chmod 700 $PROJECT_DIR/instance

log_success "文件权限设置完成"

echo ""

# ============================================
# 步骤8: 启动服务
# ============================================
log_step "步骤8/8: 启动服务"

# 启动CRM服务
log_info "启动CRM服务..."
systemctl enable crm
systemctl start crm

sleep 3

if systemctl is-active --quiet crm; then
    log_success "CRM服务已启动"
else
    log_error "CRM服务启动失败"
    log_info "查看日志: journalctl -u crm -n 50"
    exit 1
fi

# 重启Nginx
log_info "重启Nginx..."
systemctl restart nginx

if systemctl is-active --quiet nginx; then
    log_success "Nginx已启动"
else
    log_error "Nginx启动失败"
    exit 1
fi

echo ""

# ============================================
# 完成
# ============================================
echo "========================================="
echo "  ✅ 部署完成！"
echo "========================================="
echo ""

log_success "CRM系统已成功部署到Ubuntu"

echo ""
echo "📋 服务信息:"
echo "  - CRM服务: systemctl status crm"
echo "  - Nginx服务: systemctl status nginx"
echo "  - 项目目录: $PROJECT_DIR"
echo "  - 运行用户: $ACTUAL_USER"
echo ""

echo "🌐 访问地址:"
echo "  - HTTP: http://$(hostname -I | awk '{print $1}')"
echo "  - 本地: http://localhost"
echo ""

echo "📝 常用命令:"
echo "  - 查看服务状态: systemctl status crm"
echo "  - 重启服务: sudo systemctl restart crm"
echo "  - 查看日志: sudo journalctl -u crm -f"
echo "  - 查看应用日志: tail -f /var/log/crm/app.log"
echo "  - 查看错误日志: tail -f /var/log/crm/error.log"
echo ""

echo "🔄 代码更新流程:"
echo "  1. git pull origin master"
echo "  2. sudo systemctl restart crm"
echo "  3. 刷新浏览器"
echo ""

echo "💡 提示:"
echo "  - 代码更新后只需重启服务即可生效"
echo "  - 不需要重新构建Docker镜像"
echo "  - 数据库文件位置: $PROJECT_DIR/instance/edu_crm.db"
echo ""

# 显示服务状态
log_info "当前服务状态:"
echo "-----------------------------------"
systemctl status crm --no-pager -l | head -15
echo "-----------------------------------"

echo ""
log_success "部署完成！请访问系统进行测试。"
echo ""

