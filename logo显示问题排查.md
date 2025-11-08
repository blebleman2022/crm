# Logo无法显示问题排查指南

## 🔍 问题分析

Logo的访问路径：
- **浏览器请求**：`http://sxylab.com/static/images/custom-logo.png`
- **Nginx配置**：`location /static/` → `alias /root/crm/static/`
- **实际文件路径**：`/root/crm/static/images/custom-logo.png`

## 📋 排查步骤

### 步骤1：检查logo文件是否存在

```bash
# SSH登录服务器
ssh root@47.100.238.50

# 检查logo文件
ls -la /root/crm/static/images/

# 应该看到 custom-logo.png 或 custom-logo.jpg 等文件
```

**如果文件不存在**，需要上传logo文件：

```bash
# 在本地执行（上传logo）
scp static/images/custom-logo.png root@47.100.238.50:/root/crm/static/images/
```

### 步骤2：检查文件权限

```bash
# 检查目录权限
ls -ld /root/crm/static/
ls -ld /root/crm/static/images/

# 检查文件权限
ls -l /root/crm/static/images/custom-logo.*

# 修复权限（如果需要）
chmod 755 /root/crm/static/
chmod 755 /root/crm/static/images/
chmod 644 /root/crm/static/images/custom-logo.*
```

### 步骤3：检查Nginx配置

```bash
# 查看Nginx配置
cat /etc/nginx/sites-enabled/sxylab.com | grep -A 5 "location /static"

# 应该看到：
# location /static/ {
#     alias /root/crm/static/;
#     ...
# }
```

**重要**：`alias` 路径末尾必须有 `/`，否则会导致路径错误！

### 步骤4：测试静态文件访问

```bash
# 在服务器上测试
curl -I http://localhost/static/images/custom-logo.png

# 应该返回 200 OK
# 如果返回 404，说明Nginx配置或文件路径有问题
# 如果返回 403，说明权限有问题
```

### 步骤5：检查浏览器控制台

在浏览器中：
1. 按 `F12` 打开开发者工具
2. 切换到 `Network` (网络) 标签
3. 刷新页面
4. 查找 `custom-logo.png` 请求
5. 查看状态码和错误信息

**常见错误**：
- `404 Not Found` - 文件不存在或路径错误
- `403 Forbidden` - 权限问题
- `502 Bad Gateway` - Nginx配置错误

### 步骤6：检查Nginx错误日志

```bash
# 查看错误日志
tail -50 /var/log/nginx/sxylab_error.log

# 查看访问日志
tail -50 /var/log/nginx/sxylab_access.log | grep "custom-logo"
```

## 🛠️ 常见问题和解决方案

### 问题1：文件不存在

**症状**：浏览器返回404错误

**解决方案**：

```bash
# 方案A：从本地上传
scp static/images/custom-logo.png root@47.100.238.50:/root/crm/static/images/

# 方案B：在服务器上从git拉取
cd /root/crm
git pull origin master

# 确保文件存在
ls -la static/images/custom-logo.*
```

### 问题2：权限问题

**症状**：浏览器返回403 Forbidden

**解决方案**：

```bash
# 修复目录权限
chmod 755 /root/crm/static/
chmod 755 /root/crm/static/images/

# 修复文件权限
chmod 644 /root/crm/static/images/custom-logo.*

# 如果Nginx以www-data用户运行，可能需要修改所有者
chown -R www-data:www-data /root/crm/static/
```

### 问题3：Nginx配置错误

**症状**：静态文件无法访问

**常见错误配置**：

```nginx
# ❌ 错误：alias路径末尾缺少 /
location /static/ {
    alias /root/crm/static;  # 缺少末尾的 /
}

# ✅ 正确：alias路径末尾必须有 /
location /static/ {
    alias /root/crm/static/;  # 末尾有 /
}
```

**修复方法**：

```bash
# 编辑配置文件
vim /etc/nginx/sites-enabled/sxylab.com

# 确保配置正确后测试
nginx -t

# 重新加载Nginx
systemctl reload nginx
```

### 问题4：浏览器缓存

**症状**：修复后仍然看不到logo

**解决方案**：

```bash
# 清除浏览器缓存
# Chrome: Ctrl+Shift+Delete
# Firefox: Ctrl+Shift+Delete

# 或者强制刷新
# Ctrl+F5 (Windows)
# Cmd+Shift+R (Mac)
```

### 问题5：路径大小写问题

**症状**：Linux系统区分大小写

**解决方案**：

```bash
# 检查文件名大小写
ls -la /root/crm/static/images/

# 确保文件名完全匹配
# custom-logo.png (正确)
# Custom-Logo.png (错误)
# CUSTOM-LOGO.PNG (错误)
```

## 🔧 快速诊断脚本

我已经创建了一个诊断脚本 `check_logo.sh`，上传到服务器后运行：

```bash
# 上传诊断脚本
scp check_logo.sh root@47.100.238.50:/root/

# SSH登录服务器
ssh root@47.100.238.50

# 运行诊断脚本
bash /root/check_logo.sh
```

脚本会自动检查：
- ✅ Logo文件是否存在
- ✅ 文件权限是否正确
- ✅ Nginx配置是否正确
- ✅ 静态文件是否可访问
- ✅ 错误日志中的相关信息

## 📝 完整的修复流程

```bash
# 1. SSH登录服务器
ssh root@47.100.238.50

# 2. 进入项目目录
cd /root/crm

# 3. 拉取最新代码（包含logo文件）
git pull origin master

# 4. 检查logo文件
ls -la static/images/custom-logo.*

# 5. 如果文件不存在，从本地上传
# 在本地终端执行：
# scp static/images/custom-logo.png root@47.100.238.50:/root/crm/static/images/

# 6. 修复权限
chmod 755 static/
chmod 755 static/images/
chmod 644 static/images/custom-logo.*

# 7. 测试访问
curl -I http://localhost/static/images/custom-logo.png

# 8. 如果返回200，说明配置正确
# 如果返回404或403，检查上面的常见问题

# 9. 清除浏览器缓存并刷新页面
```

## ✅ 验证清单

修复后，请验证以下内容：

- [ ] 文件存在：`ls -la /root/crm/static/images/custom-logo.*`
- [ ] 权限正确：`-rw-r--r--` (644)
- [ ] Nginx配置正确：`alias /root/crm/static/;` (末尾有/)
- [ ] 本地测试通过：`curl -I http://localhost/static/images/custom-logo.png` 返回200
- [ ] 浏览器可以访问：`http://sxylab.com/static/images/custom-logo.png`
- [ ] 登录页显示logo
- [ ] 侧边栏显示logo

## 🎯 最可能的原因

根据经验，logo无法显示最常见的原因是：

1. **文件未上传到服务器** (80%的情况)
2. **文件权限问题** (15%的情况)
3. **Nginx配置错误** (5%的情况)

建议先检查文件是否存在，这是最常见的问题！

---

如果以上方法都无法解决问题，请提供以下信息：

1. `ls -la /root/crm/static/images/` 的输出
2. `curl -I http://localhost/static/images/custom-logo.png` 的输出
3. `/var/log/nginx/sxylab_error.log` 的最后50行
4. 浏览器控制台中的错误信息截图

