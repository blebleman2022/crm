from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from functools import wraps
from models import Teacher, Customer, Lead, TeacherImage, db
from datetime import datetime
import os
from werkzeug.utils import secure_filename

teachers_bp = Blueprint('teachers', __name__)

def teacher_supervisor_required(f):
    """班主任角色权限装饰器（只有teacher_supervisor角色的用户可以访问）"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'teacher_supervisor':
            flash('您没有权限访问此页面，仅班主任可访问', 'error')
            return redirect(url_for('leads.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def sales_manager_required(f):
    """销售管理角色权限装饰器（只有sales_manager角色的用户可以访问）"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'sales_manager':
            flash('您没有权限访问此页面，仅销售管理可访问', 'error')
            return redirect(url_for('leads.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

@teachers_bp.route('/list')
@login_required
@teacher_supervisor_required
def list_teachers():
    """老师列表页"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '', type=str)
    status_filter = request.args.get('status', '', type=str)

    # 数据隔离：只查询当前班主任创建的老师
    query = Teacher.query.filter(Teacher.created_by_user_id == current_user.id)

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
@teacher_supervisor_required
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
                status=True,
                created_by_user_id=current_user.id  # 记录创建人
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
@teacher_supervisor_required
def edit_teacher(teacher_id):
    """编辑老师"""
    teacher = Teacher.query.get_or_404(teacher_id)

    # 权限检查：只能编辑自己创建的老师
    if teacher.created_by_user_id != current_user.id:
        flash('您只能编辑自己创建的老师信息', 'error')
        return redirect(url_for('teachers.list_teachers'))

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
@teacher_supervisor_required
def detail_teacher(teacher_id):
    """老师详情页"""
    teacher = Teacher.query.get_or_404(teacher_id)

    # 权限检查：只能查看自己创建的老师
    if teacher.created_by_user_id != current_user.id:
        flash('您只能查看自己创建的老师信息', 'error')
        return redirect(url_for('teachers.list_teachers'))

    # 获取该老师负责的客户列表
    customers = Customer.query.filter(Customer.teacher_id == teacher_id).join(Lead).all()
    
    return render_template('teachers/detail.html', 
                         teacher=teacher,
                         customers=customers)

@teachers_bp.route('/delete/<int:teacher_id>', methods=['POST'])
@login_required
@teacher_supervisor_required
def delete_teacher(teacher_id):
    """删除老师（软删除，设置status=False）"""
    try:
        teacher = Teacher.query.get_or_404(teacher_id)

        # 权限检查：只能删除自己创建的老师
        if teacher.created_by_user_id != current_user.id:
            flash('您只能删除自己创建的老师', 'error')
            return redirect(url_for('teachers.list_teachers'))

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
@teacher_supervisor_required
def activate_teacher(teacher_id):
    """启用老师"""
    try:
        teacher = Teacher.query.get_or_404(teacher_id)

        # 权限检查：只能启用自己创建的老师
        if teacher.created_by_user_id != current_user.id:
            flash('您只能启用自己创建的老师', 'error')
            return redirect(url_for('teachers.list_teachers'))

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
    # 数据隔离：只返回当前班主任创建的启用老师
    if current_user.role == 'teacher_supervisor':
        teachers = Teacher.query.filter(
            Teacher.status == True,
            Teacher.created_by_user_id == current_user.id
        ).order_by(Teacher.chinese_name).all()
    else:
        # 非班主任角色返回空列表
        teachers = []

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
        if current_user.role != 'teacher_supervisor':
            return jsonify({'success': False, 'message': '只有班主任可以分配老师'}), 403

        # 权限检查：只能分配自己创建的老师
        if teacher.created_by_user_id != current_user.id:
            return jsonify({'success': False, 'message': '您只能分配自己创建的老师'}), 403
        
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

        # 获取JSON数据
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': '无效的请求数据'}), 400

        teacher_id = data.get('teacher_id')
        confirmed = data.get('confirmed', False)

        if not teacher_id:
            return jsonify({'success': False, 'message': '请选择老师'}), 400

        # 转换为整数
        try:
            teacher_id = int(teacher_id)
        except (ValueError, TypeError):
            return jsonify({'success': False, 'message': '无效的老师ID'}), 400

        teacher = Teacher.query.get_or_404(teacher_id)

        if not teacher.status:
            return jsonify({'success': False, 'message': '该老师已被禁用'}), 400

        # 检查权限：只有班主任角色可以更换老师
        if current_user.role != 'teacher_supervisor':
            return jsonify({'success': False, 'message': '只有班主任可以更换老师'}), 403

        # 权限检查：只能分配自己创建的老师
        if teacher.created_by_user_id != current_user.id:
            return jsonify({'success': False, 'message': '您只能分配自己创建的老师'}), 403

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


# 图片上传相关配置
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB
MAX_IMAGES_PER_TEACHER = 5
UPLOAD_FOLDER = 'static/uploads/teacher_images'

def allowed_image_file(filename):
    """检查文件扩展名是否允许"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS

@teachers_bp.route('/upload-image/<int:teacher_id>', methods=['POST'])
@login_required
@teacher_supervisor_required
def upload_teacher_image(teacher_id):
    """上传老师图片"""
    teacher = Teacher.query.get_or_404(teacher_id)

    # 权限检查：只能为自己创建的老师上传图片
    if teacher.created_by_user_id != current_user.id:
        return jsonify({'success': False, 'message': '您只能为自己创建的老师上传图片'}), 403

    # 检查当前图片数量
    current_image_count = TeacherImage.query.filter_by(teacher_id=teacher_id).count()
    if current_image_count >= MAX_IMAGES_PER_TEACHER:
        return jsonify({'success': False, 'message': f'最多只能上传{MAX_IMAGES_PER_TEACHER}张图片'}), 400

    # 检查是否有文件
    if 'images' not in request.files:
        return jsonify({'success': False, 'message': '请选择要上传的图片'}), 400

    files = request.files.getlist('images')
    descriptions = request.form.getlist('descriptions')

    if not files or files[0].filename == '':
        return jsonify({'success': False, 'message': '请选择要上传的图片'}), 400

    # 检查上传数量
    if len(files) + current_image_count > MAX_IMAGES_PER_TEACHER:
        return jsonify({'success': False, 'message': f'最多只能上传{MAX_IMAGES_PER_TEACHER}张图片，当前已有{current_image_count}张'}), 400

    try:
        # 确保上传目录存在
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)

        uploaded_images = []

        for idx, file in enumerate(files):
            # 检查文件类型
            if not allowed_image_file(file.filename):
                continue

            # 检查文件大小
            file.seek(0, os.SEEK_END)
            file_size = file.tell()
            file.seek(0)

            if file_size > MAX_IMAGE_SIZE:
                return jsonify({'success': False, 'message': f'图片 {file.filename} 超过5MB限制'}), 400

            # 生成安全的文件名
            original_filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"teacher_{teacher_id}_{timestamp}_{idx}_{original_filename}"
            filepath = os.path.join(UPLOAD_FOLDER, filename)

            # 保存文件
            file.save(filepath)

            # 获取对应的描述
            description = descriptions[idx] if idx < len(descriptions) else ''

            # 保存到数据库
            teacher_image = TeacherImage(
                teacher_id=teacher_id,
                image_path=f'uploads/teacher_images/{filename}',
                description=description.strip(),
                file_size=file_size,
                file_name=original_filename
            )
            db.session.add(teacher_image)
            uploaded_images.append({
                'id': teacher_image.id,
                'filename': original_filename,
                'description': description
            })

        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'成功上传{len(uploaded_images)}张图片',
            'images': uploaded_images
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'上传失败：{str(e)}'}), 500

