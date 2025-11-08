# SSL证书自动续期配置说明

## 🚀 一键配置（推荐）

### 步骤1：上传脚本到服务器

```bash
# 在本地执行
scp 一键配置SSL自动续期.sh root@47.100.238.50:/root/
```

### 步骤2：SSH登录服务器并执行

```bash
# SSH登录
ssh root@47.100.238.50

# 执行配置脚本
bash /root/一键配置SSL自动续期.sh
```

### 步骤3：验证配置

脚本执行完成后会自动显示配置状态。如果看到 ✅ 标志，说明配置成功！

---

## 📋 脚本功能

`一键配置SSL自动续期.sh` 会自动完成以下配置：

1. ✅ 检查并安装certbot
2. ✅ 验证SSL证书是否存在
3. ✅ 创建certbot验证目录
4. ✅ 配置systemd timer（每天自动检查）
5. ✅ 配置cron任务（备用方案）
6. ✅ 创建续期后钩子（自动重新加载nginx）
7. ✅ 创建证书监控脚本
8. ✅ 测试证书续期功能

---

## 🔧 手动配置（如果需要）

如果一键脚本执行失败，可以手动执行以下步骤：

### 1. 启用systemd timer

```bash
# 启用并启动certbot timer
systemctl enable certbot.timer
systemctl start certbot.timer

# 查看状态
systemctl status certbot.timer
```

### 2. 添加cron任务（备用）

```bash
# 编辑crontab
crontab -e

# 添加以下行（每天凌晨3点检查）
0 3 * * * /usr/bin/certbot renew --quiet --post-hook 'systemctl reload nginx'
```

### 3. 测试续期

```bash
# 模拟续期测试
certbot renew --dry-run

# 应该看到：
# Congratulations, all simulated renewals succeeded
```

---

## 💡 常用命令

### 查看证书状态

```bash
# 查看所有证书
certbot certificates

# 查看证书过期时间
/usr/local/bin/check-ssl-expiry.sh
```

### 手动续期

```bash
# 手动续期所有证书
certbot renew

# 强制续期（即使未到期）
certbot renew --force-renewal
```

### 查看自动续期状态

```bash
# 查看systemd timer状态
systemctl status certbot.timer

# 查看下次运行时间
systemctl list-timers | grep certbot

# 查看cron任务
crontab -l | grep certbot
```

### 查看日志

```bash
# 查看certbot日志
tail -f /var/log/letsencrypt/letsencrypt.log

# 查看续期日志
tail -f /var/log/certbot-renew.log

# 查看cron日志
tail -f /var/log/certbot-cron.log
```

---

## ⚠️ 常见问题

### 问题1：续期测试失败

**症状**：`certbot renew --dry-run` 失败

**原因**：nginx配置中HTTP完全重定向到HTTPS，导致certbot无法验证域名

**解决方案**：

修改nginx.conf中的HTTP服务器块：

```nginx
server {
    listen 80;
    server_name sxylab.com www.sxylab.com;

    # certbot验证路径（不重定向）
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    # 其他路径重定向到HTTPS
    location / {
        return 301 https://$server_name$request_uri;
    }
}
```

然后重新加载nginx：

```bash
nginx -t && systemctl reload nginx
```

### 问题2：systemd timer未运行

**检查**：

```bash
systemctl status certbot.timer
```

**解决方案**：

```bash
# 启用并启动timer
systemctl enable certbot.timer
systemctl start certbot.timer

# 如果certbot.timer不存在，运行配置脚本
bash /root/一键配置SSL自动续期.sh
```

### 问题3：证书续期后nginx未重新加载

**原因**：续期后钩子未配置

**解决方案**：

```bash
# 创建钩子脚本
mkdir -p /etc/letsencrypt/renewal-hooks/post

cat > /etc/letsencrypt/renewal-hooks/post/reload-nginx.sh << 'EOF'
#!/bin/bash
systemctl reload nginx
echo "$(date): nginx已重新加载" >> /var/log/certbot-renew.log
EOF

chmod +x /etc/letsencrypt/renewal-hooks/post/reload-nginx.sh
```

---

## 📊 监控和维护

### 每月检查（推荐）

```bash
# 检查证书状态
/usr/local/bin/check-ssl-expiry.sh

# 查看续期日志
tail -20 /var/log/certbot-renew.log

# 测试续期功能
certbot renew --dry-run
```

### 证书过期提醒

Let's Encrypt会在证书过期前发送邮件提醒：
- 过期前30天：第一次提醒
- 过期前7天：第二次提醒
- 过期前1天：最后提醒

**确保您能收到这些邮件！**

---

## 🎯 工作原理

### 自动续期流程

1. **每天检查**：systemd timer或cron任务每天运行
2. **判断是否需要续期**：证书过期前30天开始尝试续期
3. **验证域名所有权**：通过HTTP-01验证（访问 `/.well-known/acme-challenge/`）
4. **下载新证书**：验证成功后下载新证书
5. **重新加载nginx**：执行续期后钩子，重新加载nginx
6. **记录日志**：记录续期结果到日志文件

### 双重保障

- **主要方案**：systemd timer（每天随机时间运行）
- **备用方案**：cron任务（每天凌晨3点运行）

即使一个失败，另一个也能确保证书续期！

---

## ✅ 验证清单

配置完成后，请确认以下项目：

- [ ] `certbot renew --dry-run` 测试成功
- [ ] `systemctl status certbot.timer` 显示运行中
- [ ] `crontab -l` 显示certbot任务
- [ ] `/usr/local/bin/check-ssl-expiry.sh` 显示证书有效
- [ ] 能收到certbot的邮件通知
- [ ] nginx配置包含 `/.well-known/acme-challenge/` 路径

---

## 📞 支持

如果遇到问题：

1. 查看日志：`tail -f /var/log/letsencrypt/letsencrypt.log`
2. 测试续期：`certbot renew --dry-run`
3. 检查nginx配置：`nginx -t`
4. 重新运行配置脚本：`bash /root/一键配置SSL自动续期.sh`

---

## 🎉 总结

配置完成后，您的SSL证书将：

- ✅ 每天自动检查
- ✅ 过期前30天自动续期
- ✅ 续期成功后自动重新加载nginx
- ✅ 双重保障（systemd + cron）
- ✅ 邮件提醒

**您无需手动操作，证书将永久有效！**

