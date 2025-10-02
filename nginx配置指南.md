# Nginx 反向代理配置指南

## 📋 目标

将Nginx 80端口的访问转发到CRM应用的5000端口

---

## 🚀 快速配置（推荐）

### 方法1: 使用配置脚本（一键配置）

在服务器上创建并执行以下脚本：

```bash
cat > setup-nginx.sh << 'EOF'
#!/bin/bash

echo "========================================="
echo "  Nginx反向代理配置脚本"
echo "========================================="

# 获取服务器IP或域名
read -p "请输入服务器域名（如果没有域名，直接回车使用IP）: " DOMAIN
if [ -z "$DOMAIN" ]; then
    DOMAIN="_"
    echo "使用默认配置（通过IP访问）"
else
    echo "使用域名: $DOMAIN"
fi

# 创建Nginx配置文件
echo "📝 创建Nginx配置文件..."
sudo tee /etc/nginx/sites-available/crm << NGINX_EOF
server {
    listen 80;
    server_name $DOMAIN;

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
        
        # WebSocket支持（如果需要）
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # 超时设置
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # 静态文件直接由Nginx处理（可选，提升性能）
    location /static {
        alias /root/crm/static;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
NGINX_EOF

# 创建软链接启用站点
echo "🔗 启用站点配置..."
sudo ln -sf /etc/nginx/sites-available/crm /etc/nginx/sites-enabled/crm

# 删除默认站点（可选）
if [ -f /etc/nginx/sites-enabled/default ]; then
    echo "🗑️  删除默认站点配置..."
    sudo rm /etc/nginx/sites-enabled/default
fi

# 测试Nginx配置
echo "🧪 测试Nginx配置..."
sudo nginx -t

if [ $? -eq 0 ]; then
    # 重启Nginx
    echo "🔄 重启Nginx..."
    sudo systemctl restart nginx
    
    echo ""
    echo "========================================="
    echo "  ✅ Nginx配置成功！"
    echo "========================================="
    echo ""
    echo "📋 访问信息："
    if [ "$DOMAIN" = "_" ]; then
        echo "  - HTTP访问: http://$(curl -s ifconfig.me)"
    else
        echo "  - HTTP访问: http://$DOMAIN"
    fi
    echo ""
    echo "🔧 管理命令："
    echo "  - 查看Nginx状态: sudo systemctl status nginx"
    echo "  - 重启Nginx: sudo systemctl restart nginx"
    echo "  - 查看访问日志: sudo tail -f /var/log/nginx/crm-access.log"
    echo "  - 查看错误日志: sudo tail -f /var/log/nginx/crm-error.log"
    echo ""
else
    echo ""
    echo "❌ Nginx配置测试失败，请检查配置文件"
    echo "配置文件位置: /etc/nginx/sites-available/crm"
    echo ""
fi
EOF

chmod +x setup-nginx.sh
./setup-nginx.sh
```

---

## 📝 方法2: 手动配置

### 步骤1: 创建Nginx配置文件

```bash
sudo nano /etc/nginx/sites-available/crm
```

粘贴以下内容：

```nginx
server {
    listen 80;
    server_name _;  # 使用下划线表示接受所有域名/IP访问

    # 日志配置
    access_log /var/log/nginx/crm-access.log;
    error_log /var/log/nginx/crm-error.log;

    # 客户端上传大小限制
    client_max_body_size 10M;

    # 反向代理到Flask应用
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket支持
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # 超时设置
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # 静态文件直接由Nginx处理（可选，提升性能）
    location /static {
        alias /root/crm/static;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
```

**如果您有域名**，将 `server_name _;` 改为：
```nginx
server_name your-domain.com www.your-domain.com;
```

### 步骤2: 启用站点配置

```bash
# 创建软链接
sudo ln -s /etc/nginx/sites-available/crm /etc/nginx/sites-enabled/crm

# 删除默认站点（可选）
sudo rm /etc/nginx/sites-enabled/default
```

### 步骤3: 测试配置

```bash
sudo nginx -t
```

**预期输出**:
```
nginx: the configuration file /etc/nginx/nginx.conf syntax is ok
nginx: configuration file /etc/nginx/nginx.conf test is successful
```

### 步骤4: 重启Nginx

```bash
sudo systemctl restart nginx
```

### 步骤5: 验证配置

```bash
# 检查Nginx状态
sudo systemctl status nginx

# 测试访问
curl -I http://localhost
```

---

## 🔒 HTTPS配置（推荐）

如果您有域名，强烈建议配置HTTPS：

### 使用Let's Encrypt免费SSL证书

```bash
# 安装Certbot
sudo apt update
sudo apt install certbot python3-certbot-nginx -y

# 自动配置SSL
sudo certbot --nginx -d your-domain.com -d www.your-domain.com

# 测试自动续期
sudo certbot renew --dry-run
```

