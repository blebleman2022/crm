# EduConnect CRM 云服务器部署指南

## 📋 部署概述

本指南适用于在云服务器上部署 EduConnect CRM 系统，使用与本地开发环境相同的配置方式。

## 🔧 系统要求

### 服务器配置
- **操作系统**: Ubuntu 20.04+ / CentOS 7+ / Debian 10+
- **内存**: 最低 2GB，推荐 4GB+
- **存储**: 最低 10GB 可用空间
- **网络**: 开放 5000 端口（与本地开发环境一致）

### 软件依赖
- Docker 20.10+
- Docker Compose 2.0+
- Git

## 🚀 部署步骤

### 1. 准备服务器环境

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装 Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# 安装 Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 将用户添加到 docker 组
sudo usermod -aG docker $USER

# 重新登录以使组权限生效
exit
```

### 2. 部署应用

```bash
# 克隆项目
git clone <your-repository-url>
cd CRM1

# 创建必要目录
mkdir -p instance logs backups

# 使用现有的 Docker Compose 配置启动
docker-compose up -d

# 查看启动状态
docker-compose ps
docker-compose logs
```

### 3. 访问应用

部署完成后，通过浏览器访问：
```
http://your-server-ip:5000
```

默认管理员账号：
- 用户名: `admin`
- 密码: `admin123`

## ⚙️ 配置说明

### 数据库配置

系统使用 SQLite 数据库，配置与本地开发环境完全一致：
```
DATABASE_URL=sqlite:///instance/edu_crm.db
```

数据文件位于：`./instance/edu_crm.db`

### Docker 配置

使用现有的 `docker-compose.yml` 文件，配置如下：
- **端口映射**: 5000:5000（与本地开发环境一致）
- **环境**: development
- **数据持久化**: `./instance:/app/instance`
- **日志持久化**: `./logs:/app/logs`

## 📁 文件结构

```
CRM1/
├── .env                    # 生产环境变量
├── docker-compose.prod.yml # 生产环境 Docker 配置
├── deploy-cloud.sh         # 一键部署脚本
├── instance/               # 数据库文件目录
├── logs/                   # 日志文件目录
├── backups/               # 备份文件目录
└── ...
```

## 🔧 管理命令

### 服务管理
```bash
# 查看服务状态
docker ps

# 查看日志
docker logs crm-production

# 重启服务
docker restart crm-production

# 停止服务
docker-compose -f docker-compose.prod.yml down

# 重新部署
docker-compose -f docker-compose.prod.yml up -d --build
```

### 数据库管理
```bash
# 备份数据库
cp instance/edu_crm.db backups/edu_crm_$(date +%Y%m%d_%H%M%S).db

# 查看数据库大小
ls -lh instance/edu_crm.db
```

### 日志管理
```bash
# 查看应用日志
docker logs crm-production

# 查看日志文件
tail -f logs/crm.log

# 清理旧日志
find logs/ -name "*.log.*" -mtime +7 -delete
```

## 🛠️ 故障排除

### 常见问题

1. **端口被占用**
   ```bash
   # 检查端口占用
   netstat -tlnp | grep :80
   
   # 修改端口（在 docker-compose.prod.yml 中）
   ports:
     - "8080:80"  # 改为其他端口
   ```

2. **权限问题**
   ```bash
   # 检查目录权限
   ls -la instance/ logs/ backups/
   
   # 修复权限
   sudo chown -R $USER:$USER instance/ logs/ backups/
   chmod 755 instance/ logs/ backups/
   ```

3. **数据库文件不存在**
   ```bash
   # 检查数据库文件
   ls -la instance/
   
   # 重新初始化（会清空数据）
   docker exec crm-production python run.py init-db
   ```

### 性能优化

1. **调整 Gunicorn 工作进程数**
   ```bash
   # 在 .env 文件中修改
   GUNICORN_WORKERS=4  # 根据 CPU 核心数调整
   ```

2. **配置日志轮转**
   ```bash
   # 在 docker-compose.prod.yml 中已配置
   logging:
     options:
       max-size: "10m"
       max-file: "5"
   ```

## 🔒 安全建议

1. **修改默认密钥**: 必须修改 `.env` 中的 `SECRET_KEY`
2. **定期备份**: 设置定时任务备份数据库
3. **监控日志**: 定期检查应用日志
4. **更新系统**: 定期更新服务器系统和 Docker
5. **网络安全**: 配置防火墙，只开放必要端口

## 📞 技术支持

如遇到部署问题，请检查：
1. 服务器系统要求是否满足
2. Docker 和 Docker Compose 是否正确安装
3. 端口是否被占用
4. 防火墙设置是否正确
5. 日志文件中的错误信息
