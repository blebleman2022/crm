from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from functools import wraps
from models import Teacher, Customer, Lead, db
from datetime import datetime

teachers_bp = Blueprint('teachers', __name__)

def teacher_role_required(f):
    """班主任角色权限装饰器（只有teacher角色的用户可以访问）"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'teacher':
            flash('您没有权限访问此页面，仅班主任可访问', 'error')
            return redirect(url_for('leads.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

@teachers_bp.route('/list')
@login_required
@teacher_role_required
def list_teachers():
    """老师列表页"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '', type=str)
    status_filter = request.args.get('status', '', type=str)
    
    query = Teacher.query
    
    # 搜索过滤
    if search:
        query = query.filter(
            (Teacher.chinese_name.contains(search)) |
            (Teacher.english_name.contains(search)) |
            (Teacher.current_institution.contains(search)) |
            (Teacher.major_direction.contains(search))
        )
    
    # 状态筛选
    if status_filter == 'active':
        query = query.filter(Teacher.status == True)
    elif status_filter == 'inactive':
        query = query.filter(Teacher.status == False)
    
    # 按创建时间倒序排列
    query = query.order_by(Teacher.created_at.desc())
    
    # 分页
    per_page = 20
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    teachers = pagination.items
    
    # 统计每个老师负责的客户数量
    teacher_customer_counts = {}
    for teacher in teachers:
        count = Customer.query.filter(Customer.teacher_id == teacher.id).count()
        teacher_customer_counts[teacher.id] = count
    
    return render_template('teachers/list.html',
                         teachers=teachers,
                         pagination=pagination,
                         search=search,
                         status_filter=status_filter,
                         teacher_customer_counts=teacher_customer_counts)

