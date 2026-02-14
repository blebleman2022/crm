#!/bin/bash
# 详细检查 SSL 证书和浏览器访问问题
# 使用方法: bash check_ssl_detail.sh

echo "============================================================"
echo "🔍 SSL 证书详细检查"
echo "============================================================"
echo ""

# 1. 检查证书详情
echo "📜 1. 证书详细信息"
echo "-----------------------------------------------------------"
sudo certbot certificates
echo ""

# 2. 检查证书文件内容
echo "📄 2. 证书文件验证"
echo "-----------------------------------------------------------"
CERT_FILE="/etc/letsencrypt/live/sxylab.com/cert.pem"

if [ -f "$CERT_FILE" ]; then
    echo "证书主题:"
    openssl x509 -in "$CERT_FILE" -noout -subject
    
    echo ""
    echo "证书颁发者:"
    openssl x509 -in "$CERT_FILE" -noout -issuer
    
    echo ""
    echo "证书有效期:"
    openssl x509 -in "$CERT_FILE" -noout -dates
    
    echo ""
    echo "证书包含的域名 (SAN):"
    openssl x509 -in "$CERT_FILE" -noout -text | grep -A1 "Subject Alternative Name"
    
    echo ""
    echo "证书序列号:"
    openssl x509 -in "$CERT_FILE" -noout -serial
fi

echo ""

# 3. 测试服务器端 SSL
echo "🌐 3. 服务器端 SSL 测试"
echo "-----------------------------------------------------------"
echo "测试 sxylab.com:443..."
echo | openssl s_client -connect sxylab.com:443 -servername sxylab.com 2>/dev/null | grep -E "subject=|issuer=|notAfter=|Verify return code"

echo ""
echo "测试 www.sxylab.com:443..."
echo | openssl s_client -connect www.sxylab.com:443 -servername www.sxylab.com 2>/dev/null | grep -E "subject=|issuer=|notAfter=|Verify return code"

echo ""

# 4. 检查 Nginx 配置
echo "⚙️  4. Nginx 配置检查"
echo "-----------------------------------------------------------"
echo "当前使用的证书路径:"
grep -E "ssl_certificate|server_name" /etc/nginx/sites-available/crm | grep -v "#"

echo ""

# 5. 检查 Nginx 进程加载的证书
echo "🔄 5. Nginx 进程状态"
echo "-----------------------------------------------------------"
echo "Nginx 主进程启动时间:"
ps -eo pid,lstart,cmd | grep "nginx: master" | grep -v grep

echo ""
echo "Nginx 配置最后修改时间:"
ls -lh /etc/nginx/sites-available/crm | awk '{print $6, $7, $8, $9}'

echo ""

# 6. 测试 HTTPS 访问
echo "🌍 6. HTTPS 访问测试"
echo "-----------------------------------------------------------"
echo "测试 https://sxylab.com ..."
curl -I -v https://sxylab.com 2>&1 | grep -E "SSL certificate|subject:|issuer:|expire date|Server certificate"

echo ""
echo "测试 https://www.sxylab.com ..."
curl -I -v https://www.sxylab.com 2>&1 | grep -E "SSL certificate|subject:|issuer:|expire date|Server certificate"

echo ""

# 7. 检查证书链
echo "🔗 7. 证书链检查"
echo "-----------------------------------------------------------"
echo "检查 fullchain.pem 是否包含完整证书链..."
CHAIN_COUNT=$(grep -c "BEGIN CERTIFICATE" /etc/letsencrypt/live/sxylab.com/fullchain.pem)
echo "证书链包含 $CHAIN_COUNT 个证书"

if [ $CHAIN_COUNT -ge 2 ]; then
    echo "✅ 证书链完整 (包含服务器证书和中间证书)"
else
    echo "❌ 证书链不完整 (可能导致浏览器不信任)"
fi

echo ""

# 8. 在线 SSL 测试建议
echo "============================================================"
echo "📊 诊断建议"
echo "============================================================"
echo ""
echo "请访问以下在线工具进行详细检测:"
echo "1. SSL Labs: https://www.ssllabs.com/ssltest/analyze.html?d=www.sxylab.com"
echo "2. SSL Checker: https://www.sslshopper.com/ssl-checker.html#hostname=www.sxylab.com"
echo ""
echo "浏览器测试:"
echo "1. 清除浏览器缓存 (Ctrl+Shift+Delete)"
echo "2. 使用隐私模式访问 https://www.sxylab.com"
echo "3. 按 F12 打开开发者工具 -> Security 标签查看证书详情"
echo ""
echo "如果仍显示不安全,请:"
echo "1. 截图浏览器的错误信息"
echo "2. 查看浏览器证书详情 (点击地址栏的不安全图标)"
echo "3. 将以上信息发送给技术支持"
echo ""

