"""
移动端测试路由
用于测试移动端响应式功能
"""

from flask import Blueprint, render_template
from flask_login import login_required

mobile_test_bp = Blueprint('mobile_test', __name__)

@mobile_test_bp.route('/mobile-test')
@login_required
def mobile_test():
    """移动端响应式测试页面"""
    return render_template('mobile-test.html')