@teachers_bp.route('/add', methods=['GET', 'POST'])
@login_required
@teacher_role_required
def add_teacher():
    """添加老师"""
    if request.method == 'POST':
        try:
            teacher = Teacher(
                chinese_name=request.form.get('chinese_name', '').strip(),
                english_name=request.form.get('english_name', '').strip(),
                current_institution=request.form.get('current_institution', '').strip(),
                major_direction=request.form.get('major_direction', '').strip(),
                highest_degree=request.form.get('highest_degree', '').strip(),
                degree_description=request.form.get('degree_description', '').strip(),
                research_achievements=request.form.get('research_achievements', '').strip(),
                innovation_coaching_achievements=request.form.get('innovation_coaching_achievements', '').strip(),
                social_roles=request.form.get('social_roles', '').strip(),
                status=True
            )
            
            # 验证必填字段
            if not teacher.chinese_name:
                flash('中文名为必填项', 'error')
                return render_template('teachers/add.html', teacher=teacher)
            
            db.session.add(teacher)
            db.session.commit()
            
            flash(f'老师 {teacher.chinese_name} 添加成功', 'success')
            return redirect(url_for('teachers.list_teachers'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'添加老师失败：{str(e)}', 'error')
            return render_template('teachers/add.html')
    
    return render_template('teachers/add.html')

@teachers_bp.route('/edit/<int:teacher_id>', methods=['GET', 'POST'])
@login_required
@teacher_role_required
def edit_teacher(teacher_id):
    """编辑老师"""
    teacher = Teacher.query.get_or_404(teacher_id)
    
    if request.method == 'POST':
        try:
            teacher.chinese_name = request.form.get('chinese_name', '').strip()
            teacher.english_name = request.form.get('english_name', '').strip()
            teacher.current_institution = request.form.get('current_institution', '').strip()
            teacher.major_direction = request.form.get('major_direction', '').strip()
            teacher.highest_degree = request.form.get('highest_degree', '').strip()
            teacher.degree_description = request.form.get('degree_description', '').strip()
            teacher.research_achievements = request.form.get('research_achievements', '').strip()
            teacher.innovation_coaching_achievements = request.form.get('innovation_coaching_achievements', '').strip()
            teacher.social_roles = request.form.get('social_roles', '').strip()
            
            # 验证必填字段
            if not teacher.chinese_name:
                flash('中文名为必填项', 'error')
                return render_template('teachers/edit.html', teacher=teacher)
            
            teacher.updated_at = datetime.utcnow()
            db.session.commit()
            
            flash(f'老师 {teacher.chinese_name} 更新成功', 'success')
            return redirect(url_for('teachers.list_teachers'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'更新老师失败：{str(e)}', 'error')
    
    return render_template('teachers/edit.html', teacher=teacher)

@teachers_bp.route('/detail/<int:teacher_id>')
@login_required
@teacher_role_required
def detail_teacher(teacher_id):
    """老师详情页"""
    teacher = Teacher.query.get_or_404(teacher_id)
    
    # 获取该老师负责的客户列表
    customers = Customer.query.filter(Customer.teacher_id == teacher_id).join(Lead).all()
    
    return render_template('teachers/detail.html', 
                         teacher=teacher,
                         customers=customers)

@teachers_bp.route('/delete/<int:teacher_id>', methods=['POST'])
@login_required
@teacher_role_required
def delete_teacher(teacher_id):
    """删除老师（软删除，设置status=False）"""
    try:
        teacher = Teacher.query.get_or_404(teacher_id)
        
        # 检查是否有客户关联
        customer_count = Customer.query.filter(Customer.teacher_id == teacher_id).count()
        if customer_count > 0:
            flash(f'无法删除老师 {teacher.chinese_name}，该老师还负责 {customer_count} 位客户', 'error')
            return redirect(url_for('teachers.list_teachers'))
        
        # 软删除
        teacher.status = False
        teacher.updated_at = datetime.utcnow()
        db.session.commit()
        
        flash(f'老师 {teacher.chinese_name} 已禁用', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'删除老师失败：{str(e)}', 'error')
    
    return redirect(url_for('teachers.list_teachers'))

@teachers_bp.route('/activate/<int:teacher_id>', methods=['POST'])
@login_required
@teacher_role_required
def activate_teacher(teacher_id):
    """启用老师"""
    try:
        teacher = Teacher.query.get_or_404(teacher_id)
        teacher.status = True
        teacher.updated_at = datetime.utcnow()
        db.session.commit()
        
        flash(f'老师 {teacher.chinese_name} 已启用', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'启用老师失败：{str(e)}', 'error')
    
    return redirect(url_for('teachers.list_teachers'))

@teachers_bp.route('/get_active_teachers', methods=['GET'])
@login_required
def get_active_teachers():
    """获取所有启用的老师（用于分配老师的下拉列表）"""
    teachers = Teacher.query.filter(Teacher.status == True).order_by(Teacher.chinese_name).all()
    return jsonify([{
        'id': t.id,
        'chinese_name': t.chinese_name,
        'english_name': t.english_name,
        'major_direction': t.major_direction
    } for t in teachers])

@teachers_bp.route('/assign/<int:customer_id>', methods=['POST'])
@login_required
def assign_teacher(customer_id):
    """分配老师给客户"""
    try:
        customer = Customer.query.get_or_404(customer_id)
        teacher_id = request.form.get('teacher_id', type=int)
        
        if not teacher_id:
            return jsonify({'success': False, 'message': '请选择老师'}), 400
        
        teacher = Teacher.query.get_or_404(teacher_id)
        
        if not teacher.status:
            return jsonify({'success': False, 'message': '该老师已被禁用'}), 400
        
        # 检查权限：只有班主任角色可以分配老师
        if current_user.role != 'teacher':
            return jsonify({'success': False, 'message': '只有班主任可以分配老师'}), 403
        
        old_teacher_name = customer.teacher.chinese_name if customer.teacher else '未分配'
        customer.teacher_id = teacher_id
        customer.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'已将老师从 {old_teacher_name} 更换为 {teacher.chinese_name}',
            'teacher_name': teacher.chinese_name
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'分配老师失败：{str(e)}'}), 500

@teachers_bp.route('/change/<int:customer_id>', methods=['POST'])
@login_required
def change_teacher(customer_id):
    """更换客户的老师（需要二次确认）"""
    try:
        customer = Customer.query.get_or_404(customer_id)
        teacher_id = request.json.get('teacher_id', type=int)
        confirmed = request.json.get('confirmed', False)
        
        if not teacher_id:
            return jsonify({'success': False, 'message': '请选择老师'}), 400
        
        teacher = Teacher.query.get_or_404(teacher_id)
        
        if not teacher.status:
            return jsonify({'success': False, 'message': '该老师已被禁用'}), 400
        
        # 检查权限：只有班主任角色可以更换老师
        if current_user.role != 'teacher':
            return jsonify({'success': False, 'message': '只有班主任可以更换老师'}), 403
        
        # 如果未确认，返回需要确认的信息
        if not confirmed:
            old_teacher_name = customer.teacher.chinese_name if customer.teacher else '未分配'
            return jsonify({
                'success': False,
                'need_confirm': True,
                'message': f'确定要将老师从 {old_teacher_name} 更换为 {teacher.chinese_name} 吗？'
            })
        
        # 已确认，执行更换
        old_teacher_name = customer.teacher.chinese_name if customer.teacher else '未分配'
        customer.teacher_id = teacher_id
        customer.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'已将老师从 {old_teacher_name} 更换为 {teacher.chinese_name}',
            'teacher_name': teacher.chinese_name
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'更换老师失败：{str(e)}'}), 500

