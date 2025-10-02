#!/usr/bin/env python3
"""
配置检查脚本 - 验证云服务器配置是否满足要求
"""

import os
import sys

def print_header(title):
    """打印标题"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)

def print_check(item, status, message=""):
    """打印检查结果"""
    symbol = "✅" if status else "❌"
    print(f"{symbol} {item}: {message if message else ('通过' if status else '失败')}")

def check_files():
    """检查必要文件是否存在"""
    print_header("检查必要文件")
    
    required_files = {
        'config.py': '统一配置文件',
        'run.py': '应用启动文件',
        'models.py': '数据模型文件',
        'docker-compose.yml': 'Docker编排文件',
        'Dockerfile': 'Docker镜像文件',
        'requirements.txt': 'Python依赖文件',
    }
    
    all_exist = True
    for file, desc in required_files.items():
        exists = os.path.exists(file)
        print_check(f"{file} ({desc})", exists)
        all_exist = all_exist and exists
    
    return all_exist

def check_config_py():
    """检查config.py配置"""
    print_header("检查config.py配置")
    
    try:
        from config import config, BaseConfig
        
        # 检查配置类
        print_check("BaseConfig类", 'BaseConfig' in dir())
        print_check("DevelopmentConfig", 'development' in config)
        print_check("ProductionConfig", 'production' in config)
        print_check("TestingConfig", 'testing' in config)
        
        # 检查数据库路径配置
        db_uri = BaseConfig.SQLALCHEMY_DATABASE_URI
        print_check("数据库URI配置", db_uri is not None, db_uri)
        
        # 检查是否使用绝对路径
        if 'sqlite:///' in db_uri:
            is_absolute = os.path.isabs(db_uri.replace('sqlite:///', ''))
            print_check("数据库使用绝对路径", is_absolute, 
                       "使用绝对路径" if is_absolute else "使用相对路径")
        
        return True
    except Exception as e:
        print_check("config.py导入", False, str(e))
        return False

def check_docker_compose():
    """检查docker-compose.yml配置"""
    print_header("检查docker-compose.yml配置")
    
    try:
        with open('docker-compose.yml', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查关键配置
        checks = {
            'DATABASE_URL配置': 'DATABASE_URL=' in content,
            '数据库绝对路径': 'sqlite:////app/instance/edu_crm.db' in content,
            'instance卷挂载': './instance:/app/instance' in content,
            'logs卷挂载': './logs:/app/logs' in content,
            '端口映射': '5000:5000' in content,
        }
        
        all_pass = True
        for check, result in checks.items():
            print_check(check, result)
            all_pass = all_pass and result
        
        # 显示DATABASE_URL配置
        for line in content.split('\n'):
            if 'DATABASE_URL=' in line:
                print(f"\n  当前配置: {line.strip()}")
        
        return all_pass
    except Exception as e:
        print_check("docker-compose.yml读取", False, str(e))
        return False

def check_requirements():
    """检查requirements.txt"""
    print_header("检查requirements.txt")
    
    try:
        with open('requirements.txt', 'r', encoding='utf-8') as f:
            content = f.read()
        
        required_packages = {
            'Flask': 'Flask==',
            'SQLAlchemy': 'SQLAlchemy==',
            'Flask-Login': 'Flask-Login==',
            'Pillow': 'Pillow==',
            'gunicorn': 'gunicorn==',
        }
        
        all_found = True
        for package, pattern in required_packages.items():
            found = pattern in content
            print_check(package, found)
            all_found = all_found and found
        
        return all_found
    except Exception as e:
        print_check("requirements.txt读取", False, str(e))
        return False

def check_run_py():
    """检查run.py配置加载"""
    print_header("检查run.py配置加载")
    
    try:
        with open('run.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查是否使用统一配置
        checks = {
            '使用统一config.py': 'from config import config' in content,
            '不引用config_production': 'config_production' not in content,
            '配置类正确获取': "config.get(config_name" in content,
        }
        
        all_pass = True
        for check, result in checks.items():
            print_check(check, result)
            all_pass = all_pass and result
        
        return all_pass
    except Exception as e:
        print_check("run.py读取", False, str(e))
        return False

def check_directories():
    """检查必要目录"""
    print_header("检查必要目录")
    
    required_dirs = ['instance', 'logs', 'routes', 'templates', 'utils']
    
    all_exist = True
    for dir_name in required_dirs:
        exists = os.path.isdir(dir_name)
        print_check(f"{dir_name}/", exists)
        all_exist = all_exist and exists
    
    return all_exist

def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("  EduConnect CRM 配置检查工具")
    print("=" * 60)
    print(f"\n当前目录: {os.getcwd()}")
    
    # 执行所有检查
    results = {
        '文件检查': check_files(),
        '目录检查': check_directories(),
        'config.py检查': check_config_py(),
        'run.py检查': check_run_py(),
        'docker-compose.yml检查': check_docker_compose(),
        'requirements.txt检查': check_requirements(),
    }
    
    # 总结
    print_header("检查总结")
    
    all_pass = all(results.values())
    for check, result in results.items():
        print_check(check, result)
    
    print("\n" + "=" * 60)
    if all_pass:
        print("  ✅ 所有检查通过！配置满足云服务器部署要求")
    else:
        print("  ⚠️  部分检查未通过，请修复后再部署")
    print("=" * 60 + "\n")
    
    return 0 if all_pass else 1

if __name__ == '__main__':
    sys.exit(main())

