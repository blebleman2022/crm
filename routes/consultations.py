"""
咨询管理路由
"""

from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from models import db, Lead, Customer, CommunicationRecord
from datetime import datetime
import functools
from communication_utils import CommunicationManager

# 创建蓝图
consultations_bp = Blueprint('consultations', __name__)

def sales_required(f):
    """装饰器：要求销售权限"""
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role not in ['sales', 'admin']:
            flash('您没有权限访问此页面', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def sales_or_admin_required(f):
    """装饰器：要求销售或管理员权限"""
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role not in ['sales', 'admin']:
            flash('您没有权限访问此页面', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

@consultations_bp.route('/list')
@login_required
@sales_required
def list_consultations():
    """咨询管理主页面 - 显示所有已约见的线索"""
    try:
        # 查询所有有线下见面记录的线索（meeting_at不为空）
        leads_with_meetings = db.session.query(Lead).filter(
            Lead.meeting_at.isnot(None)
        ).order_by(Lead.meeting_at.desc()).all()

        return render_template('consultations/list.html',
                             consultation_data=leads_with_meetings)

    except Exception as e:
        flash(f'获取咨询数据失败: {str(e)}', 'error')
        return render_template('consultations/list.html', consultation_data=[])

@consultations_bp.route('/details/<int:lead_id>')
@login_required
@sales_required
def consultation_details(lead_id):
    """线索咨询明细页面"""
    try:
        # 获取线索信息
        lead = Lead.query.get_or_404(lead_id)

        # 获取该线索对应的客户记录（如果存在）
        customer = Customer.query.filter_by(lead_id=lead_id).first()

        # 获取该线索的所有沟通记录
        communication_records = CommunicationManager.get_all_communications_by_lead(lead_id)

        return render_template('consultations/details.html',
                             lead=lead,
                             customer=customer,
                             communication_records=communication_records)

    except Exception as e:
        flash(f'获取咨询明细失败: {str(e)}', 'error')
        return redirect(url_for('consultations.list_consultations'))

# 旧的add_consultation_feedback函数已删除，现在使用统一的add_communication_record函数



@consultations_bp.route('/details_data/<int:lead_id>')
@login_required
@sales_or_admin_required
def consultation_details_data(lead_id):
    """获取咨询明细数据（JSON格式）"""
    try:
        # 获取线索信息
        lead = Lead.query.get_or_404(lead_id)

        # 获取该线索对应的客户记录（如果存在）
        customer = Customer.query.filter_by(lead_id=lead_id).first()

        # 检查是否只获取客户阶段记录
        customer_only = request.args.get('customer_only', 'false').lower() == 'true'

        # 获取沟通记录
        if customer_only and customer:
            communication_records = CommunicationManager.get_customer_communications(customer.id)
        else:
            communication_records = CommunicationManager.get_all_communications_by_lead(lead_id)

        # 格式化沟通记录
        communication_records_data = []
        for record in communication_records:
            stage = "客户阶段" if record.customer_id else "线索阶段"
            communication_records_data.append({
                'id': record.id,
                'content': record.content,
                'created_at': record.created_at.isoformat() if record.created_at else None,
                'stage': stage,
                'lead_id': record.lead_id,
                'customer_id': record.customer_id
            })

        # 获取统计信息
        stats = CommunicationManager.get_communication_stats(lead_id)

        # 构建响应数据
        response_data = {
            'lead': {
                'id': lead.id,
                'student_name': lead.student_name,
                'parent_wechat_display_name': lead.parent_wechat_display_name,
                'parent_wechat_name': lead.parent_wechat_name,
                'contact_info': lead.contact_info,
                'grade': lead.grade,
                'meeting_at': lead.meeting_at.isoformat() if lead.meeting_at else None,
                'meeting_location': lead.meeting_location,
                'lead_source': lead.lead_source,
                'stage': lead.stage,
                'created_at': lead.created_at.isoformat() if lead.created_at else None
            },
            'customer': {
                'id': customer.id if customer else None,
                'service_type': customer.service_type if customer else None,
                'payment_amount': float(customer.payment_amount) if customer and customer.payment_amount else None,
                'converted_at': customer.converted_at.isoformat() if customer and customer.converted_at else None
            } if customer else None,
            'communication_records': communication_records_data,
            'stats': stats
        }

        return jsonify({
            'success': True,
            'data': {
                'lead': response_data['lead'],
                'customer': response_data['customer'],
                'communication_records': communication_records_data,
                'stats': stats
            }
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取咨询明细失败: {str(e)}'
        }), 500

@consultations_bp.route('/add_communication/<int:lead_id>', methods=['POST'])
@login_required
@sales_or_admin_required
def add_communication_record(lead_id):
    """添加沟通记录 - 使用统一沟通记录表"""
    try:
        # 获取线索信息
        lead = Lead.query.get_or_404(lead_id)

        # 获取表单数据
        content = request.form.get('content', '').strip()
        consultation_time_str = request.form.get('communication_time', '').strip()

        if not content:
            raise ValueError('沟通内容不能为空')

        # 解析时间
        consultation_time = datetime.now()
        if consultation_time_str:
            try:
                consultation_time = datetime.fromisoformat(consultation_time_str.replace('T', ' '))
            except ValueError:
                consultation_time = datetime.now()

        # 检查是否已转化为客户
        customer = Customer.query.filter_by(lead_id=lead_id).first()

        if customer:
            # 客户阶段：添加客户沟通记录
            record = CommunicationManager.add_customer_communication(
                lead_id=lead_id,
                customer_id=customer.id,
                content=content,
                created_at=consultation_time
            )
        else:
            # 线索阶段：添加线索沟通记录
            record = CommunicationManager.add_lead_communication(
                lead_id=lead_id,
                content=content,
                created_at=consultation_time
            )

        # 检查请求是否为AJAX
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', ''):
            return jsonify({
                'success': True,
                'message': '沟通记录添加成功',
                'record': {
                    'id': record.id,
                    'content': record.content,
                    'created_at': record.created_at.isoformat(),
                    'stage': '客户阶段' if record.customer_id else '线索阶段'
                }
            })
        else:
            flash('沟通记录添加成功', 'success')
            return redirect(url_for('consultations.consultation_details', lead_id=lead_id))

    except Exception as e:
        db.session.rollback()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', ''):
            return jsonify({
                'success': False,
                'message': f'添加沟通记录失败: {str(e)}'
            }), 500
        else:
            flash(f'添加沟通记录失败: {str(e)}', 'error')
            return redirect(url_for('consultations.consultation_details', lead_id=lead_id))

@consultations_bp.route('/update_meeting_time/<int:lead_id>', methods=['POST'])
@login_required
@sales_required
def update_meeting_time(lead_id):
    """更新约见时间"""
    try:
        lead = Lead.query.get_or_404(lead_id)
        
        meeting_date = request.form.get('meeting_date', '').strip()
        meeting_hour = request.form.get('meeting_hour', '').strip()
        meeting_minute = request.form.get('meeting_minute', '').strip()
        meeting_location = request.form.get('meeting_location', '').strip()
        
        if meeting_date and meeting_hour and meeting_minute:
            # 组合完整的datetime
            meeting_datetime_str = f"{meeting_date}T{meeting_hour}:{meeting_minute}"
            try:
                meeting_datetime = datetime.fromisoformat(meeting_datetime_str)
                lead.meeting_at = meeting_datetime
                
                if meeting_location:
                    lead.meeting_location = meeting_location
                
                db.session.commit()
                flash('约见时间更新成功', 'success')
            except ValueError:
                flash('时间格式不正确', 'error')
        else:
            # 清空约见时间
            lead.meeting_at = None
            lead.meeting_location = None
            db.session.commit()
            flash('约见时间已清空', 'success')
        
        return redirect(url_for('consultations.list_consultations'))
    
    except Exception as e:
        db.session.rollback()
        flash(f'更新约见时间失败: {str(e)}', 'error')
        return redirect(url_for('consultations.list_consultations'))
