# ECS服务器部署指南（非Docker方式）

## 📋 前提条件

- Ubuntu 20.04+ 服务器
- Python 3.8+
- Git
- 已配置好SSH访问

## 🚀 部署步骤

### 1. 在ECS服务器上拉取最新代码

```bash
# SSH登录到ECS服务器
ssh your-user@your-ecs-ip

# 进入项目目录
cd /path/to/CRM1

# 拉取最新代码（从GitHub或Gitee）
git pull origin master
# 或
git pull github main
```

### 2. 激活虚拟环境

```bash
# 如果虚拟环境不存在，先创建
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate
```

### 3. 安装/更新依赖（使用国内镜像）

```bash
# 使用清华镜像源安装依赖
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn
```

### 4. 验证配置修复

```bash
# 测试配置导入
python -c "from run import app; print('✅ 配置加载成功')"

# 如果看到 "✅ 配置加载成功"，说明修复成功
```

### 5. 重启服务

#### 方式1：使用systemd服务（推荐）

```bash
# 重启CRM服务
sudo systemctl restart crm

# 检查服务状态
sudo systemctl status crm

# 查看服务日志
sudo journalctl -u crm -f
```

#### 方式2：使用项目脚本

```bash
# 如果有restart-server.sh脚本
./restart-server.sh

# 或使用rollback-server.sh（如果需要回滚）
./rollback-server.sh
```

#### 方式3：手动重启Gunicorn

```bash
# 查找Gunicorn进程
ps aux | grep gunicorn

# 杀死旧进程
pkill -f gunicorn

# 启动新进程
cd /path/to/CRM1
source venv/bin/activate
gunicorn -c gunicorn.conf.py run:app &
```

### 6. 验证部署

```bash
# 检查健康检查端点
curl http://localhost:5000/health

# 应该返回类似：
# {"status":"healthy","service":"EduConnect CRM","version":"1.0.0","database":"connected"}

# 检查登录页面
curl http://localhost:5000/auth/login

# 应该返回HTML页面
```

### 7. 检查日志

```bash
# 查看应用日志
tail -f logs/crm.log

# 查看Gunicorn日志（如果使用systemd）
sudo journalctl -u crm -n 100 --no-pager
```

## 🔧 配置说明

### 环境变量

在ECS服务器上，确保设置了正确的环境变量：

```bash
# 编辑 ~/.bashrc 或 /etc/environment
export FLASK_ENV=production
export SECRET_KEY=your-production-secret-key
export DATABASE_URL=sqlite:///instance/edu_crm.db
```

### Systemd服务配置

如果使用systemd管理服务，配置文件通常在：`/etc/systemd/system/crm.service`

```ini
[Unit]
Description=EduConnect CRM Application
After=network.target

[Service]
Type=notify
User=your-user
Group=your-group
WorkingDirectory=/path/to/CRM1
Environment="FLASK_ENV=production"
Environment="PATH=/path/to/CRM1/venv/bin"
ExecStart=/path/to/CRM1/venv/bin/gunicorn -c gunicorn.conf.py run:app
ExecReload=/bin/kill -s HUP $MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

## ⚠️ 常见问题

### 问题1：ModuleNotFoundError: No module named 'config_production'

**原因**：使用了旧版本的代码

**解决**：
```bash
git pull origin master  # 拉取最新代码
python -c "from run import app; print('测试')"  # 验证修复
```

### 问题2：服务启动失败

**检查步骤**：
```bash
# 1. 检查Python版本
python3 --version  # 应该是3.8+

# 2. 检查虚拟环境
source venv/bin/activate
which python  # 应该指向venv中的python

# 3. 检查依赖
pip list | grep Flask

# 4. 检查配置
python -c "from config import ProductionConfig; print(ProductionConfig)"
```

### 问题3：数据库连接失败

**检查步骤**：
```bash
# 1. 检查数据库文件
ls -la instance/edu_crm.db

# 2. 检查权限
chmod 666 instance/edu_crm.db
chmod 755 instance/

# 3. 初始化数据库（如果需要）
python run.py init-db
```

### 问题4：端口被占用

**解决**：
```bash
# 查看端口占用
sudo netstat -tlnp | grep 5000

# 杀死占用进程
sudo kill -9 <PID>

# 或修改gunicorn.conf.py中的端口
```

## 📊 监控和维护

### 日志监控

```bash
# 实时查看日志
tail -f logs/crm.log

# 查看错误日志
grep ERROR logs/crm.log

# 查看最近的访问
tail -100 logs/crm.log | grep "GET\|POST"
```

### 性能监控

```bash
# 查看进程资源使用
ps aux | grep gunicorn

# 查看内存使用
free -h

# 查看磁盘使用
df -h
```

### 数据库备份

```bash
# 手动备份
cp instance/edu_crm.db backups/edu_crm_$(date +%Y%m%d_%H%M%S).db

# 使用备份脚本（如果有）
./backup-db.sh

# 设置定时备份（crontab）
crontab -e
# 添加：0 3 * * * /path/to/CRM1/backup-db.sh
```

## 🔄 回滚步骤

如果新版本有问题，可以回滚到之前的版本：

```bash
# 1. 查看提交历史
git log --oneline -10

# 2. 回滚到指定版本
git reset --hard <commit-hash>

# 3. 重启服务
sudo systemctl restart crm

# 4. 验证
curl http://localhost:5000/health
```

## 📝 更新日志

### 2025-01-XX - 配置修复
- 修复了config_production导入错误
- 统一使用config.py中的配置类
- 添加了详细的部署文档

## 🆘 紧急联系

如果遇到紧急问题：
1. 查看日志：`tail -f logs/crm.log`
2. 检查服务状态：`sudo systemctl status crm`
3. 尝试重启：`sudo systemctl restart crm`
4. 如果无法解决，回滚到上一个稳定版本

## ✅ 部署检查清单

- [ ] 代码已拉取到最新版本
- [ ] 虚拟环境已激活
- [ ] 依赖已安装/更新
- [ ] 配置导入测试通过
- [ ] 服务已重启
- [ ] 健康检查通过
- [ ] 登录页面可访问
- [ ] 日志无错误
- [ ] 数据库已备份

---

**部署完成后，请访问：** `http://your-ecs-ip:5000`

**默认管理员账号：**
- 手机号：13800138000
- 验证码：任意6位数字（开发环境）

