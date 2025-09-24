# EduConnect CRM 配置说明

## 📋 统一配置架构

本项目已统一配置文件，简化部署和维护：

### 🗂️ 配置文件结构

```
├── config.py              # 统一配置文件（包含所有环境）
├── docker-compose.yml     # Docker编排文件
├── Dockerfile            # Docker镜像构建文件
├── .env.example          # 环境变量示例
└── .env                  # 实际环境变量（需要创建）
```

### 🔧 配置类说明

#### BaseConfig
- 基础配置类，包含所有通用配置
- 数据库、安全、邮件等基础设置

#### DevelopmentConfig
- 开发环境配置
- 启用调试模式
- 使用HTTP cookie

#### ProductionConfig  
- 生产环境配置
- 禁用调试模式
- 启用HTTPS cookie
- 配置日志文件
- 数据库连接池优化

#### TestingConfig
- 测试环境配置
- 使用内存数据库
- 禁用CSRF保护

### 🌍 环境变量配置

通过环境变量控制应用行为：

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `FLASK_ENV` | `production` | 应用环境 |
| `DATABASE_URL` | `sqlite:///instance/edu_crm.db` | 数据库连接 |
| `SECRET_KEY` | 自动生成 | 安全密钥 |
| `LOG_LEVEL` | `INFO` | 日志级别 |
| `GUNICORN_WORKERS` | `2` | Gunicorn工作进程数 |
| `GUNICORN_TIMEOUT` | `120` | 请求超时时间 |

### 🚀 部署方式

#### 1. 开发环境
```bash
# 设置开发环境
export FLASK_ENV=development
python run.py
```

#### 2. 生产环境
```bash
# 使用Docker Compose
cp .env.example .env
# 编辑 .env 文件设置生产环境变量
docker compose up -d
```

#### 3. 自定义配置
```bash
# 通过环境变量覆盖默认配置
export DATABASE_URL=postgresql://user:pass@host:5432/db
export SECRET_KEY=your-production-secret
docker compose up -d
```

### 📝 配置最佳实践

1. **生产环境**：
   - 使用强密码作为SECRET_KEY
   - 设置适当的GUNICORN_WORKERS数量
   - 配置外部数据库（PostgreSQL/MySQL）

2. **开发环境**：
   - 使用SQLite数据库
   - 启用调试模式
   - 设置详细日志级别

3. **安全配置**：
   - 不要在代码中硬编码敏感信息
   - 使用.env文件管理环境变量
   - 定期更换SECRET_KEY

### 🔄 迁移说明

从旧版本迁移：
1. 删除 `config_production.py`
2. 使用统一的 `config.py`
3. 通过环境变量控制配置
4. 更新部署脚本使用新的配置方式
