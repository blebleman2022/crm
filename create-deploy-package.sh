#!/bin/bash

# 创建部署包脚本
set -e

echo "📦 创建CRM应用部署包"
echo "===================="

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 获取版本信息
get_version() {
    local timestamp=$(date +%Y%m%d-%H%M%S)
    local git_hash=""
    
    if git rev-parse --short HEAD >/dev/null 2>&1; then
        git_hash="-$(git rev-parse --short HEAD)"
    fi
    
    echo "v${timestamp}${git_hash}"
}

# 创建部署目录
create_deploy_dir() {
    local version=$1
    local deploy_dir="deploy-${version}"

    log_info "创建部署目录: ${deploy_dir}"

    # 清理旧的部署目录
    rm -rf deploy-* 2>/dev/null || true

    # 创建新的部署目录
    mkdir -p "${deploy_dir}"

    echo "${deploy_dir}"
}

# 复制应用文件
copy_app_files() {
    local deploy_dir=$1
    
    log_info "复制应用文件..."
    
    # 复制核心文件
    cp run.py "${deploy_dir}/"
    cp config.py "${deploy_dir}/"
    cp models.py "${deploy_dir}/"
    cp communication_utils.py "${deploy_dir}/"
    cp Dockerfile "${deploy_dir}/"
    cp start.sh "${deploy_dir}/"
    cp gunicorn.conf.py "${deploy_dir}/"
    cp requirements.txt "${deploy_dir}/"
    cp README.md "${deploy_dir}/"
    
    # 复制目录
    cp -r routes "${deploy_dir}/"
    cp -r templates "${deploy_dir}/"
    cp -r static "${deploy_dir}/"
    cp -r utils "${deploy_dir}/"
    
    # 创建必要的目录
    mkdir -p "${deploy_dir}/instance"
    mkdir -p "${deploy_dir}/logs"
    
    log_success "应用文件复制完成"
}

# 创建部署脚本
create_deploy_script() {
    local deploy_dir=$1
    
    log_info "创建部署脚本..."
    
    cat > "${deploy_dir}/deploy-server.sh" << 'EOF'
#!/bin/bash

# 服务器端部署脚本
set -e

echo "🚀 CRM应用服务器端部署"
echo "====================="

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查Docker
check_docker() {
    if ! command -v docker &> /dev/null; then
        log_error "Docker未安装"
        exit 1
    fi
    
    if ! docker info > /dev/null 2>&1; then
        log_error "Docker未运行"
        exit 1
    fi
    
    log_success "Docker检查通过"
}

# 停止旧容器
stop_old_container() {
    log_info "停止旧容器..."
    
    if docker ps -q --filter "name=crm-app" | grep -q .; then
        docker stop crm-app
        docker rm crm-app
        log_success "旧容器已停止"
    else
        log_info "没有运行中的容器"
    fi
}

# 构建新镜像
build_image() {
    log_info "构建Docker镜像..."
    
    docker build -t crm-app:latest .
    
    if [ $? -eq 0 ]; then
        log_success "镜像构建成功"
    else
        log_error "镜像构建失败"
        exit 1
    fi
}

# 启动新容器
start_container() {
    log_info "启动新容器..."
    
    docker run -d \
        --name crm-app \
        --restart unless-stopped \
        -p 80:80 \
        -e FLASK_ENV=production \
        -e DATABASE_URL=sqlite:///instance/edu_crm.db \
        -e SECRET_KEY=${SECRET_KEY:-crm-production-secret-$(date +%s)} \
        -v /var/lib/crm/instance:/app/instance \
        -v /var/lib/crm/logs:/app/logs \
        crm-app:latest
    
    if [ $? -eq 0 ]; then
        log_success "容器启动成功"
    else
        log_error "容器启动失败"
        exit 1
    fi
}

# 健康检查
health_check() {
    log_info "等待应用启动..."
    sleep 10
    
    log_info "执行健康检查..."
    
    for i in {1..30}; do
        if curl -f http://localhost/health > /dev/null 2>&1; then
            log_success "应用健康检查通过"
            return 0
        elif curl -f http://localhost/auth/login > /dev/null 2>&1; then
            log_success "应用启动成功（登录页面可访问）"
            return 0
        fi
        
        log_info "等待应用启动... ($i/30)"
        sleep 2
    done
    
    log_error "应用启动失败或健康检查超时"
    docker logs crm-app
    return 1
}

# 显示状态
show_status() {
    log_info "部署完成！"
    echo "================================"
    log_success "✅ 应用已成功部署"
    log_info "🌐 访问地址: http://$(hostname -I | awk '{print $1}')"
    log_info "📊 容器状态: $(docker ps --filter name=crm-app --format 'table {{.Status}}')"
    log_info "📝 查看日志: docker logs -f crm-app"
    log_info "🛑 停止应用: docker stop crm-app"
}

# 主函数
main() {
    check_docker
    stop_old_container
    build_image
    start_container
    health_check
    show_status
}

# 执行主函数
main "$@"
EOF

    chmod +x "${deploy_dir}/deploy-server.sh"
    
    log_success "部署脚本创建完成"
}

