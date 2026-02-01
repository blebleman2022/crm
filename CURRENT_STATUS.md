# EduConnect CRM 当前系统状态

## ✅ 已完成功能

### 认证系统
- ✅ 统一手机号免密登录(所有角色)
- ✅ 自动角色识别和重定向
- ✅ 登录日志记录
- ✅ 账号启用/禁用状态检查

### 老师管理
- ✅ 班主任创建老师账号(无需密码)
- ✅ 班主任编辑老师信息
- ✅ 班主任启用/禁用老师账号
- ✅ 老师列表查看和管理

### 学生管理
- ✅ 班主任分配老师给学生
- ✅ 老师查看负责的学生列表
- ✅ 老师查看学生详情
- ✅ 权限隔离(老师只能看自己的学生)

### 文档管理
- ✅ 6种文档类型支持(初稿/终稿/演示/查新/查重/综评)
- ✅ 文档上传(老师)
- ✅ 文档下载(老师和班主任)
- ✅ 文档删除(老师,仅自己上传)
- ✅ 版本管理(自动递增)
- ✅ 权限控制(班主任只读)

### 课题管理
- ✅ 老师编辑课题名称
- ✅ 班主任设置课题截止时间
- ✅ 班主任设置首个参赛赛事
- ✅ 截止时间提醒(学生列表显示剩余天数)

### 用户界面
- ✅ 老师登录后直接进入学生列表页
- ✅ 取消老师dashboard页面
- ✅ 取消老师个人设置页面
- ✅ 简化导航栏(仅显示用户名和退出)

---

## 🐛 已知问题

### 1. AttributeError: 'Teacher' object has no attribute 'role'
**状态:** 已识别,需要修复
**原因:** 在某些代码路径中尝试访问 Teacher 对象的 role 属性,但 Teacher 模型中没有此属性
**影响:** 可能导致某些页面崩溃
**解决方案:** 
- Teacher 对象应通过 `teacher.user.role` 访问角色
- 或在代码中检查对象类型后再访问属性

### 2. 用户类型判断不一致
**状态:** 需要规范化
**问题:** 代码中混合使用 `hasattr(current_user, 'role')` 和 `isinstance()` 来判断用户类型
**建议:** 统一使用 `current_user.role` 判断(User 对象有此属性)

---

## 📋 测试账号

### 班主任账号
- **姓名:** 葛老师
- **手机号:** 13585811031
- **角色:** teacher_supervisor
- **权限:** 创建老师、分配老师、查看文档

### 老师账号
- **姓名:** 张老师
- **手机号:** 13800001111
- **角色:** teacher
- **权限:** 上传文档、编辑课题名称

### 新建老师账号
- **姓名:** 李老师
- **手机号:** 13900002222
- **角色:** teacher
- **权限:** 上传文档、编辑课题名称

### 测试学生
- **姓名:** 东炎炎
- **ID:** 8
- **年级:** 高一
- **分配老师:** 张老师

---

## 🔧 系统配置

### 文件上传配置
- **允许扩展名:** .doc, .docx, .pdf, .zip, .rar, .txt(测试)
- **最大文件大小:** 10MB
- **存储路径:** uploads/documents/
- **文件命名:** {customer_id}_{doc_type}_v{version}_{timestamp}.{ext}

### 数据库配置
- **类型:** SQLite
- **路径:** instance/edu_crm.db
- **备份路径:** backups/ 和 bak/

### 服务器配置
- **本地测试端口:** 5002
- **生产服务器:** sxylab.com (Alibaba Cloud)
- **部署方式:** Gunicorn + Nginx + Systemd

---

## 📊 数据库统计

### 当前数据量(示例)
- Users: 多个(admin/sales_manager/salesperson/teacher_supervisor/teacher)
- Teachers: 4+ (李明、明天、张老师、李老师等)
- Leads: 多个
- Customers: 多个
- DeliveryDocuments: 多个(带版本管理)
- CompetitionNames: 多个竞赛

---

## 🚀 下一步计划

### 短期(需要修复)
1. 修复 AttributeError: 'Teacher' object has no attribute 'role'
2. 规范化用户类型判断逻辑
3. 完整的系统测试

### 中期(功能增强)
1. 添加更多报表功能
2. 优化性能(数据库查询优化)
3. 增强搜索功能

### 长期(架构优化)
1. 考虑迁移到 PostgreSQL
2. 添加缓存层(Redis)
3. 微服务架构改造

---

## 📝 重要笔记

### 用户模型设计
- **User 表:** 存储登录信息和角色(phone, role, status)
- **Teacher 表:** 存储老师专业信息(user_id 一对一关联)
- **登录:** 只查询 User 表,通过 role 判断权限
- **老师信息:** 通过 user.teacher_profile 访问

### 权限控制原则
- 班主任(teacher_supervisor): 管理交付、创建老师、查看文档
- 老师(teacher): 上传文档、编辑课题名称
- 权限检查: 使用装饰器 @teacher_required 或 @teacher_supervisor_required

### 文档管理原则
- 版本管理: 上传新版本时自动将旧版本 is_latest 设为 False
- 权限控制: 记录 uploaded_by_type 和 uploaded_by_id
- 删除权限: 只有上传者可以删除


