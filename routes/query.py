from flask import Blueprint, render_template, request, jsonify
from models import Lead, db
import re

query_bp = Blueprint('query', __name__)

@query_bp.route('/leads-search')
def leads_search():
    """独立的线索查询页面"""
    return render_template('query/leads_search.html')

@query_bp.route('/api/search-leads', methods=['POST'])
def api_search_leads():
    """API接口：查询线索数据"""
    data = request.get_json()
    search_type = data.get('search_type', '')  # 'wechat' 或 'phone'
    search_value = data.get('search_value', '').strip()
    
    if not search_value:
        return jsonify({
            'success': False,
            'message': '请输入查询内容'
        })
    
    results = []
    
    try:
        if search_type == 'wechat':
            # 查询微信号（家长微信号）
            leads = Lead.query.filter(
                Lead.parent_wechat_name.like(f'%{search_value}%')
            ).all()
            
        elif search_type == 'phone':
            # 查询联系电话
            leads = Lead.query.filter(
                Lead.contact_info.like(f'%{search_value}%')
            ).all()
            
        else:
            return jsonify({
                'success': False,
                'message': '无效的查询类型'
            })
        
        # 格式化查询结果
        for lead in leads:
            results.append({
                'id': lead.id,
                'student_name': lead.student_name or '未填写',
                'parent_wechat_display_name': lead.parent_wechat_display_name or '未填写',
                'parent_wechat_name': lead.parent_wechat_name or '未填写',
                'contact_info': lead.contact_info or '未填写',
                'grade': lead.grade or '未填写',
                'lead_source': lead.lead_source or '未填写',
                'stage': lead.stage or '未填写',
                'sales_user_name': lead.sales_user.username if lead.sales_user else '未分配',
                'created_at': lead.created_at.strftime('%Y-%m-%d %H:%M:%S') if lead.created_at else '未知',
                'updated_at': lead.updated_at.strftime('%Y-%m-%d %H:%M:%S') if lead.updated_at else '未知'
            })
        
        return jsonify({
            'success': True,
            'count': len(results),
            'results': results,
            'message': f'找到 {len(results)} 条匹配记录'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'查询失败: {str(e)}'
        })

@query_bp.route('/api/exact-search', methods=['POST'])
def api_exact_search():
    """API接口：精确查询（检查是否存在）"""
    data = request.get_json()
    search_type = data.get('search_type', '')
    search_value = data.get('search_value', '').strip()
    
    if not search_value:
        return jsonify({
            'exists': False,
            'message': '请输入查询内容'
        })
    
    try:
        if search_type == 'wechat':
            # 精确查询微信号
            lead = Lead.query.filter_by(parent_wechat_name=search_value).first()
            
        elif search_type == 'phone':
            # 精确查询联系电话
            lead = Lead.query.filter_by(contact_info=search_value).first()
            
        else:
            return jsonify({
                'exists': False,
                'message': '无效的查询类型'
            })
        
        if lead:
            return jsonify({
                'exists': True,
                'lead_info': {
                    'id': lead.id,
                    'student_name': lead.student_name or '未填写',
                    'parent_wechat_display_name': lead.parent_wechat_display_name or '未填写',
                    'parent_wechat_name': lead.parent_wechat_name or '未填写',
                    'contact_info': lead.contact_info or '未填写',
                    'grade': lead.grade or '未填写',
                    'stage': lead.stage or '未填写',
                    'sales_user_name': lead.sales_user.username if lead.sales_user else '未分配',
                    'created_at': lead.created_at.strftime('%Y-%m-%d %H:%M:%S') if lead.created_at else '未知'
                },
                'message': '找到匹配记录'
            })
        else:
            return jsonify({
                'exists': False,
                'message': '未找到匹配记录'
            })
            
    except Exception as e:
        return jsonify({
            'exists': False,
            'message': f'查询失败: {str(e)}'
        })