# 创建说明文件
create_readme() {
    local deploy_dir=$1
    local version=$2
    
    log_info "创建部署说明..."
    
    cat > "${deploy_dir}/DEPLOY.md" << EOF
# CRM应用部署包 ${version}

## 📦 包含内容

- 完整的Flask应用代码
- Docker配置文件
- 自动部署脚本
- 配置文件和依赖

## 🚀 快速部署

### 方法1：自动部署（推荐）
\`\`\`bash
# 解压部署包
tar -xzf crm-${version}.tar.gz
cd deploy-${version}

# 运行自动部署脚本
sudo ./deploy-server.sh
\`\`\`

### 方法2：手动部署
\`\`\`bash
# 构建镜像
docker build -t crm-app:latest .

# 启动容器
docker run -d \\
    --name crm-app \\
    --restart unless-stopped \\
    -p 80:80 \\
    -e FLASK_ENV=production \\
    -v /var/lib/crm/instance:/app/instance \\
    -v /var/lib/crm/logs:/app/logs \\
    crm-app:latest
\`\`\`

## 🔧 配置说明

### 环境变量
- \`FLASK_ENV\`: 运行环境（production）
- \`DATABASE_URL\`: 数据库连接字符串
- \`SECRET_KEY\`: 应用密钥

### 数据持久化
- 数据库文件: \`/var/lib/crm/instance/\`
- 日志文件: \`/var/lib/crm/logs/\`

## 📋 部署后检查

1. **健康检查**: \`curl http://localhost/health\`
2. **登录页面**: \`curl http://localhost/auth/login\`
3. **容器状态**: \`docker ps\`
4. **应用日志**: \`docker logs crm-app\`

## 🛠️ 故障排除

### 查看日志
\`\`\`bash
# 容器日志
docker logs -f crm-app

# 应用日志
docker exec crm-app tail -f /app/logs/app.log
\`\`\`

### 重启应用
\`\`\`bash
docker restart crm-app
\`\`\`

### 完全重新部署
\`\`\`bash
docker stop crm-app
docker rm crm-app
./deploy-server.sh
\`\`\`

## 📞 技术支持

如有问题，请检查：
1. Docker是否正常运行
2. 端口80是否被占用
3. 防火墙设置
4. 磁盘空间是否充足

部署时间: $(date)
版本: ${version}
EOF

    log_success "部署说明创建完成"
}

# 打包部署文件
create_package() {
    local deploy_dir=$1
    local version=$2
    
    log_info "打包部署文件..."
    
    local package_name="crm-${version}.tar.gz"
    
    tar -czf "${package_name}" "${deploy_dir}"
    
    if [ $? -eq 0 ]; then
        log_success "部署包创建成功: ${package_name}"
        
        # 显示包信息
        local size=$(du -h "${package_name}" | cut -f1)
        log_info "包大小: ${size}"
        log_info "包路径: $(pwd)/${package_name}"
        
        # 创建上传脚本
        create_upload_script "${package_name}"
        
    else
        log_error "打包失败"
        exit 1
    fi
}

# 创建上传脚本
create_upload_script() {
    local package_name=$1
    
    cat > "upload-${package_name%.tar.gz}.sh" << EOF
#!/bin/bash

# 上传部署包到服务器
echo "📤 上传部署包到服务器"
echo "===================="

SERVER_IP="47.100.238.50"
PACKAGE="${package_name}"

echo "正在上传 \${PACKAGE} 到服务器..."

# 上传文件
scp "\${PACKAGE}" root@\${SERVER_IP}:/tmp/

echo "正在服务器上解压和部署..."

# 在服务器上执行部署
ssh root@\${SERVER_IP} << 'REMOTE_SCRIPT'
cd /tmp
tar -xzf ${package_name}
cd deploy-*
chmod +x deploy-server.sh
./deploy-server.sh
REMOTE_SCRIPT

echo "🎉 部署完成！"
echo "访问地址: http://\${SERVER_IP}"
EOF

    chmod +x "upload-${package_name%.tar.gz}.sh"
    
    log_success "上传脚本创建完成: upload-${package_name%.tar.gz}.sh"
}

# 主函数
main() {
    local version=$(get_version)
    log_info "版本: ${version}"

    local deploy_dir=$(create_deploy_dir "${version}")

    copy_app_files "${deploy_dir}"
    create_deploy_script "${deploy_dir}"
    create_readme "${deploy_dir}" "${version}"
    create_package "${deploy_dir}" "${version}"
    
    # 清理临时目录
    rm -rf "${deploy_dir}"
    
    echo ""
    log_success "🎉 部署包创建完成！"
    echo "================================"
    log_info "📦 部署包: crm-${version}.tar.gz"
    log_info "📤 上传脚本: upload-crm-${version}.sh"
    echo ""
    log_info "🚀 快速部署命令:"
    echo "  ./upload-crm-${version}.sh"
    echo ""
    log_info "📋 手动部署步骤:"
    echo "  1. scp crm-${version}.tar.gz root@47.100.238.50:/tmp/"
    echo "  2. ssh root@47.100.238.50"
    echo "  3. cd /tmp && tar -xzf crm-${version}.tar.gz"
    echo "  4. cd deploy-${version} && ./deploy-server.sh"
}

# 执行主函数
main "$@"
