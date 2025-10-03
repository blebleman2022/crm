# 部署配置修复说明

## 问题描述

在ECS服务器上部署时，应用启动失败，报错：
```
ModuleNotFoundError: No module named 'config_production'
```

## 问题原因

`run.py` 文件中的配置加载逻辑尝试导入不存在的 `config_production` 模块：

```python
# 旧代码（错误）
if config_name == 'production':
    from config_production import ProductionConfig  # ❌ 文件不存在
    app.config.from_object(ProductionConfig)
```

实际上，所有配置类（`ProductionConfig`、`DevelopmentConfig`、`TestingConfig`）都已经在 `config.py` 文件中定义。

## 修复方案

修改 `run.py` 中的配置加载逻辑，统一从 `config.py` 导入配置：

```python
# 新代码（正确）
from config import config as config_dict

# 根据环境选择配置
config_class = config_dict.get(config_name, config_dict['default'])
app.config.from_object(config_class)
config_class.init_app(app)
```

## 修复内容

### 修改文件：`run.py`

**修改位置**：第 23-34 行

**修改前**：
```python
# 加载配置
if config_name == 'production':
    from config_production import ProductionConfig
    app.config.from_object(ProductionConfig)
    ProductionConfig.init_app(app)
elif config_name == 'testing':
    from config_production import TestingConfig
    app.config.from_object(TestingConfig)
    TestingConfig.init_app(app)
else:
    from config import Config
    app.config.from_object(Config)
```

**修改后**：
```python
# 加载配置
from config import config as config_dict

# 根据环境选择配置
config_class = config_dict.get(config_name, config_dict['default'])
app.config.from_object(config_class)
config_class.init_app(app)
```

## 验证方法

### 本地验证

```bash
# 1. 测试开发环境
FLASK_ENV=development python run.py

# 2. 测试生产环境
FLASK_ENV=production python -c "from run import app; print('✅ 成功')"

# 3. 测试Gunicorn导入
gunicorn --check-config gunicorn.conf:app
```

### ECS服务器验证

```bash
# 1. 拉取最新代码
git pull origin master  # 或 git pull github main

# 2. 激活虚拟环境
source venv/bin/activate

# 3. 测试应用导入
python -c "from run import app; print('✅ 配置加载成功')"

# 4. 重启服务
sudo systemctl restart crm
# 或
./restart-server.sh

# 5. 检查服务状态
sudo systemctl status crm
curl http://localhost:5000/health
```

## 配置说明

### config.py 中的配置类

```python
config = {
    'development': DevelopmentConfig,   # 开发环境
    'production': ProductionConfig,     # 生产环境
    'testing': TestingConfig,           # 测试环境
    'default': DevelopmentConfig        # 默认环境
}
```

### 环境变量控制

通过 `FLASK_ENV` 环境变量控制使用哪个配置：

```bash
# 开发环境
export FLASK_ENV=development

# 生产环境
export FLASK_ENV=production

# 测试环境
export FLASK_ENV=testing
```

## 部署步骤

### 1. 推送代码到GitHub

```bash
git add run.py DEPLOYMENT_FIX.md
git commit -m "fix: 修复生产环境配置导入错误，统一使用config.py"
git push github main
```

### 2. 在ECS服务器上更新

```bash
# SSH登录到ECS服务器
ssh user@your-ecs-server

# 进入项目目录
cd /path/to/CRM1

# 拉取最新代码
git pull origin master

# 重启服务
sudo systemctl restart crm

# 验证服务状态
sudo systemctl status crm
curl http://localhost:5000/health
```

## 注意事项

1. **不需要创建 `config_production.py` 文件**，所有配置都在 `config.py` 中
2. **环境变量优先级**：环境变量 > 配置文件默认值
3. **生产环境建议**：
   - 设置强密码的 `SECRET_KEY`
   - 配置适当的 `GUNICORN_WORKERS` 数量
   - 定期备份数据库

## 相关文件

- `run.py` - 应用入口文件（已修复）
- `config.py` - 统一配置文件
- `gunicorn.conf.py` - Gunicorn配置
- `docker-compose.yml` - Docker配置（可选）

## 修复时间

2025-01-XX

## 修复人员

Augment AI Assistant

