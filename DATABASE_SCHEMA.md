# EduConnect CRM 数据库架构详解

## 📊 完整表结构

### 1. users (用户账号表)

```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    username VARCHAR(50) NOT NULL,
    phone VARCHAR(11) UNIQUE NOT NULL,
    role VARCHAR(20) NOT NULL,  -- admin/sales_manager/salesperson/teacher_supervisor/teacher
    group_name VARCHAR(50),
    status BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    created_by_user_id INTEGER
);
```

**关键字段说明:**
- `role`: 用户角色,决定权限和重定向
- `phone`: 登录账号(免密登录)
- `status`: 账号启用/禁用状态

---

### 2. teachers (老师信息表)

```sql
CREATE TABLE teachers (
    id INTEGER PRIMARY KEY,
    user_id INTEGER UNIQUE NOT NULL FOREIGN KEY,  -- 关联User表
    current_institution VARCHAR(200),
    major_direction VARCHAR(200),
    highest_degree VARCHAR(50),
    degree_description TEXT,
    research_achievements TEXT,
    innovation_coaching_achievements TEXT,
    social_roles TEXT,
    email VARCHAR(100),
    subject VARCHAR(50),  -- 擅长学科
    status BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

**关键关系:**
- 一对一关联到 User 表(user_id)
- 一对多关联到 Customer 表(teacher_id)

---

### 3. leads (学员线索表)

```sql
CREATE TABLE leads (
    id INTEGER PRIMARY KEY,
    student_name VARCHAR(50),
    parent_wechat_display_name VARCHAR(50) NOT NULL,
    parent_wechat_name VARCHAR(50) UNIQUE NOT NULL,
    contact_info VARCHAR(100),
    contact_locked BOOLEAN DEFAULT TRUE,
    lead_source VARCHAR(50),
    grade VARCHAR(10),  -- 1-9年级、高一、高二、高三
    district VARCHAR(20),
    school VARCHAR(100),
    sales_user_id INTEGER NOT NULL FOREIGN KEY,  -- 责任销售
    stage VARCHAR(50) NOT NULL,  -- 线索阶段
    contract_amount NUMERIC(10,2),
    
    -- 各阶段时间
    contact_obtained_at DATETIME,
    meeting_at DATETIME,
    meeting_location VARCHAR(20),  -- 浦东/浦西
    first_payment_at DATETIME,
    second_payment_at DATETIME,
    
    -- 服务内容
    service_types TEXT,  -- JSON格式
    competition_award_level VARCHAR(20),  -- 市奖/国奖
    additional_requirements TEXT,
    
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

**关键字段说明:**
- `stage`: 线索阶段(获取联系方式/线下见面/首笔支付/次笔支付/全款支付)
- `service_types`: JSON格式存储服务类型列表
- `sales_user_id`: 指向 users 表

---

### 4. customers (成交客户表)

```sql
CREATE TABLE customers (
    id INTEGER PRIMARY KEY,
    lead_id INTEGER NOT NULL FOREIGN KEY,  -- 关联线索
    teacher_user_id INTEGER FOREIGN KEY,  -- 班主任ID(User表)
    teacher_id INTEGER FOREIGN KEY,  -- 辅导老师ID(Teacher表)
    
    payment_amount NUMERIC(10,2) NOT NULL,
    exam_year INTEGER,
    thesis_name VARCHAR(200),  -- 课题名称
    customer_notes TEXT,
    converted_at DATETIME,
    is_priority BOOLEAN DEFAULT FALSE,
    
    -- 交付管理增强
    thesis_deadline DATE,  -- 课题完成截止时间
    first_competition_id INTEGER FOREIGN KEY,  -- 首个参赛赛事
    
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

**关键关系:**
- 多对一: 关联到 Lead 表
- 多对一: 关联到 Teacher 表(辅导老师)
- 多对一: 关联到 User 表(班主任)
- 一对一: 关联到 TutoringDelivery 表
- 一对多: 关联到 DeliveryDocument 表

---

### 5. delivery_documents (交付文档表)

```sql
CREATE TABLE delivery_documents (
    id INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL FOREIGN KEY,
    
    doc_type VARCHAR(50) NOT NULL,  -- 文档类型
    -- 枚举值: thesis_draft/thesis_final/presentation/novelty_report/plagiarism_report/evaluation_material
    
    file_name VARCHAR(200) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    file_size INTEGER,
    file_ext VARCHAR(10),
    
    -- 上传者信息
    uploaded_by_type VARCHAR(20) NOT NULL,  -- teacher_supervisor/teacher
    uploaded_by_id INTEGER NOT NULL,
    uploaded_by_name VARCHAR(50),
    
    -- 版本管理
    version INTEGER DEFAULT 1,
    is_latest BOOLEAN DEFAULT TRUE,
    
    description VARCHAR(500),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

**关键特性:**
- 支持6种文档类型
- 版本管理: 上传新版本时自动递增
- 权限控制: 记录上传者类型和ID

---

### 6. tutoring_deliveries (课题辅导交付表)

```sql
CREATE TABLE tutoring_deliveries (
    id INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL FOREIGN KEY,
    
    total_sessions INTEGER DEFAULT 6,
    completed_sessions INTEGER DEFAULT 0,
    remaining_sessions INTEGER DEFAULT 6,
    
    thesis_status VARCHAR(20) DEFAULT '未开始',
    thesis_completed_at DATETIME,
    last_class_at DATETIME,
    next_class_at DATETIME,
    
    delivery_notes TEXT,
    notes_history JSON,
    
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

---

### 7. competition_names (竞赛名称配置表)

```sql
CREATE TABLE competition_names (
    id INTEGER PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

---

### 8. customer_competitions (客户赛事关联表)

```sql
CREATE TABLE customer_competitions (
    id INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL FOREIGN KEY,
    competition_name_id INTEGER NOT NULL FOREIGN KEY,
    status VARCHAR(50) NOT NULL DEFAULT '未报名',
    notes TEXT,
    created_by_user_id INTEGER NOT NULL FOREIGN KEY,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

---

## 🔗 关键关系图

```
User (role='teacher_supervisor')
  ↓ created_by_user_id
  ├─→ Teacher (user_id)
  │     ↓ teacher_id
  │     └─→ Customer
  │           ↓ lead_id
  │           └─→ Lead (sales_user_id → User)
  │                 ↓
  │                 └─→ Payment
  │
  └─→ Customer (teacher_user_id)
        ↓
        ├─→ DeliveryDocument
        ├─→ TutoringDelivery
        ├─→ CustomerCompetition
        └─→ Lead

User (role='salesperson')
  ↓ sales_user_id
  └─→ Lead
        ↓
        └─→ Customer
```

---

## 📈 数据流向

### 线索转化流程

1. **销售创建线索** → Lead 表
2. **销售转化客户** → Customer 表(lead_id)
3. **班主任分配老师** → Customer 表(teacher_id)
4. **老师上传文档** → DeliveryDocument 表
5. **班主任查看文档** → DeliveryDocument 表(只读)

---

## 🔐 权限控制

| 操作 | User角色 | Teacher角色 |
|------|---------|-----------|
| 创建老师 | teacher_supervisor | ✗ |
| 分配老师 | teacher_supervisor | ✗ |
| 上传文档 | ✗ | ✓ |
| 删除文档 | ✗ | ✓(仅自己上传) |
| 查看文档 | teacher_supervisor | ✓ |
| 下载文档 | teacher_supervisor | ✓ |
| 编辑课题名称 | ✗ | ✓ |
