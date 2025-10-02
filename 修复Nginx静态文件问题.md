# 修复Nginx静态文件问题

## 🔴 问题描述

- ✅ 5000端口访问正常
- ❌ 80端口访问时logo和favicon显示错误

## 🎯 问题原因

Nginx反向代理配置中，静态文件路径配置不正确，导致：
1. `/static/` 路径无法正确映射到实际文件
2. `/favicon.ico` 路径配置错误
3. 可能存在文件权限问题

---

## ✅ 快速修复（推荐）

### 方法1: 使用自动修复脚本

在服务器上执行：

```bash
# 1. 进入项目目录
cd ~/crm

# 2. 拉取最新代码（包含修复脚本）
git pull origin master

# 3. 运行诊断脚本（可选，查看问题）
sudo bash diagnose-nginx.sh

# 4. 运行修复脚本
sudo bash fix-nginx-static.sh
```

修复脚本会自动：
- ✅ 检查并修复文件权限
- ✅ 更新Nginx配置
- ✅ 重新加载Nginx
- ✅ 测试静态文件访问

---

### 方法2: 手动修复

#### 步骤1: 检查静态文件是否存在

```bash
ls -la /root/crm/static/images/
```

**预期输出**:
```
-rw-r--r-- 1 root root  xxxx custom-logo.png
-rw-r--r-- 1 root root  xxxx logo.jpg
-rw-r--r-- 1 root root  xxxx logo1.png
```

#### 步骤2: 修复文件权限

```bash
# 修改权限为755（目录）和644（文件）
sudo chmod -R 755 /root/crm/static
sudo find /root/crm/static -type f -exec chmod 644 {} \;

# 修改所有者为nginx用户（根据系统不同可能是www-data）
sudo chown -R www-data:www-data /root/crm/static
# 或者
sudo chown -R nginx:nginx /root/crm/static
```

#### 步骤3: 更新Nginx配置

编辑Nginx配置文件：

```bash
sudo nano /etc/nginx/sites-available/crm
```

确保包含以下配置（**注意 `/static/` 后面的斜杠很重要**）：

```nginx
server {
    listen 80;
    server_name _;

    # 日志配置
    access_log /var/log/nginx/crm-access.log;
    error_log /var/log/nginx/crm-error.log;

    # 客户端上传大小限制
    client_max_body_size 10M;

    # ⭐ 静态文件配置（必须在反向代理之前）
    location /static/ {
        alias /root/crm/static/;  # 注意结尾的斜杠
        expires 30d;
        add_header Cache-Control "public, immutable";
        access_log off;
    }

    # ⭐ Favicon配置
    location = /favicon.ico {
        alias /root/crm/static/images/logo1.png;
        access_log off;
        log_not_found off;
        expires 30d;
    }

    # 反向代理到Flask应用
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
}
```

**关键点**:
1. ✅ `location /static/` 必须以斜杠结尾
2. ✅ `alias /root/crm/static/;` 必须以斜杠结尾
3. ✅ 静态文件location必须在反向代理location之前

#### 步骤4: 测试并重新加载Nginx

```bash
# 测试配置
sudo nginx -t

# 重新加载Nginx
sudo systemctl reload nginx
```

#### 步骤5: 验证修复

```bash
# 测试logo访问
curl -I http://localhost/static/images/logo1.png

# 测试custom-logo访问
curl -I http://localhost/static/images/custom-logo.png

# 测试favicon访问
curl -I http://localhost/favicon.ico
```

**预期输出**（都应该返回200）:
```
HTTP/1.1 200 OK
Content-Type: image/png
...
```

---

## 🔍 常见问题排查

### 问题1: 返回404 Not Found

**原因**: 文件路径配置错误

**解决方案**:
```bash
# 检查Nginx配置中的alias路径
grep "alias" /etc/nginx/sites-available/crm

# 确保路径正确且以斜杠结尾
# 正确: alias /root/crm/static/;
# 错误: alias /root/crm/static;
```

### 问题2: 返回403 Forbidden