配置完成后，Nginx配置会自动更新为：

```nginx
server {
    listen 80;
    server_name your-domain.com www.your-domain.com;
    return 301 https://$server_name$request_uri;  # 重定向到HTTPS
}

server {
    listen 443 ssl http2;
    server_name your-domain.com www.your-domain.com;

    # SSL证书配置（由Certbot自动添加）
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    
    # SSL优化配置
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # 其他配置同上...
    location / {
        proxy_pass http://127.0.0.1:5000;
        # ... 其他proxy配置
    }
}
```

---

## 🔧 完整的生产环境配置（推荐）

```nginx
# HTTP重定向到HTTPS（如果配置了SSL）
server {
    listen 80;
    server_name your-domain.com www.your-domain.com;
    return 301 https://$server_name$request_uri;
}

# HTTPS主配置
server {
    listen 443 ssl http2;
    server_name your-domain.com www.your-domain.com;

    # SSL证书
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    
    # SSL优化
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # 安全头
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # 日志
    access_log /var/log/nginx/crm-access.log;
    error_log /var/log/nginx/crm-error.log;

    # 上传大小限制
    client_max_body_size 10M;

    # Gzip压缩
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript application/json application/javascript application/xml+rss;

    # 反向代理
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        
        proxy_buffering off;
    }

    # 静态文件
    location /static {
        alias /root/crm/static;
        expires 30d;
        add_header Cache-Control "public, immutable";
        access_log off;
    }

    # Favicon
    location = /favicon.ico {
        alias /root/crm/static/images/favicon.ico;
        access_log off;
        log_not_found off;
    }
}
```

---

## 🛠️ 常用管理命令

```bash
# 查看Nginx状态
sudo systemctl status nginx

# 启动Nginx
sudo systemctl start nginx

# 停止Nginx
sudo systemctl stop nginx

# 重启Nginx
sudo systemctl restart nginx

# 重新加载配置（不中断服务）
sudo systemctl reload nginx

# 测试配置文件
sudo nginx -t

# 查看访问日志
sudo tail -f /var/log/nginx/crm-access.log

# 查看错误日志
sudo tail -f /var/log/nginx/crm-error.log

# 查看Nginx版本
nginx -v
```

---

## 🔍 故障排查

### 问题1: 502 Bad Gateway

**原因**: Nginx无法连接到后端5000端口

**解决方案**:
```bash
# 检查CRM应用是否运行
docker compose ps

# 检查5000端口是否监听
sudo netstat -tlnp | grep 5000

# 查看CRM应用日志
docker compose logs -f

# 重启CRM应用
docker compose restart
```

### 问题2: 403 Forbidden

**原因**: 静态文件权限问题

**解决方案**:
```bash
# 检查文件权限
ls -la /root/crm/static

# 修改权限
sudo chmod -R 755 /root/crm/static
```

### 问题3: Nginx配置测试失败

**解决方案**:
```bash
# 查看详细错误
sudo nginx -t

# 检查配置文件语法
sudo nginx -T | grep -i error
```

---

## 📊 性能优化建议

### 1. 启用Gzip压缩

已在完整配置中包含

### 2. 配置缓存

```nginx
# 在http块中添加
proxy_cache_path /var/cache/nginx levels=1:2 keys_zone=crm_cache:10m max_size=100m inactive=60m;

# 在location块中添加
proxy_cache crm_cache;
proxy_cache_valid 200 10m;
proxy_cache_bypass $http_cache_control;
```

### 3. 限流配置

```nginx
# 在http块中添加
limit_req_zone $binary_remote_addr zone=crm_limit:10m rate=10r/s;

# 在location块中添加
limit_req zone=crm_limit burst=20 nodelay;
```

---

## ✅ 配置验证清单

- [ ] Nginx已安装并运行
- [ ] 配置文件已创建
- [ ] 配置文件语法正确（nginx -t）
- [ ] 软链接已创建
- [ ] Nginx已重启
- [ ] CRM应用在5000端口运行
- [ ] 可以通过80端口访问
- [ ] 日志文件正常记录
- [ ] 静态文件可以访问
- [ ] （可选）HTTPS已配置

---

## 🎯 快速测试

```bash
# 测试HTTP访问
curl -I http://localhost

# 测试通过IP访问
curl -I http://$(curl -s ifconfig.me)

# 测试静态文件
curl -I http://localhost/static/images/logo.png
```

---

**一键配置命令**（复制到服务器执行）:
```bash
curl -o setup-nginx.sh https://raw.githubusercontent.com/blebleman2022/crm/master/setup-nginx.sh && chmod +x setup-nginx.sh && ./setup-nginx.sh
```

