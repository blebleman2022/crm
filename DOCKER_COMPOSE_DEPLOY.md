# Docker Compose 部署指南

## 🚀 快速部署

### 方法1：一键部署（推荐）
```bash
chmod +x deploy-compose.sh
./deploy-compose.sh
```

### 方法2：手动部署
```bash
# 1. 停止现有服务
docker-compose -f docker-compose.prod.yml down

# 2. 构建并启动
docker-compose -f docker-compose.prod.yml up -d --build

# 3. 查看状态
docker-compose -f docker-compose.prod.yml ps
```

## 📋 部署前检查

### ✅ 必需文件
- [x] `docker-compose.prod.yml` - 生产环境配置
- [x] `Dockerfile` - 镜像构建文件
- [x] `instance/edu_crm.db` - 数据库文件
- [x] `.env` 或 `.env.production` - 环境变量

### ✅ 环境要求
- Docker Engine 20.10+
- Docker Compose 2.0+
- 至少512MB可用内存
- 端口80可用

## 🔧 配置说明

### 环境变量配置
复制并修改环境配置文件：
```bash
cp .env.production .env
# 编辑 .env 文件，修改SECRET_KEY等配置
```

### 数据库配置
- **数据库文件**: `./instance/edu_crm.db`
- **挂载方式**: 绑定挂载（确保数据持久化）
- **权限**: 容器内用户ID 1000

### 端口配置
- **应用端口**: 80 (HTTP)
- **管理工具**: 8080 (Adminer，可选)

## 📊 管理命令

### 基本操作
```bash
# 启动服务
./deploy-compose.sh start

# 停止服务
./deploy-compose.sh stop

# 重启服务
./deploy-compose.sh restart

# 查看状态
./deploy-compose.sh status

# 查看日志
./deploy-compose.sh logs
```

### Docker Compose 原生命令
```bash
# 查看服务状态
docker-compose -f docker-compose.prod.yml ps

# 查看日志
docker-compose -f docker-compose.prod.yml logs -f

# 重启特定服务
docker-compose -f docker-compose.prod.yml restart crm-app

# 进入容器
docker-compose -f docker-compose.prod.yml exec crm-app bash

# 停止并删除所有服务
docker-compose -f docker-compose.prod.yml down
```

## 🔍 故障排查

### 常见问题

1. **端口被占用**
   ```bash
   # 检查端口占用
   netstat -tlnp | grep :80
   # 或使用其他端口
   ```

2. **数据库权限问题**
   ```bash
   # 检查数据库文件权限
   ls -la instance/
   # 修复权限
   chmod 666 instance/edu_crm.db
   ```

3. **容器启动失败**
   ```bash
   # 查看详细日志
   docker-compose -f docker-compose.prod.yml logs crm-app
   ```

4. **健康检查失败**
   ```bash
   # 手动测试
   curl http://localhost/health
   curl http://localhost/auth/login
   ```

### 日志位置
- **应用日志**: `./logs/`
- **容器日志**: `docker-compose logs`
- **系统日志**: `/var/log/docker/`

## 🛡️ 安全建议

1. **修改默认密钥**
   ```bash
   # 生成新的SECRET_KEY
   openssl rand -hex 32
   ```

2. **使用HTTPS**
   - 配置SSL证书
   - 启用nginx profile

3. **限制访问**
   - 配置防火墙
   - 使用VPN或内网访问

## 📈 性能优化

### 资源限制
在 `docker-compose.prod.yml` 中已配置：
- 内存限制: 512MB
- CPU限制: 1核心

### 扩展配置
```bash
# 增加worker数量
docker-compose -f docker-compose.prod.yml exec crm-app \
  sed -i 's/workers = 2/workers = 4/' gunicorn.conf.py

# 重启应用
docker-compose -f docker-compose.prod.yml restart crm-app
```

## 🔄 更新部署

### 应用更新
```bash
# 1. 停止服务
docker-compose -f docker-compose.prod.yml down

# 2. 拉取最新代码
git pull

# 3. 重新构建并启动
docker-compose -f docker-compose.prod.yml up -d --build
```

### 数据库备份
```bash
# 创建备份
cp instance/edu_crm.db instance/edu_crm_backup_$(date +%Y%m%d_%H%M%S).db

# 或使用脚本
./simple-migrate.sh
```

## 🌐 访问应用

部署成功后，访问：
- **主应用**: http://YOUR_SERVER_IP
- **数据库管理**: http://YOUR_SERVER_IP:8080 (如果启用)

默认管理员账号：
- 手机号: 13800138000
- 角色: admin
