#!/bin/bash

# ============================================
# ECS部署验证脚本
# 用于快速验证部署是否成功
# ============================================

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 日志函数
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

# 测试计数
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# 测试函数
run_test() {
    local test_name="$1"
    local test_command="$2"
    
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    
    echo ""
    log_info "测试 $TOTAL_TESTS: $test_name"
    
    if eval "$test_command" > /dev/null 2>&1; then
        log_success "$test_name"
        PASSED_TESTS=$((PASSED_TESTS + 1))
        return 0
    else
        log_error "$test_name"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        return 1
    fi
}

echo "========================================"
echo "  EduConnect CRM 部署验证"
echo "========================================"
echo ""

# 1. 检查Python环境
run_test "Python 3.8+ 已安装" "python3 --version | grep -E 'Python 3\.(8|9|10|11|12)'"

# 2. 检查项目文件
run_test "run.py 文件存在" "test -f run.py"
run_test "config.py 文件存在" "test -f config.py"
run_test "models.py 文件存在" "test -f models.py"
run_test "requirements.txt 文件存在" "test -f requirements.txt"

# 3. 检查虚拟环境
if [ -d "venv" ]; then
    log_success "虚拟环境目录存在"
    PASSED_TESTS=$((PASSED_TESTS + 1))
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    
    # 激活虚拟环境
    source venv/bin/activate
    
    # 4. 检查Python包
    run_test "Flask 已安装" "python -c 'import flask'"
    run_test "SQLAlchemy 已安装" "python -c 'import sqlalchemy'"
    run_test "Flask-Login 已安装" "python -c 'import flask_login'"
    run_test "Gunicorn 已安装" "python -c 'import gunicorn'"
    
    # 5. 测试配置导入
    echo ""
    log_info "测试配置导入..."
    if python -c "from config import config, ProductionConfig; print('OK')" 2>/dev/null | grep -q "OK"; then
        log_success "config 模块导入成功"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        log_error "config 模块导入失败"
        FAILED_TESTS=$((FAILED_TESTS + 1))
    fi
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    
    # 6. 测试应用创建（开发环境）
    echo ""
    log_info "测试开发环境应用创建..."
    if FLASK_ENV=development python -c "from run import create_app; app = create_app('development'); print('OK')" 2>/dev/null | grep -q "OK"; then
        log_success "开发环境应用创建成功"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        log_error "开发环境应用创建失败"
        FAILED_TESTS=$((FAILED_TESTS + 1))
    fi
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    
    # 7. 测试应用创建（生产环境）
    echo ""
    log_info "测试生产环境应用创建..."
    if FLASK_ENV=production python -c "from run import create_app; app = create_app('production'); print('OK')" 2>/dev/null | grep -q "OK"; then
        log_success "生产环境应用创建成功"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        log_error "生产环境应用创建失败"
        FAILED_TESTS=$((FAILED_TESTS + 1))
    fi
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    
    # 8. 测试Gunicorn应用实例导入
    echo ""
    log_info "测试Gunicorn应用实例导入..."
    if FLASK_ENV=production python -c "from run import app; print('OK')" 2>/dev/null | grep -q "OK"; then
        log_success "Gunicorn应用实例导入成功"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        log_error "Gunicorn应用实例导入失败"
        FAILED_TESTS=$((FAILED_TESTS + 1))
    fi
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    
else
    log_error "虚拟环境目录不存在"
    FAILED_TESTS=$((FAILED_TESTS + 1))
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    
    echo ""
    log_warning "请先创建虚拟环境："
    echo "  python3 -m venv venv"
    echo "  source venv/bin/activate"
    echo "  pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple"
fi

# 9. 检查目录结构
echo ""
log_info "检查目录结构..."
run_test "instance 目录存在" "test -d instance || mkdir -p instance"
run_test "logs 目录存在" "test -d logs || mkdir -p logs"
run_test "backups 目录存在" "test -d backups || mkdir -p backups"

# 10. 检查Gunicorn配置
run_test "gunicorn.conf.py 文件存在" "test -f gunicorn.conf.py"

# 11. 检查服务状态（如果使用systemd）
echo ""
log_info "检查服务状态..."
if systemctl is-active --quiet crm 2>/dev/null; then
    log_success "CRM服务正在运行"
    PASSED_TESTS=$((PASSED_TESTS + 1))
elif systemctl status crm 2>/dev/null | grep -q "could not be found"; then
    log_warning "CRM服务未配置（这是正常的，如果不使用systemd）"
else
    log_warning "CRM服务未运行"
fi
TOTAL_TESTS=$((TOTAL_TESTS + 1))

# 12. 检查端口监听
echo ""
log_info "检查端口监听..."
if netstat -tlnp 2>/dev/null | grep -q ":5000" || ss -tlnp 2>/dev/null | grep -q ":5000"; then
    log_success "端口 5000 正在监听"
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    log_warning "端口 5000 未监听（服务可能未启动）"
fi
TOTAL_TESTS=$((TOTAL_TESTS + 1))

# 13. 测试健康检查端点（如果服务在运行）
echo ""
log_info "测试健康检查端点..."
if curl -f -s --connect-timeout 3 http://localhost:5000/health > /dev/null 2>&1; then
    log_success "健康检查端点响应正常"
    PASSED_TESTS=$((PASSED_TESTS + 1))
    
    # 显示健康检查结果
    HEALTH_RESPONSE=$(curl -s http://localhost:5000/health)
    echo "  响应: $HEALTH_RESPONSE"
else
    log_warning "健康检查端点无响应（服务可能未启动）"
fi
TOTAL_TESTS=$((TOTAL_TESTS + 1))

# 输出测试结果
echo ""
echo "========================================"
echo "  测试结果汇总"
echo "========================================"
echo ""
echo "总测试数: $TOTAL_TESTS"
echo -e "${GREEN}通过: $PASSED_TESTS${NC}"
echo -e "${RED}失败: $FAILED_TESTS${NC}"
echo ""

# 计算通过率
PASS_RATE=$((PASSED_TESTS * 100 / TOTAL_TESTS))

if [ $FAILED_TESTS -eq 0 ]; then
    echo -e "${GREEN}🎉 所有测试通过！部署成功！${NC}"
    echo ""
    echo "下一步："
    echo "1. 如果服务未运行，启动服务："
    echo "   sudo systemctl start crm"
    echo "   或"
    echo "   gunicorn -c gunicorn.conf.py run:app"
    echo ""
    echo "2. 访问应用："
    echo "   http://localhost:5000"
    echo ""
    exit 0
elif [ $PASS_RATE -ge 80 ]; then
    echo -e "${YELLOW}⚠️  大部分测试通过 (${PASS_RATE}%)${NC}"
    echo ""
    echo "建议："
    echo "1. 检查失败的测试项"
    echo "2. 如果只是服务未启动，可以启动服务"
    echo "3. 查看日志: tail -f logs/crm.log"
    echo ""
    exit 0
else
    echo -e "${RED}❌ 多个测试失败 (${PASS_RATE}%)${NC}"
    echo ""
    echo "请检查："
    echo "1. 是否拉取了最新代码: git pull"
    echo "2. 是否安装了依赖: pip install -r requirements.txt"
    echo "3. 查看详细错误信息"
    echo ""
    exit 1
fi

