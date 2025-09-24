#!/bin/bash

# 本地测试脚本集合
set -e

echo "🧪 CRM应用本地测试套件"
echo "======================="

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

# 测试1：Python语法和导入测试
test_python_syntax() {
    log_info "测试1: Python语法和导入测试"
    echo "--------------------------------"
    
    # 语法检查
    python -m py_compile run.py
    if [ $? -eq 0 ]; then
        log_success "run.py 语法检查通过"
    else
        log_error "run.py 语法错误"
        return 1
    fi
    
    # 导入测试
    python -c "
import sys
sys.path.insert(0, '.')
try:
    from run import app
    print('✅ 成功导入 run.app')
    print(f'✅ app 类型: {type(app)}')
    print(f'✅ app 名称: {app.name}')
    
    with app.app_context():
        print('✅ 应用上下文正常')
        
    print('🎉 Python导入测试通过！')
except Exception as e:
    print(f'❌ 导入测试失败: {e}')
    import traceback
    traceback.print_exc()
    exit(1)
"
    
    log_success "Python测试完成"
    echo ""
}

# 测试2：Docker构建测试
test_docker_build() {
    log_info "测试2: Docker构建测试"
    echo "--------------------------------"
    
    # 检查Docker
    if ! docker info > /dev/null 2>&1; then
        log_error "Docker未运行，跳过Docker测试"
        return 1
    fi
    
    # 构建镜像
    log_info "构建Docker镜像..."
    docker build -t crm-test-build . --no-cache
    
    if [ $? -eq 0 ]; then
        log_success "Docker镜像构建成功"
    else
        log_error "Docker镜像构建失败"
        return 1
    fi
    
    # 测试镜像
    log_info "测试镜像启动..."
    docker run --rm -d --name crm-build-test -p 8082:80 crm-test-build
    
    sleep 10
    
    # 测试连接
    if curl -f http://localhost:8082/health > /dev/null 2>&1; then
        log_success "Docker容器启动成功"
    else
        log_warning "健康检查失败，查看日志..."
        docker logs crm-build-test
    fi
    
    # 清理
    docker stop crm-build-test 2>/dev/null || true
    docker rmi crm-test-build 2>/dev/null || true
    
    log_success "Docker构建测试完成"
    echo ""
}

# 测试3：使用Docker Compose测试
test_docker_compose() {
    log_info "测试3: Docker Compose测试"
    echo "--------------------------------"
    
    if ! command -v docker-compose &> /dev/null; then
        log_warning "docker-compose未安装，跳过此测试"
        return 1
    fi
    
    # 创建测试目录
    mkdir -p test-data/instance test-data/logs
    
    # 启动服务
    log_info "启动Docker Compose服务..."
    docker-compose -f docker-compose.test.yml up -d
    
    sleep 15
    
    # 测试服务
    if curl -f http://localhost:8080/health > /dev/null 2>&1; then
        log_success "Docker Compose服务正常"
        log_info "🌐 访问地址: http://localhost:8080"
    else
        log_warning "服务可能未正常启动，查看日志..."
        docker-compose -f docker-compose.test.yml logs
    fi
    
    # 询问是否保持运行
    read -p "是否保持服务运行以便手动测试？(y/N): " -n 1 -r
    echo
    
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "停止Docker Compose服务..."
        docker-compose -f docker-compose.test.yml down
        rm -rf test-data
    else
        log_info "服务继续运行，使用以下命令管理："
        echo "  查看日志: docker-compose -f docker-compose.test.yml logs -f"
        echo "  停止服务: docker-compose -f docker-compose.test.yml down"
    fi
    
    log_success "Docker Compose测试完成"
    echo ""
}

# 测试4：端口和网络测试
test_network() {
    log_info "测试4: 端口和网络测试"
    echo "--------------------------------"
    
    # 检查端口占用
    local ports=(8080 8081 8082)
    for port in "${ports[@]}"; do
        if lsof -i :$port > /dev/null 2>&1; then
            log_warning "端口 $port 已被占用"
        else
            log_success "端口 $port 可用"
        fi
    done
    
    log_success "网络测试完成"
    echo ""
}

# 测试5：依赖检查
test_dependencies() {
    log_info "测试5: 依赖检查"
    echo "--------------------------------"
    
    # 检查Python版本
    python_version=$(python --version 2>&1)
    log_info "Python版本: $python_version"
    
    # 检查pip包
    log_info "检查关键依赖包..."
    pip list | grep -E "(Flask|gunicorn|SQLAlchemy)" || log_warning "某些依赖包可能未安装"
    
    # 检查requirements.txt
    if [ -f requirements.txt ]; then
        log_info "检查requirements.txt中的包..."
        pip check || log_warning "依赖包版本可能有冲突"
    fi
    
    log_success "依赖检查完成"
    echo ""
}

# 主函数
main() {
    local test_type=${1:-all}
    
    case $test_type in
        python)
            test_python_syntax
            ;;
        docker)
            test_docker_build
            ;;
        compose)
            test_docker_compose
            ;;
        network)
            test_network
            ;;
        deps)
            test_dependencies
            ;;
        all)
            test_dependencies
            test_python_syntax
            test_network
            test_docker_build
            test_docker_compose
            ;;
        help|*)
            echo "使用方法: $0 [test_type]"
            echo ""
            echo "Test types:"
            echo "  all      运行所有测试（默认）"
            echo "  python   Python语法和导入测试"
            echo "  docker   Docker构建测试"
            echo "  compose  Docker Compose测试"
            echo "  network  端口和网络测试"
            echo "  deps     依赖检查"
            echo "  help     显示帮助"
            ;;
    esac
}

# 执行主函数
main "$@"
