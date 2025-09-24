#!/usr/bin/env python3
"""
简化的CRM启动脚本 - 用于调试部署问题
"""

import os
import sys
from flask import Flask

def create_simple_app():
    """创建简化的Flask应用用于测试"""
    app = Flask(__name__)
    
    @app.route('/')
    def hello():
        return '''
        <h1>🎉 EduConnect CRM 测试页面</h1>
        <p>如果您看到这个页面，说明应用已经成功启动！</p>
        <p>环境: {}</p>
        <p>端口: {}</p>
        <p>主机: {}</p>
        '''.format(
            os.environ.get('FLASK_ENV', 'unknown'),
            os.environ.get('PORT', '5000'),
            '0.0.0.0'
        )
    
    @app.route('/health')
    def health():
        return {'status': 'ok', 'message': 'CRM应用运行正常'}
    
    return app

if __name__ == '__main__':
    print("🚀 启动简化版CRM应用...")
    
    # 获取配置
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV', 'development') == 'development'
    
    print(f"端口: {port}")
    print(f"调试模式: {debug}")
    print(f"环境: {os.environ.get('FLASK_ENV', 'development')}")
    
    # 创建并启动应用
    app = create_simple_app()
    
    try:
        app.run(
            host='0.0.0.0',
            port=port,
            debug=debug,
            threaded=True
        )
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        sys.exit(1)
