# Ubuntu直接部署指南

## 🎯 部署方案对比

### Docker部署 vs Ubuntu直接部署

| 特性 | Docker部署 | Ubuntu直接部署 |
|------|-----------|---------------|
| **代码更新** | 需要重新构建镜像 | 只需重启服务 ⭐ |
| **更新速度** | 2-5分钟 | 5-10秒 ⭐ |
| **资源占用** | 较高 | 较低 ⭐ |
| **环境隔离** | 完全隔离 ⭐ | 共享系统环境 |
| **部署复杂度** | 简单 ⭐ | 中等 |
| **适用场景** | 生产环境、多服务 | 单应用、快速迭代 ⭐ |

**推荐**：如果您需要频繁更新代码，Ubuntu直接部署更合适！

---

## 🚀 一键部署

### 在服务器上执行

```bash
# 1. 进入项目目录
cd ~/crm

# 2. 拉取部署脚本
git pull origin master

# 3. 运行部署脚本
sudo bash ubuntu-deploy.sh
```

**部署时间**：约2-3分钟

---

## 📋 部署脚本功能

### ubuntu-deploy.sh 会自动完成：

1. ✅ 停止并移除Docker容器（如果存在）
2. ✅ 安装系统依赖（Python3, Nginx, Supervisor等）
3. ✅ 创建Python虚拟环境
4. ✅ 安装项目依赖
5. ✅ 创建systemd服务（开机自启动）
6. ✅ 配置Nginx反向代理
7. ✅ 设置文件权限
8. ✅ 启动服务并验证

---

## 🔄 代码更新流程

### 方法1: 使用快速更新脚本（推荐）⭐

```bash
cd ~/crm
bash quick-update.sh
```

**耗时**：5-10秒

### 方法2: 手动更新

```bash
# 1. 备份数据库（可选）
cp instance/edu_crm.db instance/backup_$(date +%Y%m%d).db

# 2. 拉取代码
git pull origin master

# 3. 重启服务
sudo systemctl restart crm

# 4. 验证
sudo systemctl status crm
```

**耗时**：10-15秒

---

## 📊 更新速度对比

### Docker部署更新

```bash
git pull origin master
docker compose down
docker compose build --no-cache  # ⏱️ 2-5分钟
docker compose up -d
```

**总耗时**：2-5分钟

### Ubuntu直接部署更新

```bash
git pull origin master
sudo systemctl restart crm  # ⏱️ 5-10秒
```

**总耗时**：5-10秒

**速度提升**：20-60倍！⚡

---

## 🛠️ 服务管理

### systemd服务命令

```bash
# 查看服务状态
sudo systemctl status crm

# 启动服务
sudo systemctl start crm

# 停止服务
sudo systemctl stop crm

# 重启服务
sudo systemctl restart crm

# 查看实时日志
sudo journalctl -u crm -f

# 查看最近50条日志
sudo journalctl -u crm -n 50

# 禁用开机自启动
sudo systemctl disable crm

# 启用开机自启动
sudo systemctl enable crm
```

### 应用日志

```bash
# 查看应用日志
tail -f /var/log/crm/app.log

# 查看错误日志
tail -f /var/log/crm/error.log

# 查看Nginx访问日志
tail -f /var/log/nginx/crm-access.log

# 查看Nginx错误日志
tail -f /var/log/nginx/crm-error.log
```

---

## 📁 目录结构

### 部署后的目录结构

```
~/crm/
├── venv/                    # Python虚拟环境
├── instance/                # 数据库目录
│   └── edu_crm.db          # SQLite数据库
├── static/                  # 静态文件
├── templates/               # 模板文件
├── routes/                  # 路由文件
├── run.py                   # 应用入口
├── requirements.txt         # 依赖列表
└── ...

/etc/systemd/system/
└── crm.service             # systemd服务文件

/etc/nginx/sites-available/
└── crm                     # Nginx配置文件

/var/log/crm/
├── app.log                 # 应用日志
└── error.log               # 错误日志
```

---

## 🔧 配置文件

### systemd服务配置

位置：`/etc/systemd/system/crm.service`

```ini
[Unit]
Description=CRM Flask Application
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/crm
Environment="PATH=/root/crm/venv/bin"
ExecStart=/root/crm/venv/bin/python /root/crm/run.py
Restart=always
RestartSec=3

StandardOutput=append:/var/log/crm/app.log
StandardError=append:/var/log/crm/error.log

[Install]
WantedBy=multi-user.target
```

### Nginx配置

位置：`/etc/nginx/sites-available/crm`

```nginx
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location /static/ {
        alias /root/crm/static/;
        expires 30d;
    }
}
```

---

## 🔍 故障排除

### 问题1: 服务启动失败

**检查日志**:
```bash
sudo journalctl -u crm -n 50
tail -f /var/log/crm/error.log
```

**常见原因**:
- 端口5000被占用
- Python依赖缺失
- 数据库文件权限问题

