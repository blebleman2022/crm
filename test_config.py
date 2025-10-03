#!/usr/bin/env python3
"""
测试配置加载是否正常
"""

import os
import sys

def test_config_import():
    """测试配置导入"""
    print("=" * 60)
    print("测试配置导入")
    print("=" * 60)
    
    try:
        from config import config, ProductionConfig, DevelopmentConfig, TestingConfig
        print("✅ 成功导入 config 模块")
        print(f"   - ProductionConfig: {ProductionConfig}")
        print(f"   - DevelopmentConfig: {DevelopmentConfig}")
        print(f"   - TestingConfig: {TestingConfig}")
        print(f"   - config字典: {config}")
        return True
    except Exception as e:
        print(f"❌ 导入 config 模块失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_create_app():
    """测试应用创建"""
    print("\n" + "=" * 60)
    print("测试应用创建")
    print("=" * 60)
    
    try:
        from run import create_app
        
        # 测试开发环境
        print("\n1. 测试开发环境...")
        app_dev = create_app('development')
        print(f"✅ 开发环境应用创建成功")
        print(f"   - DEBUG: {app_dev.config.get('DEBUG')}")
        print(f"   - TESTING: {app_dev.config.get('TESTING')}")
        
        # 测试生产环境
        print("\n2. 测试生产环境...")
        app_prod = create_app('production')
        print(f"✅ 生产环境应用创建成功")
        print(f"   - DEBUG: {app_prod.config.get('DEBUG')}")
        print(f"   - TESTING: {app_prod.config.get('TESTING')}")
        print(f"   - SESSION_COOKIE_SECURE: {app_prod.config.get('SESSION_COOKIE_SECURE')}")
        
        # 测试测试环境
        print("\n3. 测试测试环境...")
        app_test = create_app('testing')
        print(f"✅ 测试环境应用创建成功")
        print(f"   - DEBUG: {app_test.config.get('DEBUG')}")
        print(f"   - TESTING: {app_test.config.get('TESTING')}")
        
        return True
    except Exception as e:
        print(f"❌ 应用创建失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_gunicorn_import():
    """测试Gunicorn导入"""
    print("\n" + "=" * 60)
    print("测试Gunicorn导入")
    print("=" * 60)
    
    try:
        # 模拟Gunicorn导入应用
        os.environ['FLASK_ENV'] = 'production'
        from run import app
        print(f"✅ Gunicorn应用实例导入成功")
        print(f"   - 应用名称: {app.name}")
        print(f"   - DEBUG: {app.config.get('DEBUG')}")
        return True
    except Exception as e:
        print(f"❌ Gunicorn应用实例导入失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("EduConnect CRM 配置测试")
    print("=" * 60)
    
    results = []
    
    # 测试配置导入
    results.append(("配置导入", test_config_import()))
    
    # 测试应用创建
    results.append(("应用创建", test_create_app()))
    
    # 测试Gunicorn导入
    results.append(("Gunicorn导入", test_gunicorn_import()))
    
    # 输出测试结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    all_passed = True
    for name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{name}: {status}")
        if not passed:
            all_passed = False
    
    print("=" * 60)
    
    if all_passed:
        print("\n🎉 所有测试通过！配置修复成功！")
        return 0
    else:
        print("\n⚠️  部分测试失败，请检查错误信息")
        return 1

if __name__ == '__main__':
    sys.exit(main())

