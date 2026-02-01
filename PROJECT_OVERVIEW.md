# EduConnect CRM 项目概览

## 📋 项目简介

EduConnect CRM 是一个教育机构客户关系管理系统,用于管理学员线索、成交客户、课题辅导交付和竞赛管理。

**技术栈:**
- 后端: Flask 3.0.0 + SQLAlchemy 2.0.23
- 数据库: SQLite (instance/edu_crm.db)
- 前端: HTML5 + Tailwind CSS + JavaScript
- 认证: Flask-Login (支持User和Teacher两种用户类型)
- 部署: Gunicorn + Nginx + Systemd

---

## 🗄️ 数据库表结构

### 核心表

| 表名 | 说明 | 关键字段 |
|------|------|--------|
| **users** | 用户账号表 | id, username, phone, role, status |
| **teachers** | 老师信息表 | user_id, email, subject, status |
| **leads** | 学员线索表 | id, student_name, parent_wechat_name, sales_user_id, stage |
| **customers** | 成交客户表 | id, lead_id, teacher_id, teacher_user_id, thesis_name, thesis_deadline |
| **tutoring_deliveries** | 课题辅导交付表 | id, customer_id, thesis_status, completed_sessions |
| **delivery_documents** | 交付文档表 | id, customer_id, doc_type, file_path, version, is_latest |

### 配置表

| 表名 | 说明 |
|------|------|
| **competition_names** | 竞赛名称配置 |
| **customer_competitions** | 客户赛事关联 |
| **payments** | 付款记录 |
| **customer_payments** | 客户付款信息 |
| **communication_records** | 沟通记录 |
| **login_logs** | 登录日志 |

### 图片表

| 表名 | 说明 |
|------|------|
| **teacher_images** | 老师相关图片 |
| **course_record_images** | 课程记录图片 |
| **award_certificate_images** | 获奖证书图片 |
| **customer_review_images** | 客户好评图片 |

---

## 👥 用户角色体系

### User 表中的角色 (role字段)

| 角色 | 说明 | 权限 |
|------|------|------|
| **admin** | 管理员 | 系统配置、用户管理 |
| **sales_manager** | 销售经理 | 管理销售团队、线索转化 |
| **salesperson** | 销售 | 管理分配的线索 |
| **teacher_supervisor** | 班主任 | 管理交付、创建老师、分配老师 |
| **teacher** | 辅导老师 | 上传文档、编辑课题名称 |

### Teacher 表

- 独立的老师信息表,通过 `user_id` 与 User 表一对一关联
- 登录信息存储在 User 表,专业信息存储在 Teacher 表
- 老师必须有对应的 User 记录(role='teacher')

---

## 🔐 认证系统

### 登录流程

1. 用户访问 `/auth/login`
2. 输入手机号(免密登录)
3. 系统查询 User 表
4. 验证账号状态
5. 根据 role 自动重定向:
   - admin → /admin/dashboard
   - sales_manager/salesperson → /leads/dashboard
   - teacher_supervisor → /delivery/dashboard
   - teacher → /teacher/students

### 用户加载器

```python
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
```

---

## 📁 项目结构

```
CRM1/
├── models.py              # 数据库模型定义
├── run.py                 # 应用入口
├── config.py              # 配置文件
├── requirements.txt       # 依赖包
├── routes/                # 路由模块
│   ├── auth.py           # 认证路由
│   ├── admin.py          # 管理员路由
│   ├── leads.py          # 线索管理路由
│   ├── customers.py      # 客户管理路由
│   ├── delivery.py       # 交付管理路由(班主任)
│   ├── teacher.py        # 老师路由
│   └── ...
├── templates/            # HTML模板
│   ├── auth/            # 登录相关
│   ├── admin/           # 管理员页面
│   ├── leads/           # 线索页面
│   ├── customers/       # 客户页面
│   ├── delivery/        # 交付页面
│   ├── teacher/         # 老师页面
│   └── ...
├── static/              # 静态资源
│   ├── css/
│   ├── js/
│   └── images/
├── uploads/             # 上传文件存储
│   └── documents/       # 交付文档
└── instance/            # 实例文件
    └── edu_crm.db       # SQLite数据库
```

---

## 🎯 主要功能模块

### 1. 线索管理 (leads)
- 创建/编辑线索
- 线索阶段管理
- 线索转化为客户

### 2. 客户管理 (customers)
- 客户信息维护
- 竞赛管理
- 付款记录

### 3. 交付管理 (delivery)
- 班主任创建/管理老师账号
- 分配老师给客户
- 查看文档(只读)
- 设置课题截止时间

### 4. 老师端 (teacher)
- 查看负责的学生列表
- 上传/下载/删除文档
- 编辑课题名称
- 文档版本管理

### 5. 文档管理 (delivery_documents)
- 6种文档类型支持
- 版本管理(自动递增)
- 权限控制(老师可上传/删除,班主任只读)

---

## 🔄 关键关系

```
User (role='teacher_supervisor')
  ↓
  创建 → Teacher (user_id)
           ↓
           分配给 → Customer (teacher_id)
                    ↓
                    关联 → Lead (lead_id)
                    ↓
                    上传 → DeliveryDocument
```

---

## ⚙️ 当前状态

- ✅ 登录系统统一为手机号免密登录
- ✅ 老师登录后直接进入学生列表页
- ✅ 取消老师dashboard和个人设置页
- ✅ 文档管理系统完整
- ✅ 权限控制正确

