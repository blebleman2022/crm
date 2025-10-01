# EduConnect CRM - 教育机构客户关系管理系统

基于Python Flask + SQLite开发的教育机构客户关系管理系统，专为提供课题辅导和竞赛奖项获取服务的教育机构设计，实现从线索获取到服务交付的全流程数字化管理。

## 功能特性

### 核心模块
- **用户认证系统**: 手机号免密登录，基于角色的权限控制
- **账号管理**: 管理员统一维护用户账号和权限
- **线索管理**: 学员线索录入、阶段跟踪、责任销售分配
- **客户管理**: 成交客户档案管理、班主任绑定、服务到期管理
- **交付管理**: 课题辅导和竞赛奖项两种服务的交付进度跟踪
- **基础配置**: 竞赛名称等基础数据维护

### 用户角色
- **销售管理**: 管理全量线索和客户，负责销售转化
- **班主任**: 管理分配给自己的客户交付记录
- **系统管理员**: 维护账号、基础配置，查看全量数据

## 技术栈

- **后端**: Python 3.8+, Flask 2.3+
- **数据库**: SQLite 3
- **前端**: HTML5, CSS3, JavaScript, Tailwind CSS
- **认证**: Flask-Login
- **ORM**: SQLAlchemy

## 项目结构

```
edu-crm/
├── app.py              # 应用入口文件
├── config.py           # 配置文件
├── models.py           # 数据模型
├── requirements.txt    # 依赖包列表
├── routes/            # 路由模块
│   ├── auth.py        # 认证相关路由
│   ├── admin.py       # 管理员功能路由
│   ├── leads.py       # 线索管理路由
│   ├── customers.py   # 客户管理路由
│   └── delivery.py    # 交付管理路由
├── templates/         # HTML模板
├── static/           # 静态资源
│   ├── css/          # 样式文件
│   ├── js/           # JavaScript文件
│   └── images/       # 图片资源
└── ui/               # UI设计参考文件
```

## 快速部署

### 🚀 一键部署（推荐）

```bash
# 1. 克隆项目
git clone https://github.com/blebleman2022/crm.git
cd crm

# 2. 执行一键部署脚本
./deploy.sh
```

脚本会自动：
- ✅ 检测系统环境
- ✅ 配置国内镜像源（APT、pip、Docker）
- ✅ 安装Docker环境
- ✅ 备份数据库
- ✅ 构建并启动服务
- ✅ 验证部署状态

### 📋 访问系统

部署完成后：
- **系统地址**: http://localhost:5000
- **登录页面**: http://localhost:5000/auth/login
- **默认管理员账号**: admin / admin123

### 🛠️ 常用命令

```bash
# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f

# 重启服务
docker-compose restart

# 停止服务
docker-compose down
```

### 💻 本地开发环境

如果需要本地开发：

```bash
# 1. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac

# 2. 安装依赖
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 3. 初始化数据库
python
>>> from app import app, db
>>> with app.app_context():
...     db.create_all()
>>> exit()

# 4. 运行应用
python run.py
```

### 📚 详细文档

- [部署指南](DEPLOY-CLOUD.md)
- [国内镜像源配置](CHINA-MIRRORS.md)

## 开发说明

### 数据库设计
系统包含以下核心数据表：
- `users`: 用户账号表
- `leads`: 学员线索表
- `customers`: 成交客户表
- `tutoring_deliveries`: 课题辅导交付表
- `competition_deliveries`: 竞赛奖项交付表
- `competition_names`: 竞赛名称配置表
- `login_logs`: 登录日志表

### 权限控制
- 销售管理：可查看和编辑全量线索、客户数据
- 班主任：仅可查看和编辑分配给自己的交付记录
- 管理员：拥有所有权限，负责账号和基础配置管理

## 许可证

MIT License
