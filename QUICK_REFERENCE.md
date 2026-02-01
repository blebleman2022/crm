# EduConnect CRM 快速参考指南

## 🚀 快速启动

```bash
# 进入项目目录
cd /Users/blebleman/sync/CRM1

# 启动本地服务器(端口5002)
PORT=5002 python3 run.py

# 访问应用
http://localhost:5002
```

---

## 🔑 关键文件位置

| 文件 | 说明 |
|------|------|
| `models.py` | 数据库模型定义(15个表) |
| `routes/auth.py` | 认证路由(登录/登出) |
| `routes/teacher.py` | 老师路由(学生列表/文档管理) |
| `routes/delivery.py` | 班主任路由(老师管理/文档查看) |
| `routes/customers.py` | 客户管理路由 |
| `routes/leads.py` | 线索管理路由 |
| `templates/teacher/` | 老师端模板 |
| `templates/delivery/` | 班主任端模板 |
| `instance/edu_crm.db` | SQLite数据库 |

---

## 👤 用户角色速查

### User 表中的角色

```python
# 检查用户角色
if current_user.role == 'admin':
    # 管理员权限
elif current_user.role == 'teacher_supervisor':
    # 班主任权限
elif current_user.role == 'teacher':
    # 老师权限
elif current_user.role in ['sales_manager', 'salesperson']:
    # 销售权限
```

### 装饰器

```python
@teacher_required  # 仅老师可访问
@teacher_supervisor_required  # 仅班主任可访问
@login_required  # 需要登录
```

---

## 📊 常用数据库查询

### 查询老师的学生列表
```python
students = Customer.query.filter_by(teacher_id=teacher_id).all()
```

### 查询学生的文档
```python
docs = DeliveryDocument.query.filter_by(
    customer_id=customer_id,
    doc_type='thesis_draft',
    is_latest=True
).all()
```

### 查询班主任创建的老师
```python
teachers = Teacher.query.filter(
    Teacher.user.has(created_by_user_id=supervisor_id)
).all()
```

### 查询用户
```python
user = User.query.filter_by(phone=phone).first()
teacher = Teacher.query.filter_by(user_id=user_id).first()
```

---

## 🔐 权限检查模式

### 老师权限检查
```python
@teacher_bp.route('/students/<int:customer_id>/upload/<doc_type>', methods=['POST'])
@teacher_required
def upload_document(customer_id, doc_type):
    # 验证学生是否属于当前老师
    customer = Customer.query.get_or_404(customer_id)
    if customer.teacher_id != current_user.id:
        flash('您无权操作此学生', 'error')
        return redirect(url_for('teacher.student_list'))
```

### 班主任权限检查
```python
@delivery_bp.route('/teachers/<int:teacher_id>/edit', methods=['GET', 'POST'])
@teacher_supervisor_required
def edit_teacher(teacher_id):
    teacher = Teacher.query.get_or_404(teacher_id)
    # 验证老师是否由当前班主任创建
    if teacher.user.created_by_user_id != current_user.id:
        flash('您无权编辑此老师', 'error')
        return redirect(url_for('delivery.teacher_list'))
```

---

## 📁 文档管理关键字段

### 文档类型枚举
```python
DOC_TYPES = {
    'thesis_draft': '课题初稿',
    'thesis_final': '终稿',
    'presentation': '演示方案',
    'novelty_report': '查新报告',
    'plagiarism_report': '查重报告',
    'evaluation_material': '高三综评材料'
}
```

### 文件命名规则
```
{customer_id}_{doc_type}_v{version}_{timestamp}.{ext}
例: 8_thesis_draft_v2_20260130_165207.pdf
```

### 版本管理逻辑
```python
# 上传新版本时
old_docs = DeliveryDocument.query.filter_by(
    customer_id=customer_id,
    doc_type=doc_type,
    is_latest=True
).all()
for doc in old_docs:
    doc.is_latest = False

new_doc = DeliveryDocument(
    customer_id=customer_id,
    doc_type=doc_type,
    version=max_version + 1,
    is_latest=True
)
```

---

## 🔗 关键URL路由

### 认证
- `GET/POST /auth/login` - 登录
- `GET /auth/logout` - 登出

### 老师端
- `GET /teacher/students` - 学生列表
- `GET /teacher/students/<id>` - 学生详情
- `POST /teacher/students/<id>/upload/<doc_type>` - 上传文档
- `GET /teacher/documents/<id>/download` - 下载文档
- `POST /teacher/documents/<id>/delete` - 删除文档

### 班主任端
- `GET /delivery/dashboard` - 仪表板
- `GET /delivery/teachers` - 老师列表
- `GET/POST /delivery/teachers/create` - 创建老师
- `GET/POST /delivery/teachers/<id>/edit` - 编辑老师
- `GET /delivery/customers/<id>/documents` - 查看文档

---

## 🧪 测试命令

### 启动服务器
```bash
PORT=5002 python3 run.py
```

### 查看数据库
```bash
sqlite3 instance/edu_crm.db
sqlite3> SELECT * FROM users;
sqlite3> SELECT * FROM teachers;
sqlite3> SELECT * FROM customers;
```

### 查看日志
```bash
tail -f logs/crm.log
```

---

## 💡 常见问题解决

### 问题: 老师无法看到学生
**检查:**
1. 学生是否分配了老师? `Customer.teacher_id` 是否为空
2. 老师ID是否正确? `Teacher.id` 是否与 `Customer.teacher_id` 匹配
3. 老师账号是否启用? `Teacher.status` 是否为 True

### 问题: 文档上传失败
**检查:**
1. 文件大小是否超过10MB?
2. 文件扩展名是否在允许列表中?
3. uploads/documents/ 目录是否存在?
4. 权限是否正确? 只有老师可以上传

### 问题: 班主任看不到文档
**检查:**
1. 文档是否标记为 `is_latest=True`?
2. 班主任是否有权限查看此学生的文档?
3. 文档是否已成功上传?


