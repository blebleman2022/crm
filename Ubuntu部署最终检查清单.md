# Ubuntu部署最终检查清单

## ✅ 核心文件检查

### 1. 部署脚本

| 文件 | 状态 | 功能 | 验证 |
|------|------|------|------|
| ubuntu-deploy.sh | ✅ | 一键部署到Ubuntu | 使用Gunicorn，生产环境配置 |
| quick-update.sh | ✅ | 快速更新代码 | 保护数据库，5-10秒完成 |
| health-check.sh | ✅ | 健康检查和自动重启 | 检查HTTP、端口、数据库、资源 |

**验证命令**：
```bash
# 检查脚本是否存在
ls -lh ubuntu-deploy.sh quick-update.sh health-check.sh

# 检查脚本权限
chmod +x ubuntu-deploy.sh quick-update.sh health-check.sh
```

---

### 2. 备份恢复脚本

| 文件 | 状态 | 功能 | 验证 |
|------|------|------|------|
| backup-to-gitee.sh | ✅ | 完整备份到bak分支 | 包含数据库文件 |
| restore-from-bak.sh | ✅ | 从bak分支恢复 | 恢复数据库和配置 |
| setup-git-config.sh | ✅ | 配置Git用户信息 | 设置用户名和邮箱 |

**验证命令**：
```bash
ls -lh backup-to-gitee.sh restore-from-bak.sh setup-git-config.sh
```

---

### 3. 辅助工具

| 文件 | 状态 | 功能 | 验证 |
|------|------|------|------|
| fix-git-conflict.sh | ✅ | 修复Git冲突 | 保护数据库文件 |
| verify-update.sh | ✅ | 验证更新状态 | 检查代码和容器 |
| diagnose-nginx.sh | ⚠️ | Nginx诊断（可选） | 调试用 |

---

### 4. 配置文件

| 文件 | 状态 | 功能 | 关键配置 |
|------|------|------|---------|
| config.py | ✅ | Flask配置 | 生产/开发环境配置 |
| gunicorn.conf.py | ✅ | Gunicorn配置 | Worker数量、日志 |
| requirements.txt | ✅ | Python依赖 | 包含Gunicorn |
| run.py | ✅ | 应用入口 | 健康检查端点 |

**关键检查**：
```bash
# 检查Gunicorn是否在依赖中
grep "gunicorn" requirements.txt

# 检查健康检查端点
grep "@app.route('/health')" run.py
```

---

### 5. 核心文档

| 文件 | 状态 | 内容 |
|------|------|------|
| README.md | ✅ | 项目总体说明 |
| Ubuntu直接部署指南.md | ✅ | 部署主文档 |
| Ubuntu部署问题修复.md | ✅ | 问题分析和修复 |
| 部署方案对比与建议.md | ✅ | 方案对比 |
| 备份恢复指南.md | ✅ | 备份恢复说明 |
| 数据库管理说明.md | ✅ | 数据库管理 |
| 安全更新使用指南.md | ✅ | 更新流程 |

---

## 🔍 关键配置验证

### 1. ubuntu-deploy.sh 关键配置

```bash
# 检查是否使用Gunicorn
grep "gunicorn" ubuntu-deploy.sh

# 检查是否设置生产环境
grep "FLASK_ENV=production" ubuntu-deploy.sh

# 检查是否配置日志轮转
grep "logrotate" ubuntu-deploy.sh

# 检查worker数量计算
grep "CPU_CORES" ubuntu-deploy.sh
```

**预期结果**：
- ✅ 使用Gunicorn而非Flask开发服务器
- ✅ 设置FLASK_ENV=production
- ✅ 配置日志轮转
- ✅ 自动计算worker数量

---

### 2. run.py 健康检查端点

```bash
# 检查健康检查端点
grep -A 5 "@app.route('/health')" run.py
```

**预期结果**：
```python
@app.route('/health')
def health_check():
    """健康检查端点，用于监控和负载均衡"""
    from datetime import datetime
    return {
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'environment': config_name
    }, 200
```

---

### 3. requirements.txt 依赖检查

```bash
# 检查关键依赖
grep -E "(Flask|gunicorn|SQLAlchemy|Pillow)" requirements.txt
```

**预期结果**：
```
Flask==3.0.0
gunicorn==21.2.0
Flask-SQLAlchemy==3.1.1
Pillow==10.1.0
```

---

### 4. config.py 配置检查

```bash
# 检查生产环境配置
grep -A 10 "class ProductionConfig" config.py
```

**预期结果**：
- ✅ DEBUG=False
- ✅ SESSION_COOKIE_SECURE=True
- ✅ 数据库连接池配置

---

## 📋 部署流程验证

### 首次部署流程

```bash
# 1. 配置Git（如果需要）
bash setup-git-config.sh

# 2. 执行部署
sudo bash ubuntu-deploy.sh

# 3. 验证部署
sudo systemctl status crm
curl -I http://localhost/health
```

