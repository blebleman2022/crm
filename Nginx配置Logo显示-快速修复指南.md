# Nginx配置Logo显示 - 快速修复指南

## 🔍 问题诊断结果

根据你的诊断输出：
- ✅ Logo文件存在：`/root/crm/static/images/custom-logo.png`
- ✅ 目录权限正确：755
- ✅ 文件权限正确：644
- ❌ **Nginx配置文件不存在**（问题根源）
- ❌ 访问返回301重定向

## 🎯 问题原因

Nginx没有配置静态文件路径映射，导致无法访问 `/static/` 目录下的文件。

---

## 🚀 解决方案（3种方法）

### 方法1：使用自动修复脚本（推荐）

```bash
# 1. SSH登录服务器
ssh root@47.100.238.50

# 2. 进入项目目录
cd /root/crm

# 3. 拉取最新代码（包含修复脚本）
git pull origin bak

# 4. 执行Nginx修复脚本
bash fix_nginx_logo.sh
```

---

### 方法2：手动添加Nginx配置（如果脚本失败）

#### 步骤1：查找Nginx配置文件

```bash
# 查找sxylab.com的配置文件
ls -la /etc/nginx/sites-enabled/
ls -la /etc/nginx/sites-available/

# 或者查看主配置
cat /etc/nginx/nginx.conf | grep -A 20 "server {"
```

#### 步骤2：编辑配置文件

**情况A：如果有 `/etc/nginx/sites-enabled/sxylab.com` 文件**

```bash
# 编辑配置文件
nano /etc/nginx/sites-enabled/sxylab.com

# 在 server { } 块中添加以下内容：
```

```nginx
server {
    listen 80;
    server_name sxylab.com www.sxylab.com;

    # 添加这段配置 ⬇️
    location /static/ {
        alias /root/crm/static/;
        expires 7d;
        add_header Cache-Control "public";
        access_log off;
    }
    # 添加结束 ⬆️

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

**情况B：如果配置在 `/etc/nginx/nginx.conf` 中**

```bash
# 编辑主配置文件
nano /etc/nginx/nginx.conf

# 找到 http { } 块，在其中的 server { } 块中添加上述 location /static/ 配置
```

#### 步骤3：测试并重载Nginx

```bash
# 测试配置
nginx -t

# 如果测试通过，重载Nginx
systemctl reload nginx

# 或者重启Nginx
systemctl restart nginx
```

#### 步骤4：验证修复

```bash
# 测试静态文件访问
curl -I http://localhost/static/images/custom-logo.png

# 应该返回 HTTP/1.1 200 OK
```

---

### 方法3：快速命令行修复（适合紧急情况）

如果你熟悉命令行，可以直接执行：

```bash
# 1. SSH登录
ssh root@47.100.238.50

# 2. 查找配置文件位置
CONF_FILE=$(find /etc/nginx -name "sxylab.com" -o -name "nginx.conf" | head -1)
echo "配置文件: $CONF_FILE"

# 3. 备份配置
cp $CONF_FILE ${CONF_FILE}.bak.$(date +%Y%m%d)

# 4. 检查是否已有静态文件配置
grep -n "location /static/" $CONF_FILE

# 5. 如果没有，手动编辑添加
nano $CONF_FILE

# 6. 测试并重载
nginx -t && systemctl reload nginx

# 7. 测试访问
curl -I http://localhost/static/images/custom-logo.png
```

---

## 📋 完整的Nginx配置示例

### HTTP配置（端口80）

```nginx
server {
    listen 80;
    server_name sxylab.com www.sxylab.com;

    # 静态文件配置
    location /static/ {
        alias /root/crm/static/;
        expires 7d;
        add_header Cache-Control "public";
        access_log off;
    }

    # 代理到Flask应用
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
```

### HTTPS配置（端口443）

```nginx
server {
    listen 443 ssl http2;
    server_name sxylab.com www.sxylab.com;

    # SSL证书配置
    ssl_certificate /etc/letsencrypt/live/sxylab.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/sxylab.com/privkey.pem;

    # 静态文件配置
    location /static/ {
        alias /root/crm/static/;
        expires 7d;
        add_header Cache-Control "public";
        access_log off;
    }

    # 代理到Flask应用
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
    }
}

# HTTP重定向到HTTPS
server {
    listen 80;
    server_name sxylab.com www.sxylab.com;
    return 301 https://$server_name$request_uri;
}
```

---

## ✅ 验证修复成功

修复后，执行以下检查：

### 1. 命令行测试

```bash
# 测试HTTP 200响应
curl -I http://localhost/static/images/custom-logo.png

# 应该看到：
# HTTP/1.1 200 OK
# Content-Type: image/png
```

### 2. 浏览器测试

访问以下URL，应该能看到logo图片：
- http://sxylab.com/static/images/custom-logo.png
- https://sxylab.com/static/images/custom-logo.png

### 3. 清除浏览器缓存

如果仍然看不到，清除缓存：
- **Chrome/Edge**: `Ctrl+Shift+Delete`
- **Safari**: `Cmd+Option+E`
- **强制刷新**: `Ctrl+F5` (Windows) 或 `Cmd+Shift+R` (Mac)

---

## 🔧 常见问题排查

### Q1: nginx -t 报错

```bash
# 查看详细错误
nginx -t

# 检查语法错误，通常是：
# - 缺少分号 ;
# - 大括号不匹配 { }
# - 路径错误
```

### Q2: 仍然返回404

```bash
# 检查alias路径是否正确
ls -la /root/crm/static/images/

# 检查Nginx错误日志
tail -f /var/log/nginx/error.log

# 检查文件权限
namei -l /root/crm/static/images/custom-logo.png
```

### Q3: 返回403 Forbidden

```bash
# 修复权限
chmod 755 /root
chmod 755 /root/crm
chmod 755 /root/crm/static
chmod 755 /root/crm/static/images
chmod 644 /root/crm/static/images/*.png
```

---

## 📞 需要帮助？

如果以上方法都不行，请提供以下信息：

```bash
# 1. Nginx配置文件内容
cat /etc/nginx/sites-enabled/sxylab.com

# 2. Nginx错误日志
tail -20 /var/log/nginx/error.log

# 3. 文件权限
ls -la /root/crm/static/images/

# 4. Nginx测试结果
nginx -t
```

