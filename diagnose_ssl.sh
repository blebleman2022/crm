#!/bin/bash
# SSL 配置诊断脚本
# 用于检查服务器 SSL/HTTPS 配置问题
# 使用方法: bash diagnose_ssl.sh

echo "============================================================"
echo "🔍 SSL/HTTPS 配置诊断脚本"
echo "域名: www.sxylab.com"
echo "============================================================"
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 1. 检查系统信息
echo "📋 1. 系统信息"
echo "-----------------------------------------------------------"
echo "操作系统: $(cat /etc/os-release | grep PRETTY_NAME | cut -d'"' -f2)"
echo "内核版本: $(uname -r)"
echo "当前时间: $(date)"
echo ""

# 2. 检查 Web 服务器
echo "🌐 2. Web 服务器检查"
echo "-----------------------------------------------------------"

# 检查 Nginx
if command -v nginx &> /dev/null; then
    echo -e "${GREEN}✅ Nginx 已安装${NC}"
    echo "   版本: $(nginx -v 2>&1 | cut -d'/' -f2)"
    
    # 检查 Nginx 状态
    if systemctl is-active --quiet nginx; then
        echo -e "${GREEN}✅ Nginx 正在运行${NC}"
    else
        echo -e "${RED}❌ Nginx 未运行${NC}"
    fi
    
    WEB_SERVER="nginx"
else
    echo -e "${YELLOW}⚠️  Nginx 未安装${NC}"
fi

# 检查 Apache
if command -v apache2 &> /dev/null || command -v httpd &> /dev/null; then
    echo -e "${GREEN}✅ Apache 已安装${NC}"
    if systemctl is-active --quiet apache2 || systemctl is-active --quiet httpd; then
        echo -e "${GREEN}✅ Apache 正在运行${NC}"
    fi
    WEB_SERVER="apache"
fi

echo ""

# 3. 检查端口监听
echo "🔌 3. 端口监听检查"
echo "-----------------------------------------------------------"

if netstat -tlnp 2>/dev/null | grep -q ":80 "; then
    echo -e "${GREEN}✅ 端口 80 (HTTP) 正在监听${NC}"
    netstat -tlnp 2>/dev/null | grep ":80 " | head -1
else
    echo -e "${RED}❌ 端口 80 (HTTP) 未监听${NC}"
fi

if netstat -tlnp 2>/dev/null | grep -q ":443 "; then
    echo -e "${GREEN}✅ 端口 443 (HTTPS) 正在监听${NC}"
    netstat -tlnp 2>/dev/null | grep ":443 " | head -1
else
    echo -e "${RED}❌ 端口 443 (HTTPS) 未监听${NC}"
fi

echo ""

# 4. 检查 SSL 证书
echo "📜 4. SSL 证书检查"
echo "-----------------------------------------------------------"

