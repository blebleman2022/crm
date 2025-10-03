# CRM 数据库自动备份方案

## 📋 功能说明

自动备份 CRM 系统的 SQLite 数据库文件，确保数据安全。

### 核心功能
- ⏰ **定时备份**：每天凌晨 3:00 自动执行
- 📁 **备份路径**：`/bak/edu_crm_YYYYMMDD.db`
- 🔄 **自动清理**：只保留最近 3 天的备份
- 📝 **日志记录**：所有操作记录到 `/bak/backup.log`

---

## 🚀 快速安装（Ubuntu 服务器）

### 方法一：一键安装（推荐）

```bash
# 1. 上传脚本到服务器
# 将 backup-db.sh 和 install-backup-cron.sh 上传到服务器任意目录（如 /root 或 /home/your_user）

# 2. 执行安装脚本
chmod +x install-backup-cron.sh
sudo ./install-backup-cron.sh

# 3. 按提示操作即可
```

### 方法二：手动安装

```bash
# 1. 上传备份脚本
sudo cp backup-db.sh /usr/local/bin/
sudo chmod +x /usr/local/bin/backup-db.sh

# 2. 创建备份目录
sudo mkdir -p /bak
sudo chown $USER:$USER /bak

# 3. 添加 crontab 定时任务
crontab -e

# 在打开的编辑器中添加以下行：
0 3 * * * /usr/local/bin/backup-db.sh >> /bak/backup.log 2>&1

# 保存并退出（vim: 按 ESC，输入 :wq，回车）
```

---

## 📂 文件说明

### 1. `backup-db.sh` - 备份脚本
核心备份逻辑，负责：
- 复制数据库文件到备份目录
- 按日期命名备份文件
- 清理超过 3 天的旧备份
- 记录详细日志

### 2. `install-backup-cron.sh` - 安装脚本
自动化安装工具，负责：
- 设置脚本执行权限
- 创建备份目录
- 添加 crontab 定时任务
- 验证安装结果

### 3. `README-backup.md` - 使用文档
本文档，包含完整的安装和使用说明。

---

## ⚙️ 配置说明

### 修改备份路径

编辑 `backup-db.sh`，修改以下变量：

```bash
SOURCE_DB="/crm/instance/edu_crm.db"    # 源数据库路径
BACKUP_DIR="/bak"                        # 备份目录
```

### 修改保留天数

编辑 `backup-db.sh`，修改以下变量：

```bash
KEEP_DAYS=3    # 保留天数（默认 3 天）
```

### 修改执行时间

编辑 crontab：

```bash
crontab -e
```

修改时间部分（cron 表达式）：

```
# 分 时 日 月 周
0 3 * * *    # 每天凌晨 3:00
0 2 * * *    # 每天凌晨 2:00
0 4 * * 0    # 每周日凌晨 4:00
0 3 1 * *    # 每月 1 号凌晨 3:00
```

---

## 🔍 验证与测试

### 1. 验证 crontab 任务

```bash
# 查看当前用户的定时任务
crontab -l

# 应该看到类似输出：
# 0 3 * * * /path/to/backup-db.sh >> /bak/backup.log 2>&1
```

### 2. 手动测试备份

```bash
# 直接执行备份脚本
sudo /path/to/backup-db.sh

# 或者（如果已安装到 /usr/local/bin）
sudo backup-db.sh
```

### 3. 查看备份结果

```bash
# 查看备份文件
ls -lh /bak/edu_crm_*.db

# 应该看到类似输出：
# -rw-r--r-- 1 root root 2.5M Jan 15 03:00 /bak/edu_crm_20250115.db
```

### 4. 查看备份日志

```bash
# 查看完整日志
cat /bak/backup.log

# 实时查看日志（等待下次备份）
tail -f /bak/backup.log
```

---

## 📊 日志示例

```
[2025-01-15 03:00:01] ========== 开始数据库备份 ==========
[2025-01-15 03:00:01] 正在备份: /crm/instance/edu_crm.db -> /bak/edu_crm_20250115.db
[2025-01-15 03:00:02] 备份成功！文件大小: 2.5M
[2025-01-15 03:00:02] 开始清理旧备份（保留最近 3 天）...
[2025-01-15 03:00:02] 删除旧备份: /bak/edu_crm_20250111.db
[2025-01-15 03:00:02] 当前备份文件列表:
[2025-01-15 03:00:02]   -rw-r--r-- 1 root root 2.4M Jan 12 03:00 /bak/edu_crm_20250112.db
[2025-01-15 03:00:02]   -rw-r--r-- 1 root root 2.4M Jan 13 03:00 /bak/edu_crm_20250113.db
[2025-01-15 03:00:02]   -rw-r--r-- 1 root root 2.5M Jan 14 03:00 /bak/edu_crm_20250114.db
[2025-01-15 03:00:02]   -rw-r--r-- 1 root root 2.5M Jan 15 03:00 /bak/edu_crm_20250115.db
[2025-01-15 03:00:02] 当前共有 4 个备份文件
[2025-01-15 03:00:02] ========== 备份完成 ==========
```

