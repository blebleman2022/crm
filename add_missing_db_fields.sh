#!/bin/bash

echo "=========================================="
echo "🔧 添加缺失的数据库字段"
echo "=========================================="
echo ""

cd /root/crm

echo "1. 备份数据库"
echo "----------------------------------------"
cp instance/edu_crm.db instance/edu_crm.db.backup_$(date +%Y%m%d_%H%M%S)
echo "✅ 数据库已备份"
echo ""

echo "2. 检查当前 users 表结构"
echo "----------------------------------------"
sqlite3 instance/edu_crm.db "PRAGMA table_info(users);" | grep -E "is_private_owner|teacher_scope"
echo ""

echo "3. 检查当前 leads 表结构"
echo "----------------------------------------"
sqlite3 instance/edu_crm.db "PRAGMA table_info(leads);" | grep -E "customer_scope|private_owner_id"
echo ""

echo "4. 检查当前 customers 表结构"
echo "----------------------------------------"
sqlite3 instance/edu_crm.db "PRAGMA table_info(customers);" | grep -E "customer_scope|private_owner_id"
echo ""

echo "5. 添加缺失的字段"
echo "----------------------------------------"
sqlite3 instance/edu_crm.db << 'EOF'
-- Users 表字段 (如果不存在)
ALTER TABLE users ADD COLUMN is_private_owner BOOLEAN DEFAULT 0;
ALTER TABLE users ADD COLUMN teacher_scope VARCHAR(20) DEFAULT 'public';

-- Leads 表字段 (如果不存在)
ALTER TABLE leads ADD COLUMN customer_scope VARCHAR(20) DEFAULT 'public' NOT NULL;
ALTER TABLE leads ADD COLUMN private_owner_id INTEGER REFERENCES users(id);

-- Customers 表字段 (如果不存在)
ALTER TABLE customers ADD COLUMN customer_scope VARCHAR(20) DEFAULT 'public' NOT NULL;
ALTER TABLE customers ADD COLUMN private_owner_id INTEGER REFERENCES users(id);
EOF

echo ""
echo "字段添加结果 (忽略 'duplicate column name' 错误):"
echo "✅ 如果看到 'duplicate column name' 说明字段已存在,可以忽略"
echo ""

echo "6. 验证 users 表字段"
echo "----------------------------------------"
sqlite3 instance/edu_crm.db "PRAGMA table_info(users);" | grep -E "is_private_owner|teacher_scope"
echo ""

echo "7. 验证 leads 表字段"
echo "----------------------------------------"
sqlite3 instance/edu_crm.db "PRAGMA table_info(leads);" | grep -E "customer_scope|private_owner_id"
echo ""

echo "8. 验证 customers 表字段"
echo "----------------------------------------"
sqlite3 instance/edu_crm.db "PRAGMA table_info(customers);" | grep -E "customer_scope|private_owner_id"
echo ""

echo "9. 重启 CRM 服务"
echo "----------------------------------------"
sudo systemctl restart crm
sleep 3
sudo systemctl status crm --no-pager | head -15
echo ""

echo "10. 测试访问"
echo "----------------------------------------"
curl -I http://127.0.0.1:5002/ 2>&1 | head -10
echo ""

echo "=========================================="
echo "修复完成"
echo "=========================================="
echo ""
echo "📋 下一步:"
echo "1. 刷新浏览器"
echo "2. 尝试登录"
echo "3. 如果还有错误,查看日志: tail -50 /root/crm/logs/error.log"
echo ""

