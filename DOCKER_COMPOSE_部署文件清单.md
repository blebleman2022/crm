# Docker Compose 部署文件清单

## 📋 必需文件（核心）

### 1. Docker配置文件 ⭐⭐⭐

| 文件名 | 用途 | 必需性 |
|--------|------|--------|
| `docker-compose.yml` | Docker编排配置 | ✅ 必需 |
| `Dockerfile` | Docker镜像构建文件 | ✅ 必需 |
| `.dockerignore` | Docker构建忽略文件 | ⭐ 推荐 |

### 2. 应用核心文件 ⭐⭐⭐

| 文件名 | 用途 | 必需性 |
|--------|------|--------|
| `run.py` | 应用启动入口 | ✅ 必需 |
| `config.py` | 应用配置文件 | ✅ 必需 |
| `models.py` | 数据模型定义 | ✅ 必需 |
| `requirements.txt` | Python依赖列表 | ✅ 必需 |
| `gunicorn.conf.py` | Gunicorn配置 | ⭐ 推荐 |

### 3. 应用代码目录 ⭐⭐⭐

| 目录名 | 用途 | 必需性 |
|--------|------|--------|
| `routes/` | 路由模块 | ✅ 必需 |
| `templates/` | HTML模板 | ✅ 必需 |
| `static/` | 静态资源 | ✅ 必需 |
| `utils/` | 工具函数 | ✅ 必需 |

### 4. 数据持久化目录 ⭐⭐⭐

| 目录名 | 用途 | 必需性 | 说明 |
|--------|------|--------|------|
| `instance/` | 数据库文件 | ✅ 必需 | 需要挂载到容器 |
| `logs/` | 日志文件 | ⭐ 推荐 | 需要挂载到容器 |

---

## 📦 可选文件（辅助）

### 1. 部署脚本 ⭐⭐

| 文件名 | 用途 | 必需性 |
|--------|------|--------|
| `deploy.sh` | 一键部署脚本 | ⭐ 推荐 |
| `check-config.py` | 配置检查脚本 | ⭐ 推荐 |

### 2. 文档文件 ⭐

| 文件名 | 用途 | 必需性 |
|--------|------|--------|
| `README.md` | 项目说明 | ⭐ 推荐 |
| `CONFIG.md` | 配置说明 | ⭐ 推荐 |
| `REQUIREMENTS.md` | 依赖说明 | ⭐ 推荐 |

---

## 🗂️ 完整文件清单

### 最小部署文件集（必需）

```
crm/
├── docker-compose.yml          # Docker编排配置
├── Dockerfile                  # Docker镜像构建
├── run.py                      # 应用入口
├── config.py                   # 应用配置
├── models.py                   # 数据模型
├── requirements.txt            # Python依赖
├── gunicorn.conf.py           # Gunicorn配置
├── communication_utils.py      # 通信工具
├── routes/                     # 路由模块
│   ├── __init__.py
│   ├── admin.py
│   ├── auth.py
│   ├── config.py
│   ├── consultations.py
│   ├── customers.py
│   ├── delivery.py
│   ├── leads.py
│   └── query.py
├── templates/                  # HTML模板
│   ├── admin/
│   ├── auth/
│   ├── components/
│   ├── config/
│   ├── consultations/
│   ├── customers/
│   ├── delivery/
│   ├── errors/
│   ├── leads/
│   ├── partials/
│   ├── query/
│   └── base.html
├── static/                     # 静态资源
│   └── images/
├── utils/                      # 工具函数
│   ├── __init__.py
│   ├── exam_calculator.py
│   ├── permissions.py
│   └── validators.py
├── instance/                   # 数据库目录（需创建）
└── logs/                       # 日志目录（需创建）
```

### 推荐部署文件集（包含辅助文件）

```
crm/
├── [上述所有必需文件]
├── .dockerignore              # Docker构建忽略
├── deploy.sh                  # 一键部署脚本
├── check-config.py            # 配置检查脚本
├── README.md                  # 项目说明
├── CONFIG.md                  # 配置说明
└── REQUIREMENTS.md            # 依赖说明
```

---

## 📄 关键文件内容说明

### 1. docker-compose.yml

