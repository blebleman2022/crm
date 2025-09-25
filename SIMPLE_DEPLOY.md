# 开发环境简化部署指南

## 📋 需要的文件

只需要这3个文件：
- ✅ **Dockerfile** (已存在)
- ✅ **docker-compose.yml** (已存在) 
- ✅ **instance/edu_crm.db** (数据库文件)

## 🚀 部署步骤

### 1. 准备云服务器

```bash
# 安装Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo systemctl start docker
sudo systemctl enable docker
```

### 2. 上传项目文件

```bash
# 方式1：Git克隆
git clone your-repo-url
cd crm

# 方式2：文件上传
scp -r ./crm user@server:/home/user/
```

### 3. 检查必需文件

```bash
# 确保这些文件存在
ls -la Dockerfile
ls -la docker-compose.yml  
ls -la instance/edu_crm.db
```

### 4. 部署前检查（推荐）

```bash
# 运行部署前检查脚本
chmod +x pre-deploy-check.sh
./pre-deploy-check.sh

# 如果有问题，尝试自动修复
./pre-deploy-check.sh fix
```

### 5. 手动设置权限（如果检查脚本失败）

```bash
# 数据库文件权限
chmod 666 instance/edu_crm.db

# 创建日志目录
mkdir -p logs
chmod 755 logs
```

### 6. 启动服务

```bash
# 构建并启动
docker compose up -d --build

# 查看状态
docker compose ps

# 查看日志
docker compose logs -f
```

## 🌐 访问应用

- **访问地址**: http://服务器IP:5000
- **本地测试**: http://localhost:5000
- **默认管理员**: 手机号 13800138000

## 🔧 常用命令

```bash
# 启动服务
docker compose up -d

# 停止服务  
docker compose down

# 重启服务
docker compose restart

# 查看日志
docker compose logs -f crm-app

# 进入容器
docker compose exec crm-app bash
```

## ⚠️ 潜在部署风险及解决方案

### � 高风险问题

#### 1. 启动脚本冲突
**问题**: Dockerfile使用`python run.py`，但docker-compose.yml挂载了整个目录，可能导致启动脚本冲突
```bash
# 解决方案：确保启动命令一致
# 方式1：修改Dockerfile最后一行
CMD ["python", "run.py"]

# 方式2：或者在docker-compose.yml中覆盖
command: ["python", "run.py"]
```

#### 2. 数据库文件权限
**问题**: SQLite数据库文件权限可能导致写入失败
```bash
# 必须执行的权限设置
chmod 666 instance/edu_crm.db
chmod 755 instance logs

# 检查权限
ls -la instance/edu_crm.db
# 应该显示: -rw-rw-rw- 1 user user size date edu_crm.db
```

#### 3. 目录挂载问题
**问题**: docker-compose.yml中的卷挂载可能覆盖容器内的文件
```bash
# 当前配置可能有问题的地方：
volumes:
  - .:/app  # 这会覆盖容器内的所有文件

# 建议修改为只挂载必要目录：
volumes:
  - ./instance:/app/instance
  - ./logs:/app/logs
  # 移除 - .:/app 这行
```

### 🟡 中风险问题

#### 4. 端口冲突
```bash
# 检查端口占用
sudo netstat -tlnp | grep :5000
sudo lsof -i :5000

# 如果端口被占用，修改docker-compose.yml
ports:
  - "8000:5000"  # 改为其他端口
```

#### 5. 内存不足
```bash
# 检查系统内存
free -h

# 如果内存不足，添加资源限制
deploy:
  resources:
    limits:
      memory: 256M
```

#### 6. 网络连接问题
```bash
# 测试网络连接
curl -f http://localhost:5000/auth/login

# 如果失败，检查防火墙
sudo ufw status
sudo ufw allow 5000
```

## 🔍 故障排查步骤

### 第一步：检查容器状态
```bash
# 查看容器是否启动
docker compose ps

# 查看详细日志
docker compose logs -f crm-app

# 进入容器调试
docker compose exec crm-app bash
```

### 第二步：检查数据库
```bash
# 在容器内检查数据库
docker compose exec crm-app python -c "
from run import app
from models import db, User
with app.app_context():
    print('用户数量:', User.query.count())
"
```

### 第三步：检查网络
```bash
# 测试应用响应
curl -v http://localhost:5000/auth/login

# 检查端口监听
docker compose exec crm-app netstat -tlnp
```

## 📊 数据备份

```bash
# 备份数据库
cp instance/edu_crm.db backups/edu_crm_$(date +%Y%m%d_%H%M%S).db
```

## 🔄 更新部署

```bash
# 1. 停止服务
docker compose down

# 2. 拉取最新代码
git pull

# 3. 重新启动
docker compose up -d --build
```

---

**就这么简单！** 开发环境部署只需要现有的 `Dockerfile` 和 `docker-compose.yml` 文件即可。
