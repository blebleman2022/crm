"""
数据导出路由
仅销售管理角色可访问
"""

from flask import Blueprint, render_template, request, jsonify, send_file
from flask_login import login_required, current_user
from functools import wraps
from models import db, User, Lead, Customer, Payment, Teacher, TutoringDelivery, CompetitionDelivery, CommunicationRecord, LoginLog, CompetitionName, TeacherImage
from datetime import datetime
import pandas as pd
import io
import os

data_export_bp = Blueprint('data_export', __name__)

def sales_manager_required(f):
    """销售管理权限装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'sales_manager':
            from flask import flash, redirect, url_for
            flash('您没有权限访问此页面，仅销售管理可访问', 'error')
            return redirect(url_for('leads.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# 定义所有可导出的表及其中文名称
EXPORTABLE_TABLES = {
    'users': {
        'name': '用户表',
        'model': User,
        'columns': ['id', 'username', 'phone', 'role', 'status', 'created_at', 'updated_at'],
        'column_names': ['ID', '用户名', '手机号', '角色', '状态', '创建时间', '更新时间']
    },
    'leads': {
        'name': '线索表',
        'model': Lead,
        'columns': ['id', 'student_name', 'parent_wechat_display_name', 'parent_wechat_name', 
                   'contact_info', 'lead_source', 'grade', 'stage', 'sales_user_id', 
                   'contact_obtained_at', 'meeting_at', 'meeting_location', 'follow_up_notes', 
                   'created_at', 'updated_at'],
        'column_names': ['ID', '学员姓名', '家长微信昵称', '家长微信号', '联系方式', '线索来源', 
                        '年级', '阶段', '销售负责人ID', '获取联系方式时间', '约见时间', '约见地点', 
                        '跟进备注', '创建时间', '更新时间']
    },
    'customers': {
        'name': '客户表',
        'model': Customer,
        'columns': ['id', 'lead_id', 'sales_user_id', 'teacher_user_id', 'teacher_id', 
                   'service_type', 'payment_amount', 'is_priority', 'customer_notes', 
                   'converted_at', 'created_at', 'updated_at'],
        'column_names': ['ID', '线索ID', '销售负责人ID', '班主任ID', '辅导老师ID', '服务类型', 
                        '支付金额', '是否优先', '客户备注', '转化时间', '创建时间', '更新时间']
    },
    'payments': {
        'name': '付款记录表',
        'model': Payment,
        'columns': ['id', 'lead_id', 'amount', 'payment_date', 'payment_method', 'notes', 
                   'created_at', 'updated_at'],
        'column_names': ['ID', '线索ID', '金额', '付款日期', '付款方式', '备注', '创建时间', '更新时间']
    },
    'teachers': {
        'name': '老师表',
        'model': Teacher,
        'columns': ['id', 'chinese_name', 'english_name', 'current_institution', 'major', 
                   'highest_degree', 'education_background', 'research_achievements', 
                   'innovation_achievements', 'social_roles', 'status', 'created_at', 'updated_at'],
        'column_names': ['ID', '中文名', '英文名', '现单位', '专业方向', '最高学历', '教育背景', 
                        '科研成果', '科创辅导成果', '社会角色', '状态', '创建时间', '更新时间']
    },
    'tutoring_deliveries': {
        'name': '课题辅导交付表',
        'model': TutoringDelivery,
        'columns': ['id', 'customer_id', 'project_topic', 'project_description', 
                   'start_date', 'expected_completion_date', 'actual_completion_date', 
                   'status', 'progress_notes', 'created_at', 'updated_at'],
        'column_names': ['ID', '客户ID', '课题名称', '课题描述', '开始日期', '预计完成日期', 
                        '实际完成日期', '状态', '进度备注', '创建时间', '更新时间']
    },
    'competition_deliveries': {
        'name': '竞赛交付表',
        'model': CompetitionDelivery,
        'columns': ['id', 'customer_id', 'competition_name', 'target_award_level', 
                   'registration_date', 'competition_date', 'result_date', 'actual_award_level', 
                   'status', 'notes', 'created_at', 'updated_at'],
        'column_names': ['ID', '客户ID', '竞赛名称', '目标奖项', '报名日期', '比赛日期', 
                        '结果公布日期', '实际奖项', '状态', '备注', '创建时间', '更新时间']
    },
    'communication_records': {
        'name': '沟通记录表',
        'model': CommunicationRecord,
        'columns': ['id', 'lead_id', 'customer_id', 'content', 'created_at'],
        'column_names': ['ID', '线索ID', '客户ID', '沟通内容', '创建时间']
    },
    'login_logs': {
        'name': '登录日志表',
        'model': LoginLog,
        'columns': ['id', 'user_id', 'login_time', 'ip_address', 'user_agent'],
        'column_names': ['ID', '用户ID', '登录时间', 'IP地址', '用户代理']
    },
    'competition_names': {
        'name': '竞赛名称配置表',
        'model': CompetitionName,
        'columns': ['id', 'name', 'category', 'description', 'is_active', 'created_at', 'updated_at'],
        'column_names': ['ID', '竞赛名称', '类别', '描述', '是否启用', '创建时间', '更新时间']
    }
}

@data_export_bp.route('/export')
@login_required
@sales_manager_required
def export_page():
    """数据导出页面"""
    return render_template('data_export/index.html', tables=EXPORTABLE_TABLES)

@data_export_bp.route('/export/download', methods=['POST'])
@login_required
@sales_manager_required
def download_data():
    """下载选中的表数据为Excel文件"""
    try:
        # 获取选中的表
        selected_tables = request.json.get('tables', [])
        
        if not selected_tables:
            return jsonify({'success': False, 'message': '请至少选择一个表'}), 400
        
        # 创建Excel写入器
        output = io.BytesIO()
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            for table_key in selected_tables:
                if table_key not in EXPORTABLE_TABLES:
                    continue
                
                table_info = EXPORTABLE_TABLES[table_key]
                model = table_info['model']
                columns = table_info['columns']
                column_names = table_info['column_names']
                
                # 查询数据
                query = db.session.query(model)
                
                # 特殊处理：用户表不导出密码相关字段
                if table_key == 'users':
                    data = []
                    for record in query.all():
                        row = {}
                        for col in columns:
                            value = getattr(record, col, None)
                            # 格式化特殊字段
                            if col == 'role':
                                role_map = {
                                    'admin': '管理员',
                                    'sales_manager': '销售管理',
                                    'salesperson': '销售专员',
                                    'teacher_supervisor': '班主任',
                                    'teacher': '老师'
                                }
                                value = role_map.get(value, value)
                            elif col == 'status':
                                value = '启用' if value else '禁用'
                            elif isinstance(value, datetime):
                                value = value.strftime('%Y-%m-%d %H:%M:%S')
                            row[col] = value
                        data.append(row)
                else:
                    # 其他表直接导出
                    data = []
                    for record in query.all():
                        row = {}
                        for col in columns:
                            value = getattr(record, col, None)
                            # 格式化日期时间
                            if isinstance(value, datetime):
                                value = value.strftime('%Y-%m-%d %H:%M:%S')
                            elif isinstance(value, bool):
                                value = '是' if value else '否'
                            row[col] = value
                        data.append(row)
                
                # 创建DataFrame
                if data:
                    df = pd.DataFrame(data)
                    # 重命名列为中文
                    df.columns = column_names
                else:
                    # 空表也创建表头
                    df = pd.DataFrame(columns=column_names)
                
                # 写入Excel，使用表的中文名作为sheet名
                sheet_name = table_info['name'][:31]  # Excel sheet名称最多31字符
                df.to_excel(writer, sheet_name=sheet_name, index=False)
        
        # 准备下载
        output.seek(0)
        
        # 生成文件名
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'数据导出_{timestamp}.xlsx'
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'导出失败：{str(e)}'}), 500

@data_export_bp.route('/export/preview/<table_key>')
@login_required
@sales_manager_required
def preview_table(table_key):
    """预览表数据（前10条）"""
    try:
        if table_key not in EXPORTABLE_TABLES:
            return jsonify({'success': False, 'message': '表不存在'}), 404
        
        table_info = EXPORTABLE_TABLES[table_key]
        model = table_info['model']
        columns = table_info['columns']
        column_names = table_info['column_names']
        
        # 查询前10条数据
        records = db.session.query(model).limit(10).all()
        
        data = []
        for record in records:
            row = {}
            for i, col in enumerate(columns):
                value = getattr(record, col, None)
                # 格式化显示
                if isinstance(value, datetime):
                    value = value.strftime('%Y-%m-%d %H:%M:%S')
                elif isinstance(value, bool):
                    value = '是' if value else '否'
                elif value is None:
                    value = ''
                row[column_names[i]] = str(value)
            data.append(row)
        
        # 获取总记录数
        total_count = db.session.query(model).count()
        
        return jsonify({
            'success': True,
            'table_name': table_info['name'],
            'columns': column_names,
            'data': data,
            'total_count': total_count
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'预览失败：{str(e)}'}), 500