**预期结果**：
- ✅ CRM服务运行中
- ✅ 使用Gunicorn（多个worker）
- ✅ 健康检查返回200
- ✅ Nginx正常运行

---

### 代码更新流程

```bash
# 1. 快速更新
bash quick-update.sh

# 2. 验证更新
sudo systemctl status crm
curl -I http://localhost/health
```

**预期结果**：
- ✅ 5-10秒完成更新
- ✅ 数据库文件保留
- ✅ 服务自动重启

---

### 备份流程

```bash
# 1. 执行备份
bash backup-to-gitee.sh

# 2. 验证备份
git log origin/bak -1
```

**预期结果**：
- ✅ 备份推送到bak分支
- ✅ 包含数据库文件
- ✅ 提交信息包含备份时间

---

## 🚨 常见问题检查

### 问题1: 服务启动失败

**检查**：
```bash
sudo journalctl -u crm -n 50
```

**常见原因**：
- ❌ 端口5000被占用
- ❌ Python依赖缺失
- ❌ 数据库文件权限问题

**解决方案**：
```bash
# 检查端口
sudo netstat -tuln | grep 5000

# 重新安装依赖
cd ~/crm
source venv/bin/activate
pip install -r requirements.txt

# 修复权限
sudo chown -R $USER:$USER ~/crm/instance
```

---

### 问题2: Nginx 502错误

**检查**：
```bash
sudo systemctl status crm
curl http://localhost:5000/health
```

**常见原因**：
- ❌ CRM服务未运行
- ❌ 端口配置错误

**解决方案**：
```bash
sudo systemctl start crm
sudo systemctl restart nginx
```

---

### 问题3: 静态文件404

**检查**：
```bash
ls -lh static/
sudo nginx -t
```

**常见原因**：
- ❌ 静态文件路径错误
- ❌ 文件权限问题

**解决方案**：
```bash
sudo chmod -R 755 ~/crm/static
sudo systemctl restart nginx
```

---

## 📊 性能验证

### 1. 并发测试

```bash
# 安装ab工具
sudo apt install apache2-utils

# 并发测试
ab -n 1000 -c 50 http://localhost/
```

**预期结果**：
- ✅ 成功率 > 99%
- ✅ 平均响应时间 < 500ms
- ✅ 无超时错误

---

### 2. Worker进程检查

```bash
# 查看Gunicorn进程
ps aux | grep gunicorn
```

**预期结果**：
- ✅ 1个master进程
- ✅ 多个worker进程（根据CPU核心数）

---

### 3. 资源使用检查

```bash
# CPU使用率
top -bn1 | grep gunicorn

# 内存使用
free -h

# 磁盘空间
df -h
```

**预期结果**：
- ✅ CPU使用率 < 80%
- ✅ 内存使用率 < 80%
- ✅ 磁盘空间 > 20%

---

## ✅ 最终检查清单

### 部署前检查

- [ ] 服务器系统是Ubuntu
- [ ] 有sudo权限
- [ ] 网络连接正常
- [ ] Git已配置用户信息
- [ ] 项目已克隆到服务器

### 部署后检查

- [ ] CRM服务运行正常
- [ ] Nginx服务运行正常
- [ ] 健康检查端点返回200
- [ ] 浏览器可以访问系统
- [ ] 登录功能正常
- [ ] 数据库文件存在
- [ ] 日志正常输出
- [ ] 静态文件加载正常

### 性能检查

- [ ] 使用Gunicorn（非Flask开发服务器）
- [ ] 多个worker进程运行
- [ ] 并发测试通过
- [ ] 响应时间正常
- [ ] 资源使用正常

### 备份检查

- [ ] 备份脚本可执行
- [ ] 可以推送到bak分支
- [ ] 可以从bak分支恢复
- [ ] 数据库文件包含在备份中

---

## 🎯 总结

### 核心优势

1. ✅ **生产级性能** - Gunicorn多进程
2. ✅ **更新速度快** - 5-10秒完成更新
3. ✅ **稳定可靠** - 自动重启、健康检查
4. ✅ **完整备份** - 包含数据库的完整备份
5. ✅ **易于维护** - 清晰的文档和脚本

### 关键文件

**必需**：
- ubuntu-deploy.sh
- quick-update.sh
- config.py
- gunicorn.conf.py
- requirements.txt
- run.py

**推荐**：
- health-check.sh
- backup-to-gitee.sh
- restore-from-bak.sh
- Ubuntu直接部署指南.md

### 部署命令

```bash
# 首次部署
sudo bash ubuntu-deploy.sh

# 日常更新
bash quick-update.sh

# 完整备份
bash backup-to-gitee.sh
```

---

**最后更新**: 2025-01-02  
**版本**: 1.0  
**状态**: ✅ 生产就绪

