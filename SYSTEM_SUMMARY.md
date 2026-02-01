# EduConnect CRM 系统总结

## 📌 项目概览

**EduConnect CRM** 是一个教育机构客户关系管理系统,专注于学员线索管理、客户转化、课题辅导交付和竞赛管理。

**核心特点:**
- 🔐 统一手机号免密登录系统
- 👥 双角色用户体系(User + Teacher)
- 📄 完整的文档版本管理系统
- 🎯 灵活的权限控制机制
- 📊 详细的数据追踪和日志记录

---

## 🗄️ 数据库架构(15个表)

### 核心业务表(4个)
1. **users** - 用户账号(登录信息、角色、权限)
2. **teachers** - 老师信息(专业信息、学科、状态)
3. **leads** - 学员线索(销售阶段、服务内容)
4. **customers** - 成交客户(课题信息、交付管理)

### 交付管理表(2个)
5. **tutoring_deliveries** - 课题辅导交付
6. **delivery_documents** - 交付文档(版本管理)

### 竞赛管理表(2个)
7. **competition_names** - 竞赛名称配置
8. **customer_competitions** - 客户赛事关联

### 财务管理表(2个)
9. **payments** - 付款记录
10. **customer_payments** - 客户付款信息

### 沟通和日志表(2个)
11. **communication_records** - 沟通记录
12. **login_logs** - 登录日志

### 图片管理表(3个)
13. **teacher_images** - 老师相关图片
14. **course_record_images** - 课程记录图片
15. **award_certificate_images** - 获奖证书图片
16. **customer_review_images** - 客户好评图片

---

## 👥 用户角色体系

### User 表中的5种角色

| 角色 | 说明 | 主要权限 |
|------|------|--------|
| **admin** | 管理员 | 系统配置、用户管理 |
| **sales_manager** | 销售经理 | 管理销售团队、线索转化 |
| **salesperson** | 销售 | 管理分配的线索 |
| **teacher_supervisor** | 班主任 | 创建老师、分配老师、查看文档 |
| **teacher** | 辅导老师 | 上传文档、编辑课题名称 |

### 关键设计
- **User 表:** 存储登录信息(phone, role, status)
- **Teacher 表:** 存储老师专业信息(user_id 一对一关联)
- **登录:** 仅查询 User 表,通过 role 判断权限
- **老师信息:** 通过 user.teacher_profile 访问

---

## 🔐 认证系统

### 登录流程
1. 用户访问 `/auth/login`
2. 输入手机号(免密登录)
3. 系统查询 User 表
4. 验证账号状态(status=True)
5. 根据 role 自动重定向:
   - admin → /admin/dashboard
   - sales_manager/salesperson → /leads/dashboard
   - teacher_supervisor → /delivery/dashboard
   - teacher → /teacher/students

### 特点
- ✅ 无需密码,仅需手机号
- ✅ 自动角色识别
- ✅ 登录日志记录
- ✅ 账号状态检查

---

## 📄 文档管理系统

### 支持的6种文档类型
1. **thesis_draft** - 课题初稿
2. **thesis_final** - 终稿
3. **presentation** - 演示方案
4. **novelty_report** - 查新报告
5. **plagiarism_report** - 查重报告
6. **evaluation_material** - 高三综评材料

### 版本管理
- 上传新版本时自动递增版本号(v1 → v2 → v3...)
- 自动标记旧版本为非最新(is_latest=False)
- 文件命名: `{customer_id}_{doc_type}_v{version}_{timestamp}.{ext}`

### 权限控制
- **老师:** 可上传、下载、删除(仅自己上传)
- **班主任:** 可查看、下载(只读)
- **其他:** 无权限

---

## 🎯 主要功能模块

### 班主任端(teacher_supervisor)
- ✅ 创建老师账号(无需密码)
- ✅ 编辑老师信息
- ✅ 启用/禁用老师账号
- ✅ 分配老师给学生
- ✅ 查看学生文档(只读)
- ✅ 下载学生文档
- ✅ 设置课题截止时间
- ✅ 设置首个参赛赛事

### 老师端(teacher)
- ✅ 查看负责的学生列表
- ✅ 查看学生详情
- ✅ 上传6种文档类型
- ✅ 下载文档
- ✅ 删除文档(仅自己上传)
- ✅ 编辑课题名称
- ✅ 查看课题截止时间和剩余天数

---

## 📊 关键数据关系

```
User (role='teacher_supervisor')
  ↓ created_by_user_id
  ├─→ Teacher (user_id)
  │     ↓ teacher_id
  │     └─→ Customer
  │           ↓ lead_id
  │           └─→ Lead
  │
  └─→ Customer (teacher_user_id)
        ↓
        ├─→ DeliveryDocument
        ├─→ TutoringDelivery
        └─→ CustomerCompetition
```

---

## 🚀 快速启动

```bash
# 启动本地服务器
PORT=5002 python3 run.py

# 访问应用
http://localhost:5002

# 登录(手机号免密)
手机号: 13585811031 (班主任)
手机号: 13800001111 (老师)
```

---

## 📝 重要文件

| 文件 | 说明 |
|------|------|
| `models.py` | 数据库模型定义 |
| `routes/auth.py` | 认证路由 |
| `routes/teacher.py` | 老师路由 |
| `routes/delivery.py` | 班主任路由 |
| `templates/teacher/` | 老师端模板 |
| `templates/delivery/` | 班主任端模板 |
| `instance/edu_crm.db` | SQLite数据库 |

---

## ✅ 当前状态

- ✅ 登录系统统一为手机号免密登录
- ✅ 老师登录后直接进入学生列表页
- ✅ 取消老师dashboard和个人设置页
- ✅ 文档管理系统完整
- ✅ 权限控制正确
- ✅ 版本管理正常工作

---

## 🐛 已知问题

1. **AttributeError: 'Teacher' object has no attribute 'role'**
   - 原因: 某些代码路径尝试访问 Teacher 对象的 role 属性
   - 解决: 应使用 `teacher.user.role` 或检查对象类型

---

## 📚 文档清单

- `PROJECT_OVERVIEW.md` - 项目概览和架构
- `DATABASE_SCHEMA.md` - 数据库详细架构
- `CURRENT_STATUS.md` - 当前系统状态和问题
- `QUICK_REFERENCE.md` - 快速参考指南
- `SYSTEM_SUMMARY.md` - 本文档