**原因**: 文件权限不足

**解决方案**:
```bash
# 检查文件权限
ls -la /root/crm/static/images/

# 修复权限
sudo chmod -R 755 /root/crm/static

# 检查Nginx用户
ps aux | grep nginx | grep worker

# 修改所有者（根据Nginx用户）
sudo chown -R www-data:www-data /root/crm/static
```

### 问题3: 返回502 Bad Gateway

**原因**: 后端5000端口未运行

**解决方案**:
```bash
# 检查Docker容器状态
docker compose ps

# 重启容器
docker compose restart
```

### 问题4: 浏览器仍显示错误

**原因**: 浏览器缓存

**解决方案**:
- 按 `Ctrl + F5` 强制刷新
- 或清除浏览器缓存
- 或使用隐私模式访问

---

## 📊 诊断工具

### 使用诊断脚本

```bash
cd ~/crm
sudo bash diagnose-nginx.sh
```

诊断脚本会检查：
1. ✅ 项目目录是否存在
2. ✅ 静态文件是否存在
3. ✅ 文件权限是否正确
4. ✅ Nginx配置是否正确
5. ✅ Nginx是否运行
6. ✅ 静态文件是否可访问
7. ✅ 错误日志内容

### 手动诊断命令

```bash
# 1. 检查静态文件
ls -la /root/crm/static/images/

# 2. 检查Nginx配置
sudo nginx -t
cat /etc/nginx/sites-available/crm

# 3. 检查Nginx状态
sudo systemctl status nginx

# 4. 查看错误日志
sudo tail -f /var/log/nginx/crm-error.log

# 5. 测试访问
curl -I http://localhost/static/images/logo1.png
curl -I http://localhost/favicon.ico

# 6. 检查端口监听
sudo netstat -tlnp | grep -E '80|5000'
```

---

## 🎯 完整修复流程

```bash
# 1. 进入项目目录
cd ~/crm

# 2. 拉取最新代码
git pull origin master

# 3. 修复文件权限
sudo chmod -R 755 /root/crm/static

# 4. 运行修复脚本
sudo bash fix-nginx-static.sh

# 5. 测试访问
curl -I http://localhost/static/images/logo1.png
curl -I http://localhost/favicon.ico

# 6. 清除浏览器缓存后访问
# 按 Ctrl+F5 强制刷新页面
```

---

## ✅ 验证清单

修复完成后，请验证以下项目：

- [ ] `curl -I http://localhost/static/images/logo1.png` 返回200
- [ ] `curl -I http://localhost/static/images/custom-logo.png` 返回200
- [ ] `curl -I http://localhost/favicon.ico` 返回200
- [ ] 浏览器访问页面，logo正常显示
- [ ] 浏览器标签页，favicon正常显示
- [ ] Nginx错误日志无相关错误

---

## 📝 Nginx配置要点总结

### ✅ 正确配置

```nginx
# 静态文件 - 注意斜杠
location /static/ {
    alias /root/crm/static/;  # ✅ 两个斜杠都要有
    expires 30d;
}

# Favicon
location = /favicon.ico {
    alias /root/crm/static/images/logo1.png;  # ✅ 精确匹配
}
```

### ❌ 错误配置

```nginx
# 错误1: 缺少结尾斜杠
location /static {  # ❌ 缺少斜杠
    alias /root/crm/static;  # ❌ 缺少斜杠
}

# 错误2: 使用root而不是alias
location /static/ {
    root /root/crm;  # ❌ 应该用alias
}

# 错误3: 路径不匹配
location /static/ {
    alias /root/crm/static;  # ❌ 缺少结尾斜杠
}
```

---

## 🚀 一键修复命令

```bash
cd ~/crm && git pull origin master && sudo chmod -R 755 /root/crm/static && sudo bash fix-nginx-static.sh
```

---

**需要帮助？**

查看诊断结果：
```bash
sudo bash diagnose-nginx.sh
```

查看错误日志：
```bash
sudo tail -f /var/log/nginx/crm-error.log
```

