from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from functools import wraps
from models import CompetitionName, SystemConfig, User, db
from datetime import datetime

config_bp = Blueprint('config', __name__)

def admin_required(f):
    """管理员权限装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            flash('您没有权限访问此页面', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

@config_bp.route('/competitions')
@login_required
@admin_required
def competition_list():
    """竞赛名称配置列表"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '', type=str)
    
    query = CompetitionName.query
    
    # 搜索过滤
    if search:
        query = query.filter(CompetitionName.name.contains(search))
    
    # 分页
    competitions = query.order_by(CompetitionName.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('config/competition_list.html', 
                         competitions=competitions, 
                         search=search)

@config_bp.route('/competitions/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_competition():
    """添加竞赛名称"""
    if request.method == 'POST':
        competition_name = request.form.get('competition_name', '').strip()
        description = request.form.get('description', '').strip()
        
        # 验证必填字段
        if not competition_name:
            flash('竞赛名称为必填项', 'error')
            return render_template('config/add_competition.html')
        
        # 检查重复
        existing = CompetitionConfig.query.filter_by(competition_name=competition_name).first()
        if existing:
            flash('竞赛名称已存在', 'error')
            return render_template('config/add_competition.html')
        
        try:
            competition = CompetitionConfig(
                competition_name=competition_name,
                description=description
            )
            db.session.add(competition)
            db.session.commit()
            
            flash(f'竞赛名称 {competition_name} 添加成功', 'success')
            return redirect(url_for('config.competition_list'))
        except Exception as e:
            db.session.rollback()
            flash(f'添加竞赛名称失败: {str(e)}', 'error')
    
    return render_template('config/add_competition.html')

@config_bp.route('/competitions/<int:competition_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_competition(competition_id):
    """编辑竞赛名称"""
    competition = CompetitionConfig.query.get_or_404(competition_id)
    
    if request.method == 'POST':
        competition_name = request.form.get('competition_name', '').strip()
        description = request.form.get('description', '').strip()
        
        # 验证必填字段
        if not competition_name:
            flash('竞赛名称为必填项', 'error')
            return render_template('config/edit_competition.html', competition=competition)
        
        # 检查重复（排除自己）
        existing = CompetitionConfig.query.filter(
            CompetitionConfig.competition_name == competition_name,
            CompetitionConfig.id != competition_id
        ).first()
        if existing:
            flash('竞赛名称已存在', 'error')
            return render_template('config/edit_competition.html', competition=competition)
        
        try:
            competition.competition_name = competition_name
            competition.description = description
            competition.updated_at = datetime.utcnow()
            
            db.session.commit()
            flash(f'竞赛名称 {competition_name} 更新成功', 'success')
            return redirect(url_for('config.competition_list'))
        except Exception as e:
            db.session.rollback()
            flash(f'更新竞赛名称失败: {str(e)}', 'error')
    
    return render_template('config/edit_competition.html', competition=competition)

@config_bp.route('/competitions/<int:competition_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_competition(competition_id):
    """删除竞赛名称"""
    competition = CompetitionConfig.query.get_or_404(competition_id)
    
    try:
        # 检查是否有关联的交付记录
        from models import CompetitionDelivery
        delivery_count = CompetitionDelivery.query.filter_by(competition_name=competition.competition_name).count()
        
        if delivery_count > 0:
            return jsonify({
                'success': False, 
                'message': f'无法删除，该竞赛名称已被 {delivery_count} 个交付记录使用'
            })
        
        db.session.delete(competition)
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': f'竞赛名称 {competition.competition_name} 删除成功'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'删除失败: {str(e)}'})

@config_bp.route('/api/competitions')
@login_required
def api_competitions():
    """获取竞赛名称列表API（用于下拉选择）"""
    competitions = CompetitionName.query.order_by(CompetitionName.name).all()

    return jsonify([{
        'id': comp.id,
        'name': comp.name,
        'description': comp.description
    } for comp in competitions])


# ==================== 付款锁定管理 ====================

@config_bp.route('/payment-lock')
@login_required
@admin_required
def payment_lock():
    """付款锁定管理页面"""
    # 获取当前锁定配置
    lock_config = SystemConfig.query.filter_by(config_key='payment_lock_month').first()

    lock_info = None
    if lock_config:
        updater = User.query.get(lock_config.updated_by) if lock_config.updated_by else None
        lock_info = {
            'lock_month': lock_config.config_value,
            'updated_by': updater.username if updater else '未知',
            'updated_at': lock_config.updated_at.strftime('%Y-%m-%d %H:%M:%S') if lock_config.updated_at else None,
            'description': lock_config.description
        }

    return render_template('config/payment_lock.html', lock_info=lock_info)


@config_bp.route('/payment-lock/set', methods=['POST'])
@login_required
@admin_required
def set_payment_lock():
    """设置付款锁定月份"""
    try:
        lock_month = request.form.get('lock_month', '').strip()

        if not lock_month:
            flash('请选择锁定月份', 'error')
            return redirect(url_for('config.payment_lock'))

        # 验证月份格式
        try:
            datetime.strptime(lock_month, '%Y-%m')
        except ValueError:
            flash('月份格式错误，应为YYYY-MM', 'error')
            return redirect(url_for('config.payment_lock'))

        # 更新或创建配置
        config = SystemConfig.query.filter_by(config_key='payment_lock_month').first()
        if config:
            old_value = config.config_value
            config.config_value = lock_month
            config.updated_by = current_user.id
            config.updated_at = datetime.utcnow()
            action = '更新'
        else:
            config = SystemConfig(
                config_key='payment_lock_month',
                config_value=lock_month,
                description='付款记录锁定月份（该月份及之前的付款记录不可编辑）',
                updated_by=current_user.id
            )
            db.session.add(config)
            old_value = None
            action = '设置'

        db.session.commit()

        flash(f'已{action}锁定月份为 {lock_month}，该月份及之前的所有付款记录将无法编辑', 'success')
        return redirect(url_for('config.payment_lock'))

    except Exception as e:
        db.session.rollback()
        flash(f'设置失败：{str(e)}', 'error')
        return redirect(url_for('config.payment_lock'))


@config_bp.route('/payment-lock/clear', methods=['POST'])
@login_required
@admin_required
def clear_payment_lock():
    """清除付款锁定"""
    try:
        config = SystemConfig.query.filter_by(config_key='payment_lock_month').first()

        if not config:
            flash('当前没有锁定设置', 'warning')
            return redirect(url_for('config.payment_lock'))

        old_value = config.config_value
        db.session.delete(config)
        db.session.commit()

        flash(f'已清除锁定设置（原锁定月份：{old_value}），所有付款记录现在可以编辑', 'success')
        return redirect(url_for('config.payment_lock'))

    except Exception as e:
        db.session.rollback()
        flash(f'清除失败：{str(e)}', 'error')
        return redirect(url_for('config.payment_lock'))
