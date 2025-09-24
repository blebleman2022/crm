#!/usr/bin/env python3
"""
构建wheel包的脚本，用于离线安装
在有网络的环境中运行此脚本，生成wheel包
"""

import subprocess
import sys
import os

def build_wheels():
    """构建wheel包"""
    packages = [
        'Flask==3.0.0',
        'Flask-SQLAlchemy==3.1.1', 
        'Flask-Login==0.6.3',
        'Flask-WTF==1.2.1',
        'python-dotenv==1.0.0',
        'gunicorn==21.2.0'
    ]
    
    # 创建wheels目录
    os.makedirs('wheels', exist_ok=True)
    
    for package in packages:
        print(f"Building wheel for {package}...")
        try:
            subprocess.run([
                sys.executable, '-m', 'pip', 'wheel',
                '--wheel-dir', 'wheels',
                '--no-deps',
                package
            ], check=True)
            print(f"✅ Successfully built wheel for {package}")
        except subprocess.CalledProcessError:
            print(f"❌ Failed to build wheel for {package}")
    
    print("\n🎉 Wheel building complete!")
    print("Upload the 'wheels' directory to your repository")

if __name__ == '__main__':
    build_wheels()