---

## 🛠️ 常用管理命令

### 查看定时任务

```bash
# 查看当前用户的所有定时任务
crontab -l

# 查看系统级定时任务
sudo cat /etc/crontab
```

### 编辑定时任务

```bash
# 编辑当前用户的定时任务
crontab -e
```

### 删除定时任务

```bash
# 删除备份任务（保留其他任务）
crontab -l | grep -v 'backup-db.sh' | crontab -

# 删除所有定时任务（慎用！）
crontab -r
```

### 手动执行备份

```bash
# 方式 1：直接执行脚本
sudo /path/to/backup-db.sh

# 方式 2：如果已安装到 /usr/local/bin
sudo backup-db.sh

# 方式 3：在后台执行并查看日志
sudo backup-db.sh >> /bak/backup.log 2>&1 &
tail -f /bak/backup.log
```

### 查看备份文件

```bash
# 列出所有备份文件
ls -lh /bak/edu_crm_*.db

# 按时间排序（最新的在最后）
ls -lht /bak/edu_crm_*.db

# 查看备份文件数量
ls -1 /bak/edu_crm_*.db | wc -l
```

### 恢复备份

```bash
# 1. 停止 CRM 服务（如果正在运行）
sudo systemctl stop crm  # 或根据你的服务名称

# 2. 备份当前数据库（以防万一）
sudo cp /crm/instance/edu_crm.db /crm/instance/edu_crm.db.before_restore

# 3. 恢复指定日期的备份
sudo cp /bak/edu_crm_20250115.db /crm/instance/edu_crm.db

# 4. 设置正确的权限
sudo chown crm_user:crm_user /crm/instance/edu_crm.db  # 替换为实际用户
sudo chmod 644 /crm/instance/edu_crm.db

# 5. 重启 CRM 服务
sudo systemctl start crm
```

---

## ⚠️ 注意事项

### 1. 路径检查
确保以下路径正确：
- 源数据库：`/crm/instance/edu_crm.db`
- 备份目录：`/bak`

如果路径不同，请修改 `backup-db.sh` 中的配置变量。

### 2. 权限要求
- 备份脚本需要有读取源数据库的权限
- 备份目录需要有写入权限
- 建议使用 `sudo` 或 root 用户执行

### 3. 磁盘空间
- 每个备份文件大小约等于当前数据库大小
- 保留 3 天备份，需要至少 3 倍数据库大小的空间
- 定期检查磁盘空间：`df -h /bak`

### 4. 时区设置
- crontab 使用服务器系统时区
- 确认服务器时区：`timedatectl` 或 `date`
- 如需修改时区：`sudo timedatectl set-timezone Asia/Shanghai`

### 5. 日志管理
- 日志文件会持续增长
- 建议定期清理或使用 logrotate 管理
- 手动清理：`sudo truncate -s 0 /bak/backup.log`

---

## 🔧 故障排查

### 问题 1：定时任务没有执行

**检查步骤：**

```bash
# 1. 确认 cron 服务运行
sudo systemctl status cron

# 2. 查看 cron 日志
sudo tail -f /var/log/syslog | grep CRON

# 3. 检查 crontab 语法
crontab -l

# 4. 手动执行测试
sudo /path/to/backup-db.sh
```

### 问题 2：备份失败

**检查步骤：**

```bash
# 1. 查看备份日志
cat /bak/backup.log

# 2. 检查源文件是否存在
ls -lh /crm/instance/edu_crm.db

# 3. 检查备份目录权限
ls -ld /bak

# 4. 检查磁盘空间
df -h /bak
```

### 问题 3：旧备份没有删除

**检查步骤：**

```bash
# 1. 查看备份文件的修改时间
ls -lht /bak/edu_crm_*.db

# 2. 手动测试清理逻辑
find /bak -name "edu_crm_*.db" -type f -mtime +2

# 3. 检查脚本中的 KEEP_DAYS 变量
grep KEEP_DAYS /path/to/backup-db.sh
```

---

## 📞 技术支持

如遇到问题，请提供以下信息：

1. 服务器系统版本：`lsb_release -a`
2. 备份日志：`cat /bak/backup.log`
3. Crontab 配置：`crontab -l`
4. 错误信息截图或完整输出

---

## 📝 更新日志

### v1.0.0 (2025-01-15)
- ✨ 初始版本
- ✅ 支持每天自动备份
- ✅ 支持保留最近 3 天备份
- ✅ 支持详细日志记录
- ✅ 提供一键安装脚本

---

## 📄 许可证

本脚本为 EduConnect CRM 项目的一部分，仅供内部使用。

