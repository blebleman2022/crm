# EduConnect CRM Systemd 服务管理指南

## 📋 快速参考

### 一键安装 Systemd 服务

```bash
cd ~/crm
sudo bash install_systemd_service.sh
```

### 常用命令

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

# 查看最近100条日志
sudo journalctl -u crm -n 100

# 禁用开机自启
sudo systemctl disable crm

# 启用开机自启
sudo systemctl enable crm
```

---

## 🚀 部署更新流程

### 标准部署流程（推荐）

```bash
# 1. 进入项目目录
cd ~/crm

# 2. 拉取最新代码
git pull origin master

# 3. 执行部署脚本（自动使用 systemctl 重启）
bash deploy_update.sh
```

**就这么简单！** 部署脚本会自动：
- ✅ 备份数据库
- ✅ 停止服务（使用 `systemctl stop crm`）
- ✅ 更新代码和依赖
- ✅ 执行数据库迁移
- ✅ 重启服务（使用 `systemctl restart crm`）

### 快速重启（不更新代码）

```bash
sudo systemctl restart crm
```

---

## 🔍 故障排查

### 查看服务状态

```bash
sudo systemctl status crm
```

输出示例：
```
● crm.service - EduConnect CRM Application
   Loaded: loaded (/etc/systemd/system/crm.service; enabled; vendor preset: enabled)
   Active: active (running) since Wed 2025-10-23 10:30:00 CST; 5min ago
 Main PID: 12345 (gunicorn)
   Status: "Gunicorn arbiter booted"
    Tasks: 5 (limit: 4915)
   Memory: 150.2M
   CGroup: /system.slice/crm.service
           ├─12345 /root/crm/venv/bin/python /root/crm/venv/bin/gunicorn...
           ├─12346 /root/crm/venv/bin/python /root/crm/venv/bin/gunicorn...
           ├─12347 /root/crm/venv/bin/python /root/crm/venv/bin/gunicorn...
           ├─12348 /root/crm/venv/bin/python /root/crm/venv/bin/gunicorn...
           └─12349 /root/crm/venv/bin/python /root/crm/venv/bin/gunicorn...
```

### 查看日志

**查看 systemd 日志（推荐）：**

```bash
# 查看最近的日志
sudo journalctl -u crm -n 100

# 实时查看日志
sudo journalctl -u crm -f

# 查看今天的日志
sudo journalctl -u crm --since today

# 查看最近1小时的日志
sudo journalctl -u crm --since "1 hour ago"
```

**查看应用日志文件：**

```bash
# 应用日志
tail -f ~/crm/logs/app.log

# 访问日志
tail -f ~/crm/logs/access.log

# 错误日志
tail -f ~/crm/logs/error.log
```

### 常见问题

#### 1. 服务启动失败

```bash
# 查看详细错误信息
sudo systemctl status crm -l

# 查看完整日志
sudo journalctl -u crm -n 200
```

常见原因：
- 端口被占用（检查是否有其他进程占用 5000 端口）
- 虚拟环境问题（检查 `/root/crm/venv` 是否存在）
- 数据库文件权限问题

#### 2. 端口被占用

```bash
# 查看 5000 端口占用情况
sudo lsof -i :5000

# 或者
sudo netstat -tlnp | grep 5000

# 如果有其他进程占用，停止它
sudo kill -9 <PID>
```

#### 3. 服务无法停止

```bash
# 强制停止服务
sudo systemctl kill crm

# 或者直接杀死进程
sudo pkill -9 -f "gunicorn.*run:app"
```

---

## 🔧 高级配置

### 修改服务配置

编辑服务文件：

```bash
sudo nano /etc/systemd/system/crm.service
```

修改后重新加载配置：

```bash
sudo systemctl daemon-reload
sudo systemctl restart crm
```

### 常见配置修改

#### 修改工作进程数

在 `crm.service` 中找到：
```
--workers 4 \
```

改为：
```
--workers 8 \
```

#### 修改端口

在 `crm.service` 中找到：
```
--bind 0.0.0.0:5000 \
```

改为：
```
--bind 0.0.0.0:8000 \
```

#### 修改超时时间

在 `crm.service` 中找到：
```
--timeout 120 \
```

改为：
```
--timeout 300 \
```

---

## 📊 性能监控

### 查看资源使用情况

```bash
# 查看服务的资源使用
sudo systemctl status crm

# 查看详细的资源统计
sudo systemd-cgtop
```

### 查看进程信息

```bash
# 查看所有 Gunicorn 进程
ps aux | grep gunicorn

# 查看进程树
pstree -p $(pgrep -f "gunicorn.*run:app" | head -1)
```

---

## 🔄 卸载 Systemd 服务

如果需要卸载 systemd 服务，恢复手动管理：

```bash
# 1. 停止并禁用服务
sudo systemctl stop crm
sudo systemctl disable crm

# 2. 删除服务文件
sudo rm /etc/systemd/system/crm.service

# 3. 重新加载 systemd 配置
sudo systemctl daemon-reload

# 4. 手动启动服务
cd ~/crm
source venv/bin/activate
export FLASK_ENV=production
export DATABASE_URL="sqlite:///$(pwd)/instance/edu_crm.db"
nohup gunicorn -w 4 -b 0.0.0.0:5000 --timeout 120 \
    --access-logfile logs/access.log \
    --error-logfile logs/error.log \
    run:app > logs/app.log 2>&1 &
```

---

## ✅ 最佳实践

1. **使用 systemd 管理服务**：开机自启、自动重启、统一日志
2. **定期查看日志**：`sudo journalctl -u crm -n 100`
3. **部署前备份**：部署脚本会自动备份，但重要操作前手动备份更安全
4. **监控资源使用**：定期检查 CPU、内存使用情况
5. **使用部署脚本**：避免手动操作，减少人为错误

---

## 📞 技术支持

如有问题，请查看：
- 服务状态：`sudo systemctl status crm`
- 系统日志：`sudo journalctl -u crm -n 100`
- 应用日志：`tail -100 ~/crm/logs/app.log`

