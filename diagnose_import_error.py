#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
诊断 Flask 应用导入错误
用于排查 Internal Server Error 问题
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_module_import(module_name):
    """测试模块导入"""
    try:
        __import__(module_name)
        print(f"✅ {module_name}")
        return True
    except Exception as e:
        print(f"❌ {module_name}: {e}")
        import traceback
        traceback.print_exc()
        print()
        return False

def main():
    print("=" * 60)
    print("🔍 Flask 应用导入诊断")
    print("=" * 60)
    print()
    
    # 测试基础模块
    print("1. 测试基础模块")
    print("-" * 60)
    base_modules = ['flask', 'sqlalchemy', 'werkzeug']
    for module in base_modules:
        test_module_import(module)
    print()
    
    # 测试项目模块
    print("2. 测试项目核心模块")
    print("-" * 60)
    core_modules = ['models', 'decorators']
    for module in core_modules:
        test_module_import(module)
    print()
    
    # 测试路由模块
    print("3. 测试路由模块")
    print("-" * 60)
    route_modules = [
        'routes.auth',
        'routes.leads', 
        'routes.customers',
        'routes.payments',
        'routes.admin',
        'routes.teachers',
        'routes.teacher',
        'routes.query',
        'routes.topic_tasks',
    ]
    
    failed_modules = []
    for module in route_modules:
        if not test_module_import(module):
            failed_modules.append(module)
    print()
    
    # 测试 Flask 应用
    print("4. 测试 Flask 应用启动")
    print("-" * 60)
    try:
        from run import app
        print("✅ Flask 应用创建成功")
        
        # 测试应用上下文
        with app.app_context():
            print("✅ 应用上下文正常")
            
            # 测试数据库连接
            from models import db
            try:
                db.session.execute('SELECT 1')
                print("✅ 数据库连接正常")
            except Exception as e:
                print(f"❌ 数据库连接失败: {e}")
        
        print()
        print("✅ Flask 应用完全正常!")
        
    except Exception as e:
        print(f"❌ Flask 应用启动失败: {e}")
        import traceback
        traceback.print_exc()
        failed_modules.append('run')
    
    print()
    print("=" * 60)
    print("📊 诊断总结")
    print("=" * 60)
    
    if failed_modules:
        print(f"❌ 发现 {len(failed_modules)} 个模块导入失败:")
        for module in failed_modules:
            print(f"   - {module}")
        print()
        print("建议:")
        print("1. 检查上述模块的语法错误")
        print("2. 检查模块的依赖关系")
        print("3. 查看详细的错误堆栈信息")
    else:
        print("✅ 所有模块导入正常!")
        print()
        print("如果仍然报错,请检查:")
        print("1. Gunicorn 配置")
        print("2. Nginx 配置")
        print("3. 文件权限")
    
    print()
    print("=" * 60)

if __name__ == '__main__':
    main()