@teachers_bp.route('/delete-image/<int:image_id>', methods=['POST'])
@login_required
@teacher_supervisor_required
def delete_teacher_image(image_id):
    """删除老师图片"""
    try:
        image = TeacherImage.query.get_or_404(image_id)
        teacher = Teacher.query.get_or_404(image.teacher_id)

        # 权限检查：只能删除自己创建的老师的图片
        if teacher.created_by_user_id != current_user.id:
            return jsonify({'success': False, 'message': '您只能删除自己创建的老师的图片'}), 403

        # 1. 先记录文件路径
        filepath = os.path.join('static', image.image_path)

        # 2. 删除数据库记录（先删除数据库，保证数据一致性）
        db.session.delete(image)
        db.session.commit()

        # 3. 最后删除文件（即使失败也不影响数据一致性）
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
            except Exception as e:
                # 记录日志，但不影响主流程
                import logging
                logging.warning(f"文件删除失败: {filepath}, 错误: {e}")

        return jsonify({'success': True, 'message': '图片删除成功'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'删除失败：{str(e)}'}), 500

@teachers_bp.route('/update-image-description/<int:image_id>', methods=['POST'])
@login_required
@teacher_supervisor_required
def update_image_description(image_id):
    """更新图片描述"""
    try:
        image = TeacherImage.query.get_or_404(image_id)
        teacher = Teacher.query.get_or_404(image.teacher_id)

        # 权限检查：只能更新自己创建的老师的图片描述
        if teacher.created_by_user_id != current_user.id:
            return jsonify({'success': False, 'message': '您只能更新自己创建的老师的图片描述'}), 403

        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': '无效的请求数据'}), 400

        description = data.get('description', '').strip()
        image.description = description

        db.session.commit()

        return jsonify({'success': True, 'message': '描述更新成功'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'更新失败：{str(e)}'}), 500


# ==================== 销售管理角色专用路由 ====================

@teachers_bp.route('/list_for_sales')
@login_required
@sales_manager_required
def list_teachers_for_sales():
    """销售管理角色的老师列表页（只读）"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '', type=str)
    status_filter = request.args.get('status', '', type=str)

    # 销售管理可以查看所有老师
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

    return render_template('teachers/list_for_sales.html',
                         teachers=teachers,
                         pagination=pagination,
                         search=search,
                         status_filter=status_filter,
                         teacher_customer_counts=teacher_customer_counts)

@teachers_bp.route('/detail_for_sales/<int:teacher_id>')
@login_required
@sales_manager_required
def detail_teacher_for_sales(teacher_id):
    """销售管理角色的老师详情页（只读）"""
    teacher = Teacher.query.get_or_404(teacher_id)

    # 获取该老师负责的客户列表
    customers = Customer.query.filter(Customer.teacher_id == teacher_id).join(Lead).all()

    return render_template('teachers/detail.html',
                         teacher=teacher,
                         customers=customers,
                         is_sales_manager_view=True)  # 标记为销售管理视图