**解决方案**:
```bash
# 检查端口占用
sudo netstat -tuln | grep 5000

# 重新安装依赖
cd ~/crm
source venv/bin/activate
pip install -r requirements.txt

# 检查数据库权限
ls -lh instance/edu_crm.db
```

### 问题2: Nginx 502错误

**原因**: Flask应用未运行

**解决方案**:
```bash
# 检查CRM服务状态
sudo systemctl status crm

# 如果未运行，启动服务
sudo systemctl start crm
```

### 问题3: 静态文件404

**检查Nginx配置**:
```bash
sudo nginx -t
```

**检查文件权限**:
```bash
ls -lh static/
```

**解决方案**:
```bash
# 修复权限
sudo chmod -R 755 ~/crm/static
sudo systemctl restart nginx
```

### 问题4: 代码更新后未生效

**原因**: 服务未重启

**解决方案**:
```bash
sudo systemctl restart crm
```

---

## 🔄 从Docker迁移到Ubuntu部署

### 迁移步骤

```bash
# 1. 备份数据库
docker compose exec crm-app cp /app/instance/edu_crm.db /app/instance/backup.db
docker compose cp crm-app:/app/instance/backup.db ./instance/

# 2. 停止Docker容器
docker compose down

# 3. 运行Ubuntu部署脚本
sudo bash ubuntu-deploy.sh

# 4. 验证数据库
ls -lh instance/edu_crm.db

# 5. 测试访问
curl -I http://localhost
```

---

## 📊 性能优化

### 1. 使用Gunicorn（生产环境推荐）

安装Gunicorn:
```bash
source venv/bin/activate
pip install gunicorn
```

修改systemd服务:
```bash
sudo nano /etc/systemd/system/crm.service
```

修改ExecStart行:
```ini
ExecStart=/root/crm/venv/bin/gunicorn -w 4 -b 127.0.0.1:5000 run:app
```

重启服务:
```bash
sudo systemctl daemon-reload
sudo systemctl restart crm
```

### 2. 配置日志轮转

创建日志轮转配置:
```bash
sudo nano /etc/logrotate.d/crm
```

添加内容:
```
/var/log/crm/*.log {
    daily
    rotate 7
    compress
    delaycompress
    notifempty
    create 0640 root root
    sharedscripts
    postrotate
        systemctl reload crm > /dev/null 2>&1 || true
    endscript
}
```

### 3. 启用Nginx缓存

编辑Nginx配置:
```bash
sudo nano /etc/nginx/sites-available/crm
```

添加缓存配置:
```nginx
# 在http块中添加
proxy_cache_path /var/cache/nginx levels=1:2 keys_zone=crm_cache:10m max_size=100m;

# 在location /中添加
proxy_cache crm_cache;
proxy_cache_valid 200 5m;
```

---

## 🔒 安全建议

### 1. 使用非root用户运行

创建专用用户:
```bash
sudo useradd -m -s /bin/bash crmuser
sudo chown -R crmuser:crmuser ~/crm
```

修改systemd服务:
```ini
User=crmuser
```

### 2. 配置防火墙

```bash
# 允许HTTP
sudo ufw allow 80/tcp

# 允许HTTPS
sudo ufw allow 443/tcp

# 启用防火墙
sudo ufw enable
```

### 3. 配置SSL证书

使用Let's Encrypt:
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

---

## 📝 常见问题

### Q1: 如何查看服务是否运行？

```bash
sudo systemctl status crm
```

### Q2: 如何查看实时日志？

```bash
sudo journalctl -u crm -f
```

### Q3: 如何更新Python依赖？

```bash
cd ~/crm
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart crm
```

### Q4: 如何回滚到之前的版本？

```bash
git log --oneline -10
git reset --hard <commit-hash>
sudo systemctl restart crm
```

### Q5: 如何完全卸载？

```bash
# 停止服务
sudo systemctl stop crm
sudo systemctl disable crm

# 删除服务文件
sudo rm /etc/systemd/system/crm.service
sudo systemctl daemon-reload

# 删除Nginx配置
sudo rm /etc/nginx/sites-enabled/crm
sudo rm /etc/nginx/sites-available/crm
sudo systemctl restart nginx

# 删除日志
sudo rm -rf /var/log/crm
```

---

## 🎉 总结

### Ubuntu直接部署的优势

1. ✅ **更新速度快** - 5-10秒即可完成更新
2. ✅ **资源占用低** - 不需要Docker容器
3. ✅ **操作简单** - 只需重启服务
4. ✅ **调试方便** - 直接查看日志
5. ✅ **适合快速迭代** - 频繁更新代码

### 适用场景

- ✅ 单一应用部署
- ✅ 需要频繁更新代码
- ✅ 资源有限的服务器
- ✅ 开发/测试环境

---

**最后更新**: 2025-01-02  
**版本**: 1.0

