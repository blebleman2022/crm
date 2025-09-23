# 项目依赖说明

## 📦 依赖文件说明

### `requirements.txt` - 生产环境依赖
包含运行EduConnect CRM系统所需的最小依赖集合，适用于生产环境部署。

### `requirements-dev.txt` - 开发环境依赖
包含开发、测试和调试所需的额外工具，继承生产环境依赖。

## 🔧 核心依赖详解

### Web框架
- **Flask==3.0.0**: 核心Web框架，最新稳定版本
- **Werkzeug==3.0.1**: WSGI工具库，Flask的底层依赖

### 数据库
- **Flask-SQLAlchemy==3.1.1**: Flask的SQLAlchemy集成
- **SQLAlchemy==2.0.23**: Python SQL工具包和ORM

### 认证与安全
- **Flask-Login==0.6.3**: 用户会话管理
- **Flask-WTF==1.2.1**: Flask的WTForms集成，提供CSRF保护
- **WTForms==3.1.1**: 表单验证和渲染

### 配置管理
- **python-dotenv==1.0.0**: 环境变量管理

### 生产服务器
- **gunicorn==21.2.0**: Python WSGI HTTP服务器

### 核心工具
- **click==8.1.7**: 命令行接口创建工具
- **itsdangerous==2.1.2**: 安全签名工具
- **Jinja2==3.1.2**: 模板引擎
- **MarkupSafe==2.1.3**: 安全字符串处理
- **blinker==1.7.0**: 信号系统

## 🚀 安装方式

### 生产环境
```bash
pip install -r requirements.txt
```

### 开发环境
```bash
pip install -r requirements-dev.txt
```

### Docker环境
```bash
# 生产环境构建
docker build -t crm-app .

# 开发环境构建
docker build --build-arg INSTALL_DEV=true -t crm-app-dev .
```

## 📋 版本选择原则

1. **稳定性优先**: 选择经过充分测试的稳定版本
2. **安全性**: 及时更新有安全漏洞的包
3. **兼容性**: 确保包之间的版本兼容
4. **最小化**: 只包含必需的依赖，避免冗余

## 🔄 更新依赖

### 检查过期包
```bash
pip list --outdated
```

### 更新特定包
```bash
pip install --upgrade package_name==new_version
```

### 生成新的requirements
```bash
pip freeze > requirements.txt
```

## ⚠️ 注意事项

1. **版本锁定**: 所有包都锁定了具体版本，确保部署一致性
2. **安全更新**: 定期检查安全漏洞并更新相关包
3. **测试**: 更新依赖后务必进行全面测试
4. **备份**: 更新前备份当前工作的requirements文件

## 🐳 Docker优化

- 使用多阶段构建减少镜像大小
- 通过构建参数控制开发依赖安装
- 利用Docker缓存层优化构建速度