# 检查 Let's Encrypt 证书
if [ -d "/etc/letsencrypt/live/www.sxylab.com" ]; then
    echo -e "${GREEN}✅ 发现 Let's Encrypt 证书目录${NC}"
    echo "   路径: /etc/letsencrypt/live/www.sxylab.com"
    
    # 检查证书文件
    if [ -f "/etc/letsencrypt/live/www.sxylab.com/fullchain.pem" ]; then
        echo -e "${GREEN}✅ fullchain.pem 存在${NC}"
        
        # 检查证书有效期
        CERT_FILE="/etc/letsencrypt/live/www.sxylab.com/cert.pem"
        if [ -f "$CERT_FILE" ]; then
            echo ""
            echo "   证书详情:"
            
            # 颁发者
            ISSUER=$(openssl x509 -in "$CERT_FILE" -noout -issuer 2>/dev/null | sed 's/issuer=//')
            echo "   颁发者: $ISSUER"
            
            # 有效期
            NOT_BEFORE=$(openssl x509 -in "$CERT_FILE" -noout -startdate 2>/dev/null | cut -d'=' -f2)
            NOT_AFTER=$(openssl x509 -in "$CERT_FILE" -noout -enddate 2>/dev/null | cut -d'=' -f2)
            echo "   生效时间: $NOT_BEFORE"
            echo "   过期时间: $NOT_AFTER"
            
            # 检查是否过期
            if openssl x509 -in "$CERT_FILE" -noout -checkend 0 2>/dev/null; then
                DAYS_LEFT=$(( ($(date -d "$NOT_AFTER" +%s) - $(date +%s)) / 86400 ))
                if [ $DAYS_LEFT -lt 30 ]; then
                    echo -e "   ${YELLOW}⚠️  证书将在 $DAYS_LEFT 天后过期${NC}"
                else
                    echo -e "   ${GREEN}✅ 证书有效 (剩余 $DAYS_LEFT 天)${NC}"
                fi
            else
                echo -e "   ${RED}❌ 证书已过期!${NC}"
            fi
            
            # 检查域名
            echo ""
            echo "   证书包含的域名:"
            openssl x509 -in "$CERT_FILE" -noout -text 2>/dev/null | grep -A1 "Subject Alternative Name" | tail -1 | sed 's/DNS://g' | tr ',' '\n' | sed 's/^/   - /'
        fi
    else
        echo -e "${RED}❌ fullchain.pem 不存在${NC}"
    fi
    
    if [ -f "/etc/letsencrypt/live/www.sxylab.com/privkey.pem" ]; then
        echo -e "${GREEN}✅ privkey.pem 存在${NC}"
    else
        echo -e "${RED}❌ privkey.pem 不存在${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  未找到 Let's Encrypt 证书目录${NC}"
    
    # 检查其他可能的证书位置
    echo ""
    echo "   检查其他证书位置..."
    
    if [ -d "/etc/ssl/certs" ]; then
        echo "   /etc/ssl/certs 目录存在"
        ls -lh /etc/ssl/certs/*.pem 2>/dev/null | head -3
    fi
fi

echo ""

# 5. 检查 Certbot
echo "🤖 5. Certbot 检查"
echo "-----------------------------------------------------------"

if command -v certbot &> /dev/null; then
    echo -e "${GREEN}✅ Certbot 已安装${NC}"
    echo "   版本: $(certbot --version 2>&1)"

    # 检查证书列表
    echo ""
    echo "   已安装的证书:"
    sudo certbot certificates 2>/dev/null || echo "   无法获取证书列表"
else
    echo -e "${YELLOW}⚠️  Certbot 未安装${NC}"
fi

echo ""

# 6. 检查 Nginx 配置
if [ "$WEB_SERVER" = "nginx" ]; then
    echo "⚙️  6. Nginx SSL 配置检查"
    echo "-----------------------------------------------------------"

    # 查找配置文件
    NGINX_CONF=""
    if [ -f "/etc/nginx/sites-available/crm" ]; then
        NGINX_CONF="/etc/nginx/sites-available/crm"
    elif [ -f "/etc/nginx/sites-enabled/crm" ]; then
        NGINX_CONF="/etc/nginx/sites-enabled/crm"
    elif [ -f "/etc/nginx/conf.d/crm.conf" ]; then
        NGINX_CONF="/etc/nginx/conf.d/crm.conf"
    elif [ -f "/etc/nginx/nginx.conf" ]; then
        NGINX_CONF="/etc/nginx/nginx.conf"
    fi

    if [ -n "$NGINX_CONF" ]; then
        echo -e "${GREEN}✅ 找到 Nginx 配置文件${NC}"
        echo "   路径: $NGINX_CONF"
        echo ""

        # 检查是否配置了 SSL
        if grep -q "ssl_certificate" "$NGINX_CONF"; then
            echo -e "${GREEN}✅ 配置文件包含 SSL 设置${NC}"
            echo ""
            echo "   SSL 证书配置:"
            grep "ssl_certificate" "$NGINX_CONF" | sed 's/^/   /'
            echo ""

            # 检查是否监听 443 端口
            if grep -q "listen.*443.*ssl" "$NGINX_CONF"; then
                echo -e "${GREEN}✅ 配置了 HTTPS (443端口)${NC}"
            else
                echo -e "${RED}❌ 未配置 HTTPS 监听${NC}"
            fi

            # 检查是否有 HTTP 到 HTTPS 重定向
            if grep -q "return 301 https" "$NGINX_CONF"; then
                echo -e "${GREEN}✅ 配置了 HTTP 到 HTTPS 重定向${NC}"
            else
                echo -e "${YELLOW}⚠️  未配置 HTTP 到 HTTPS 重定向${NC}"
            fi
        else
            echo -e "${RED}❌ 配置文件未包含 SSL 设置${NC}"
        fi

        # 测试配置语法
        echo ""
        echo "   测试 Nginx 配置语法:"
        if sudo nginx -t 2>&1 | grep -q "syntax is ok"; then
            echo -e "${GREEN}✅ Nginx 配置语法正确${NC}"
        else
            echo -e "${RED}❌ Nginx 配置语法错误${NC}"
            sudo nginx -t 2>&1 | sed 's/^/   /'
        fi
    else
        echo -e "${YELLOW}⚠️  未找到 Nginx 配置文件${NC}"
    fi

    echo ""
fi

# 7. 在线测试 HTTPS
echo "🌐 7. HTTPS 连接测试"
echo "-----------------------------------------------------------"

if command -v curl &> /dev/null; then
    echo "测试 HTTPS 连接..."

    # 测试 HTTPS
    if curl -s -I --max-time 5 https://www.sxylab.com > /dev/null 2>&1; then
        echo -e "${GREEN}✅ HTTPS 连接成功${NC}"

        # 获取响应头
        echo ""
        echo "   响应头信息:"
        curl -s -I --max-time 5 https://www.sxylab.com | head -5 | sed 's/^/   /'
    else
        echo -e "${RED}❌ HTTPS 连接失败${NC}"

        # 详细错误信息
        echo ""
        echo "   错误详情:"
        curl -v --max-time 5 https://www.sxylab.com 2>&1 | grep -E "SSL|certificate|error" | sed 's/^/   /'
    fi

    # 测试 HTTP
    echo ""
    if curl -s -I --max-time 5 http://www.sxylab.com > /dev/null 2>&1; then
        echo -e "${GREEN}✅ HTTP 连接成功${NC}"

        # 检查是否重定向到 HTTPS
        if curl -s -I --max-time 5 http://www.sxylab.com | grep -q "301\|302"; then
            REDIRECT_URL=$(curl -s -I --max-time 5 http://www.sxylab.com | grep -i "location:" | awk '{print $2}' | tr -d '\r')
            if [[ "$REDIRECT_URL" == https* ]]; then
                echo -e "${GREEN}✅ HTTP 正确重定向到 HTTPS${NC}"
                echo "   重定向到: $REDIRECT_URL"
            else
                echo -e "${YELLOW}⚠️  HTTP 重定向但不是到 HTTPS${NC}"
            fi
        else
            echo -e "${YELLOW}⚠️  HTTP 未重定向到 HTTPS${NC}"
        fi
    else
        echo -e "${RED}❌ HTTP 连接失败${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  curl 未安装,跳过在线测试${NC}"
fi

echo ""

# 8. 总结和建议
echo "============================================================"
echo "📊 诊断总结"
echo "============================================================"
echo ""

# 收集问题
ISSUES=()

# 检查各项状态
if ! systemctl is-active --quiet nginx 2>/dev/null && ! systemctl is-active --quiet apache2 2>/dev/null; then
    ISSUES+=("Web 服务器未运行")
fi

if ! netstat -tlnp 2>/dev/null | grep -q ":443 "; then
    ISSUES+=("HTTPS 端口 (443) 未监听")
fi

if [ ! -d "/etc/letsencrypt/live/www.sxylab.com" ]; then
    ISSUES+=("未找到 SSL 证书")
elif [ ! -f "/etc/letsencrypt/live/www.sxylab.com/fullchain.pem" ]; then
    ISSUES+=("SSL 证书文件不完整")
fi

if [ -f "/etc/letsencrypt/live/www.sxylab.com/cert.pem" ]; then
    if ! openssl x509 -in "/etc/letsencrypt/live/www.sxylab.com/cert.pem" -noout -checkend 0 2>/dev/null; then
        ISSUES+=("SSL 证书已过期")
    fi
fi

if ! command -v certbot &> /dev/null; then
    ISSUES+=("Certbot 未安装")
fi

# 显示问题
if [ ${#ISSUES[@]} -eq 0 ]; then
    echo -e "${GREEN}✅ 未发现明显问题${NC}"
    echo ""
    echo "如果浏览器仍显示不安全,可能的原因:"
    echo "1. 浏览器缓存问题 - 尝试清除缓存或使用隐私模式"
    echo "2. 证书链不完整 - 确保使用 fullchain.pem 而不是 cert.pem"
    echo "3. 混合内容 - 页面中包含 HTTP 资源"
else
    echo -e "${RED}❌ 发现以下问题:${NC}"
    echo ""
    for issue in "${ISSUES[@]}"; do
        echo "   • $issue"
    done
    echo ""
    echo "建议操作:"
    echo "1. 将此诊断结果发送给技术支持"
    echo "2. 等待修复脚本"
fi

echo ""
echo "============================================================"
echo "诊断完成! 请将以上输出发送给技术支持。"
echo "============================================================"

