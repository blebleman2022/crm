#!/bin/bash

echo "🔧 修复CRM应用部署问题..."

# 停止并删除当前容器
echo "停止当前容器..."
docker stop crm-crm-wvx7gd 2>/dev/null || true
docker rm crm-crm-wvx7gd 2>/dev/null || true

# 检查镜像
echo "检查Docker镜像..."
docker images | grep crm

# 创建测试脚本来验证应用
echo "创建应用测试脚本..."
cat > test_app.py << 'EOF'
#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, '/app')

print("=== 测试Flask应用 ===")
try:
    from run import app, create_app
    print(f"✅ 应用导入成功: {app}")
    print(f"✅ 应用名称: {app.name}")
    
    # 测试路由
    with app.test_client() as client:
        # 测试根路径
        response = client.get('/')
        print(f"✅ 根路径状态码: {response.status_code}")
        
        # 测试登录页面
        response = client.get('/auth/login')
        print(f"✅ 登录页面状态码: {response.status_code}")
        
        # 测试健康检查
        response = client.get('/health')
        print(f"✅ 健康检查状态码: {response.status_code}")
        
    # 列出所有路由
    print("\n=== 注册的路由 ===")
    for rule in app.url_map.iter_rules():
        print(f"  {rule.rule} -> {rule.endpoint}")
        
except Exception as e:
    print(f"❌ 应用测试失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("✅ 应用测试完成")
EOF

# 重新构建镜像（如果需要）
echo "重新构建Docker镜像..."
docker build -t crm-app:latest .

# 启动新容器，先用测试模式
echo "启动测试容器..."
docker run --rm -v $(pwd)/test_app.py:/app/test_app.py crm-app:latest python test_app.py

# 如果测试通过，启动正式容器
echo "启动正式容器..."
docker run -d \
    --name crm-app-fixed \
    --restart unless-stopped \
    -p 80:80 \
    -e FLASK_ENV=production \
    -e DATABASE_URL=sqlite:///instance/edu_crm.db \
    -e SECRET_KEY=crm-production-secret-$(date +%s) \
    -v /var/lib/crm/instance:/app/instance \
    -v /var/lib/crm/logs:/app/logs \
    crm-app:latest

# 等待启动
echo "等待应用启动..."
sleep 10

# 检查状态
echo "检查容器状态..."
docker ps | grep crm-app-fixed

echo "检查应用日志..."
docker logs crm-app-fixed | tail -20

# 测试访问
echo "测试应用访问..."
curl -I http://localhost:80
curl -I http://localhost:80/auth/login
curl -s http://localhost:80/health | head -5

echo "🎉 部署修复完成！"
echo "请访问: http://47.100.238.50"
