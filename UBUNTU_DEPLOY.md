# Ubuntu云服务器Docker部署指南

## 🚀 一步步部署教程

### 第一步：准备Ubuntu服务器

1. **更新系统**
```bash
sudo apt update && sudo apt upgrade -y
```

2. **安装Docker**
```bash
# 安装Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# 启动Docker服务
sudo systemctl start docker
sudo systemctl enable docker

# 将当前用户添加到docker组（可选，避免每次使用sudo）
sudo usermod -aG docker $USER
# 注意：添加用户组后需要重新登录才能生效
```

3. **验证Docker Compose**
```bash
# 新版Docker已内置Compose插件，直接验证
docker compose version

# 如果上述命令失败，则安装独立的docker-compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
docker-compose --version
```

### 第二步：获取项目代码

1. **安装Git（如果未安装）**
```bash
sudo apt install git -y
```

2. **克隆项目**
```bash
# 克隆项目到服务器
git clone https://gitee.com/blebleman/crm.git
cd crm
```

### 第三步：检查项目文件

1. **确认必要文件存在**
```bash
# 检查关键文件
ls -la docker-compose.yml
ls -la Dockerfile
ls -la instance/edu_crm.db
ls -la start.sh
```

2. **设置文件权限**
```bash
# 确保启动脚本有执行权限
chmod +x start.sh

# 确保数据库文件权限正确
chmod 666 instance/edu_crm.db

# 创建日志目录
mkdir -p logs
chmod 755 logs
```

3. **检查Docker Compose命令**
```bash
# 优先使用新版命令（推荐）
docker compose version

# 如果上述命令失败，使用旧版命令
docker-compose --version
```

### 第四步：配置环境变量（可选）

1. **创建环境配置文件**
```bash
# 复制环境变量模板
cp .env.example .env

# 编辑环境变量（可选）
nano .env
```

2. **设置SECRET_KEY（推荐）**
```bash
# 生成随机密钥
openssl rand -hex 32

# 将生成的密钥添加到.env文件
echo "SECRET_KEY=你生成的密钥" >> .env
```

### 第五步：构建和启动服务

1. **构建Docker镜像**
```bash
# 新版Docker命令（推荐）
docker compose build

# 或使用旧版命令
docker-compose build
```

2. **启动服务**
```bash
# 新版Docker命令（推荐）
docker compose up -d

# 或使用旧版命令
docker-compose up -d
```

3. **检查服务状态**
```bash
# 新版Docker命令（推荐）
docker compose ps
docker compose logs -f

# 或使用旧版命令
docker-compose ps
docker-compose logs -f
```

### 第六步：验证部署

1. **检查服务是否正常运行**
```bash
# 检查容器状态
docker ps

# 测试应用是否响应
curl http://localhost/auth/login
```

2. **在浏览器中访问**
```
http://你的服务器IP地址
```

### 第七步：防火墙配置（如果需要）

1. **开放80端口**
```bash
# Ubuntu UFW防火墙
sudo ufw allow 80
sudo ufw enable

# 或者使用iptables
sudo iptables -A INPUT -p tcp --dport 80 -j ACCEPT
```

## 🔧 常用管理命令

### 服务管理
```bash
# 启动服务（新版命令）
docker compose up -d

# 停止服务（新版命令）
docker compose down

# 重启服务（新版命令）
docker compose restart

# 查看状态（新版命令）
docker compose ps

# 查看日志（新版命令）
docker compose logs -f crm-app

# 如果新版命令不可用，使用旧版命令：
# docker-compose up -d
# docker-compose down
# docker-compose restart
# docker-compose ps
# docker-compose logs -f crm-app
```

### 更新部署
```bash
# 1. 停止服务
docker compose down

# 2. 拉取最新代码
git pull

# 3. 重新构建并启动
docker compose up -d --build

# 旧版命令替代方案：
# docker-compose down
# docker-compose up -d --build
```

### 数据库备份
```bash
# 备份数据库
cp instance/edu_crm.db instance/edu_crm_backup_$(date +%Y%m%d_%H%M%S).db
```

## 🔍 故障排查

### 常见问题

1. **端口被占用**
```bash
# 检查端口占用
sudo netstat -tlnp | grep :80
# 或者
sudo lsof -i :80
```

2. **容器启动失败**
```bash
# 查看详细日志
docker-compose logs crm-app

# 进入容器调试
docker-compose exec crm-app bash
```

3. **权限问题**
```bash
# 修复数据库权限
sudo chown -R 1000:1000 instance/
sudo chmod 666 instance/edu_crm.db
```

4. **内存不足**
```bash
# 检查系统资源
free -h
df -h
```

## 📋 默认登录信息

部署成功后，使用以下信息登录：
- **手机号**: 13800138000
- **角色**: admin

## 🛡️ 安全建议

1. **修改默认密钥**
2. **配置HTTPS**（推荐使用nginx反向代理）
3. **定期备份数据库**
4. **限制服务器访问权限**
5. **定期更新系统和Docker**

## 📞 技术支持

如果遇到问题，请检查：
1. Docker和Docker Compose版本
2. 服务器内存和磁盘空间
3. 网络连接和防火墙设置
4. 日志文件中的错误信息