```yaml
services:
  crm-app:
    build: .
    container_name: crm-app
    restart: unless-stopped
    ports:
      - "5000:5000"
    environment:
      - FLASK_ENV=development
      - SECRET_KEY=edu-crm-secret-key-2024
      - DATABASE_URL=sqlite:////app/instance/edu_crm.db
    volumes:
      - ./instance:/app/instance
      - ./logs:/app/logs
```

**关键配置**:
- ✅ 端口映射: 5000:5000
- ✅ 数据库绝对路径: `/app/instance/edu_crm.db`
- ✅ 卷挂载: instance和logs目录

### 2. Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 配置pip国内镜像源
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

# 安装Python依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 创建必要目录
RUN mkdir -p instance logs

EXPOSE 5000

CMD ["python", "run.py"]
```

**关键步骤**:
- ✅ 使用Python 3.11-slim基础镜像
- ✅ 配置国内pip镜像源
- ✅ 安装依赖
- ✅ 创建必要目录

### 3. .dockerignore

```
# 排除不需要的文件
.git
__pycache__/
*.pyc
venv/
.vscode/
.idea/
*.log
*.md
*.sh
.env
```

**作用**: 减小Docker镜像大小，加快构建速度

---

## 🚀 部署步骤

### 方法1: 使用部署脚本（推荐）

```bash
# 1. 克隆项目
git clone https://github.com/blebleman2022/crm.git
cd crm

# 2. 执行部署脚本
bash deploy.sh
```

### 方法2: 手动部署

```bash
# 1. 克隆项目
git clone https://github.com/blebleman2022/crm.git
cd crm

# 2. 创建必要目录
mkdir -p instance logs

# 3. 构建并启动
docker compose build --no-cache
docker compose up -d

# 4. 查看日志
docker compose logs -f
```

---

## ✅ 部署前检查清单

### 文件检查

- [ ] docker-compose.yml 存在
- [ ] Dockerfile 存在
- [ ] run.py 存在
- [ ] config.py 存在
- [ ] models.py 存在
- [ ] requirements.txt 存在
- [ ] routes/ 目录存在
- [ ] templates/ 目录存在
- [ ] utils/ 目录存在

### 目录检查

- [ ] instance/ 目录已创建
- [ ] logs/ 目录已创建

### 配置检查

- [ ] docker-compose.yml 中 DATABASE_URL 使用绝对路径
- [ ] docker-compose.yml 中 volumes 正确挂载
- [ ] requirements.txt 包含 Pillow
- [ ] config.py 使用绝对路径

### 运行检查脚本

```bash
python check-config.py
```

---

## 📊 文件大小参考

| 文件/目录 | 大小 | 说明 |
|-----------|------|------|
| docker-compose.yml | ~500B | Docker编排配置 |
| Dockerfile | ~300B | 镜像构建文件 |
| requirements.txt | ~500B | Python依赖 |
| routes/ | ~200KB | 路由代码 |
| templates/ | ~500KB | HTML模板 |
| static/ | ~100KB | 静态资源 |
| **总计（不含数据）** | **~1MB** | 代码文件总大小 |

---

## 🔍 常见问题

### Q1: 需要上传数据库文件吗？

**A**: 不需要。数据库文件在 `instance/` 目录中，通过卷挂载持久化。首次部署时会自动创建。

### Q2: 需要上传虚拟环境吗？

**A**: 不需要。Docker容器内会自动安装依赖，不需要上传 `venv/` 目录。

### Q3: 需要上传日志文件吗？

**A**: 不需要。日志文件在 `logs/` 目录中，通过卷挂载持久化。

### Q4: 需要上传 .git 目录吗？

**A**: 不需要。使用 `git clone` 会自动包含，手动上传时可以排除。

---

## 📝 总结

### 必需文件（13个核心文件 + 4个目录）

**配置文件（3个）**:
1. docker-compose.yml
2. Dockerfile
3. .dockerignore

**应用文件（4个）**:
4. run.py
5. config.py
6. models.py
7. requirements.txt

**辅助文件（2个）**:
8. gunicorn.conf.py
9. communication_utils.py

**代码目录（4个）**:
10. routes/
11. templates/
12. static/
13. utils/

**数据目录（2个）**:
14. instance/ (需创建)
15. logs/ (需创建)

### 推荐文件（额外3个）

16. deploy.sh (部署脚本)
17. check-config.py (检查脚本)
18. README.md (说明文档)

---

**快速检查命令**:
```bash
python check-config.py
```

**一键部署命令**:
```bash
bash deploy.sh
```

