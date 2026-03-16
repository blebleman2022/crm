"""
老师端路由
辅导老师的工作台、学生列表、文档上传等功能
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_login import login_required, current_user
from models import User, Customer, TutoringDelivery, DeliveryDocument, CustomerCompetition, TopicTask, TopicSubmission, Lead, db
from functools import wraps
from werkzeug.utils import secure_filename
from communication_utils import CommunicationManager
import os
from datetime import datetime

teacher_bp = Blueprint('teacher', __name__, url_prefix='/teacher')

def teacher_required(f):
    """装饰器：要求当前用户是辅导老师（role='teacher'）"""
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not hasattr(current_user, 'role') or current_user.role != 'teacher':
            flash('此页面仅限辅导老师访问', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

# Dashboard路由已移除 - 老师登录后直接进入学生列表页
# @teacher_bp.route('/dashboard')
# @teacher_required
# def dashboard():
#     """老师工作台"""
#     # 获取该老师负责的所有学生
#     students = Customer.query.filter_by(teacher_id=current_user.id).all()
#
#     # 统计信息
#     total_students = len(students)
#
#     # 统计文档完成情况
#     doc_stats = {
#         'thesis_draft': 0,
#         'thesis_final': 0,
#         'presentation': 0,
#         'novelty_report': 0,
#         'plagiarism_report': 0,
#         'evaluation_material': 0
#     }
#
#     for student in students:
#         for doc_type in doc_stats.keys():
#             if DeliveryDocument.query.filter_by(
#                 customer_id=student.id,
#                 doc_type=doc_type,
#                 is_latest=True
#             ).first():
#                 doc_stats[doc_type] += 1
#
#     # 计算完成率
#     doc_completion_rates = {}
#     if total_students > 0:
#         for doc_type, count in doc_stats.items():
#             doc_completion_rates[doc_type] = round(count / total_students * 100, 1)
#     else:
#         doc_completion_rates = {k: 0 for k in doc_stats.keys()}
#
#     # 统计即将到期的课题（7天内）
#     from datetime import date, timedelta
#     today = date.today()
#     deadline_7days = today + timedelta(days=7)
#
#     upcoming_deadlines = []
#     overdue_count = 0
#
#     for student in students:
#         if student.thesis_deadline:
#             days_left = (student.thesis_deadline - today).days
#             if student.thesis_deadline < today:
#                 overdue_count += 1
#             elif student.thesis_deadline <= deadline_7days:
#                 upcoming_deadlines.append({
#                     'student': student,
#                     'days_left': days_left
#                 })
#
#     # 按剩余天数排序
#     upcoming_deadlines.sort(key=lambda x: x['days_left'])
#
#     return render_template('teacher/dashboard.html',
#                          students=students,
#                          total_students=total_students,
#                          doc_stats=doc_stats,
#                          doc_completion_rates=doc_completion_rates,
#                          upcoming_deadlines=upcoming_deadlines,
#                          overdue_count=overdue_count)

@teacher_bp.route('/students')
@teacher_required
def student_list():
    """学生列表"""
    from datetime import datetime
    from sqlalchemy import func

    # 获取该老师负责的所有学生
    # current_user.id 是 User 表的 ID，需要通过 teacher_profile 获取 Teacher 表的 ID
    print(f"[DEBUG] student_list - current_user.id: {current_user.id}")
    print(f"[DEBUG] student_list - current_user.username: {current_user.username}")
    print(f"[DEBUG] student_list - current_user.teacher_profile: {current_user.teacher_profile}")

    teacher = current_user.teacher_profile
    if not teacher:
        print(f"[DEBUG] student_list - teacher_profile 为 None,重定向到登录页")
        flash('未找到老师信息', 'error')
        return redirect(url_for('auth.login'))

    # 预加载 tutoring_delivery 关联数据以显示课程进度
    from sqlalchemy.orm import joinedload
    students = Customer.query.options(joinedload(Customer.tutoring_delivery)).filter_by(tutor_user_id=teacher.user_id).all()

    # 批量查询每个学生的赛事数量（已报名的赛事）
    student_ids = [student.id for student in students]
    competition_registered_counts = {}
    competition_award_achieved = {}

    if student_ids:
        counts = db.session.query(
            CustomerCompetition.customer_id,
            func.count(CustomerCompetition.id).label('count')
        ).filter(
            CustomerCompetition.customer_id.in_(student_ids),
            CustomerCompetition.status != '未报名'
        ).group_by(CustomerCompetition.customer_id).all()

        competition_registered_counts = {customer_id: count for customer_id, count in counts}

        # 判断每个学生是否达成奖项要求
        for student in students:
            award_level = student.lead.competition_award_level
            if not award_level:
                competition_award_achieved[student.id] = False
                continue

            # 获取学生的所有赛事
            competitions = CustomerCompetition.query.filter_by(customer_id=student.id).all()
            achieved = False

            for comp in competitions:
                status = comp.status
                # 市奖要求：市级或以上奖项
                if award_level == '市奖':
                    if status in ['市级一等奖', '市级二等奖', '市级三等奖',
                                  '国家一等奖', '国家二等奖', '国家三等奖']:
                        achieved = True
                        break
                # 国奖要求：国家级奖项
                elif award_level == '国奖':
                    if status in ['国家一等奖', '国家二等奖', '国家三等奖']:
                        achieved = True
                        break

            competition_award_achieved[student.id] = achieved

    return render_template('teacher/student_list.html',
                         students=students,
                         now=datetime.utcnow(),
                         competition_registered_counts=competition_registered_counts,
                         competition_award_achieved=competition_award_achieved)

@teacher_bp.route('/topic-tasks')
@teacher_required
def topic_tasks():
    """老师课题选项任务列表"""
    tasks = TopicTask.query.filter_by(tutor_user_id=current_user.id).filter(TopicTask.status != TopicTask.STATUS_DRAFT).order_by(TopicTask.created_at.desc(), TopicTask.id.desc()).all()
    now = datetime.utcnow()
    updated = False
    for task in tasks:
        if task.status == TopicTask.STATUS_DRAFT:
            continue
        submission = TopicSubmission.query.filter_by(task_id=task.id).first()
        if submission:
            if task.status != TopicTask.STATUS_SUBMITTED:
                task.status = TopicTask.STATUS_SUBMITTED
                updated = True
        else:
            if task.due_at and task.due_at < now and task.status != TopicTask.STATUS_OVERDUE:
                task.status = TopicTask.STATUS_OVERDUE
                updated = True
    if updated:
        db.session.commit()

    # 预加载提交内容
    task_data = []
    for task in tasks:
        submission = TopicSubmission.query.filter_by(task_id=task.id).first()
        task_data.append({
            'task': task,
            'lead': task.lead,
            'submission': submission
        })

    return render_template('teacher/topic_tasks.html', task_data=task_data, now=datetime.utcnow())

@teacher_bp.route('/topic-tasks/<int:task_id>/submit', methods=['POST'])
@teacher_required
def submit_topic_task(task_id):
    task = TopicTask.query.get_or_404(task_id)
    if task.tutor_user_id != current_user.id:
        return jsonify({'success': False, 'message': '无权提交该任务'}), 403

    data = request.get_json(silent=True) or {}
    content = (data.get('content') or '').strip()
    if not content:
        return jsonify({'success': False, 'message': '内容不能为空'}), 400

    submission = TopicSubmission.query.filter_by(task_id=task.id).first()
    if submission:
        submission.content = content
        submission.submitted_at = datetime.utcnow()
    else:
        submission = TopicSubmission(task_id=task.id, content=content, submitted_at=datetime.utcnow())
        db.session.add(submission)

    task.status = TopicTask.STATUS_SUBMITTED
    task.updated_at = datetime.utcnow()
    db.session.commit()

    return jsonify({'success': True, 'message': '提交成功'})

@teacher_bp.route('/students/<int:customer_id>')
@teacher_required
def student_detail(customer_id):
    """学生详情页"""
    # 获取老师信息
    teacher = current_user.teacher_profile
    if not teacher:
        flash('未找到老师信息', 'error')
        return redirect(url_for('auth.login'))

    # 获取学生信息
    student = Customer.query.get_or_404(customer_id)

    # 验证该学生是否属于当前老师
    if student.tutor_user_id != teacher.user_id:
        flash('您无权查看此学生信息', 'error')
        return redirect(url_for('teacher.student_list'))
    
    # 获取该学生的所有文档（其他材料允许多份）
    documents = DeliveryDocument.query.filter_by(
        customer_id=customer_id
    ).order_by(DeliveryDocument.created_at.desc()).all()
    
    # 按文档类型分组
    docs_by_type = {}
    for doc in documents:
        if doc.doc_type == 'other_materials':
            docs_by_type.setdefault(doc.doc_type, []).append(doc)
        else:
            if doc.is_latest or doc.doc_type not in docs_by_type:
                docs_by_type[doc.doc_type] = doc
    
    return render_template('teacher/student_detail.html',
                         student=student,
                         docs_by_type=docs_by_type)

@teacher_bp.route('/students/<int:customer_id>/api')
@teacher_required
def get_student_api(customer_id):
    """获取学生信息的 API"""
    # 获取老师信息
    teacher = current_user.teacher_profile
    if not teacher:
        return jsonify({'success': False, 'message': '未找到老师信息'}), 403

    student = Customer.query.get_or_404(customer_id)

    # 验证该学生是否属于当前老师
    if student.tutor_user_id != teacher.user_id:
        return jsonify({'success': False, 'message': '您无权查看此学生信息'}), 403

    # 获取 TutoringDelivery 获取课时信息
    tutoring_delivery = TutoringDelivery.query.filter_by(customer_id=customer_id).first()
    default_total_sessions = student.lead.contract_total_sessions if student.lead and student.lead.contract_total_sessions else 6
    total_sessions = tutoring_delivery.total_sessions if tutoring_delivery else default_total_sessions
    completed_sessions = tutoring_delivery.completed_sessions if tutoring_delivery else 0

    # 获取赛事信息
    customer_competitions = CustomerCompetition.query.filter_by(customer_id=customer_id).all()
    competitions = []
    for cc in customer_competitions:
        competitions.append({
            'id': cc.id,
            'name': cc.competition_name.name if cc.competition_name else '',
            'status': cc.status,
        })

    # 获取文档（其他材料允许多份）
    documents = DeliveryDocument.query.filter_by(
        customer_id=customer_id
    ).order_by(DeliveryDocument.created_at.desc()).all()

    docs_by_type = {}
    for doc in documents:
        doc_payload = {
            'id': doc.id,
            'file_name': doc.file_name,
            'version': doc.version,
            'created_at': doc.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }
        if doc.doc_type == 'other_materials':
            docs_by_type.setdefault(doc.doc_type, []).append(doc_payload)
        else:
            if doc.is_latest or doc.doc_type not in docs_by_type:
                docs_by_type[doc.doc_type] = doc_payload

    # 安全获取 lead 信息（处理 lead 为空的情况）
    lead_info = {}
    if student.lead:
        lead_info = {
            'student_name': student.lead.student_name or '',
            'grade': student.lead.grade or '',
            'contact_info': student.lead.contact_info or '',
            'service_types': student.lead.service_types or '[]'
        }
    else:
        lead_info = {
            'student_name': '未知学员',
            'grade': '',
            'contact_info': '',
            'service_types': '[]'
        }

    # 为了兼容新的课程进度编辑弹窗,同时返回扁平化的字段
    return jsonify({
        'success': True,
        'student_name': lead_info.get('student_name', ''),
        'thesis_name': student.thesis_name or '',
        'total_sessions': total_sessions,
        'completed_sessions': completed_sessions,
        'student': {
            'id': student.id,
            'thesis_name': student.thesis_name or '',
            'thesis_deadline': student.thesis_deadline.strftime('%Y-%m-%d') if student.thesis_deadline else None,
            'total_sessions': total_sessions,
            'completed_sessions': completed_sessions,
            'lead': lead_info,
            'competitions': competitions,
            'documents': docs_by_type
        }
    })

@teacher_bp.route('/students/<int:customer_id>/update_thesis_name', methods=['POST'])
@teacher_required
def update_thesis_name(customer_id):
    """更新学生的课题名称"""
    # 获取老师信息
    teacher = current_user.teacher_profile
    if not teacher:
        return jsonify({'success': False, 'message': '未找到老师信息'}), 403

    student = Customer.query.get_or_404(customer_id)

    # 验证权限 - 只能修改自己负责的学生
    if student.tutor_user_id != teacher.user_id:
        return jsonify({'success': False, 'message': '您无权修改此学生信息'}), 403

    # 支持JSON和表单两种格式
    if request.is_json:
        data = request.get_json()
        thesis_name = data.get('thesis_name', '').strip()
    else:
        thesis_name = request.form.get('thesis_name', '').strip()

    if not thesis_name:
        return jsonify({'success': False, 'message': '课题名称不能为空'}), 400

    if len(thesis_name) > 200:
        return jsonify({'success': False, 'message': '课题名称不能超过200个字符'}), 400

    try:
        student.thesis_name = thesis_name
        db.session.commit()
        return jsonify({'success': True, 'message': '课题名称更新成功', 'thesis_name': thesis_name})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'更新失败: {str(e)}'}), 500

@teacher_bp.route('/students/<int:customer_id>/communication_records', methods=['GET', 'POST'])
@teacher_required
def manage_communication_records(customer_id):
    """获取/新增客户阶段沟通记录（老师端）"""
    teacher = current_user.teacher_profile
    if not teacher:
        return jsonify({'success': False, 'message': '未找到老师信息'}), 403

    student = Customer.query.get_or_404(customer_id)
    if student.tutor_user_id != teacher.user_id:
        return jsonify({'success': False, 'message': '您无权查看此学生信息'}), 403

    if request.method == 'GET':
        records = CommunicationManager.get_customer_communications(customer_id)
        data = []
        for record in records:
            data.append({
                'id': record.id,
                'content': record.content,
                'created_at': record.created_at.isoformat() if record.created_at else None,
                'user_name': record.user.username if record.user else None
            })

        lead = student.lead
        return jsonify({
            'success': True,
            'student': {
                'name': lead.student_name if lead else '未知学员',
                'grade': lead.grade if lead else ''
            },
            'communication_records': data
        })

    # POST - add communication record
    content = request.form.get('content', '').strip()
    communication_time = request.form.get('communication_time', '').strip()
    if not content:
        return jsonify({'success': False, 'message': '沟通内容不能为空'}), 400

    created_at = datetime.utcnow()
    if communication_time:
        try:
            created_at = datetime.fromisoformat(communication_time.replace('T', ' '))
        except ValueError:
            created_at = datetime.utcnow()

    try:
        CommunicationManager.add_customer_communication(
            lead_id=student.lead_id,
            customer_id=customer_id,
            content=content,
            user_id=current_user.id,
            created_at=created_at
        )
        return jsonify({'success': True, 'message': '沟通记录添加成功'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'添加失败: {str(e)}'}), 500

# ==================== 文档上传管理 ====================

# 允许的文件扩展名
ALLOWED_EXTENSIONS = {'doc', 'docx', 'pdf', 'ppt', 'pptx'}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

# 文档类型映射
DOC_TYPE_NAMES = {
    'thesis_draft': '课题初稿',
    'thesis_final': '终稿',
    'presentation': '演示方案',
    'novelty_report': '查新报告',
    'plagiarism_report': '查重报告',
    'evaluation_material': '高三综评材料',
    'preview_material': '预习材料',
    'other_materials': '其他材料'
}

def allowed_file(filename):
    """检查文件扩展名是否允许"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_upload_folder():
    """获取上传文件夹路径"""
    upload_folder = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads', 'documents')
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)
    return upload_folder

@teacher_bp.route('/students/<int:customer_id>/upload/<doc_type>', methods=['POST'])
@teacher_required
def upload_document(customer_id, doc_type):
    """上传文档"""
    # 获取老师信息
    teacher = current_user.teacher_profile
    if not teacher:
        return jsonify({'success': False, 'message': '未找到老师信息'}), 403

    # 验证学生是否属于当前老师
    student = Customer.query.get_or_404(customer_id)
    if student.tutor_user_id != teacher.user_id:
        return jsonify({'success': False, 'message': '您没有权限为该学生上传文档'}), 403

    # 验证文档类型
    if doc_type not in DOC_TYPE_NAMES:
        return jsonify({'success': False, 'message': '无效的文档类型'}), 400

    # 检查文件
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': '未选择文件'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'message': '未选择文件'}), 400

    # 验证文件扩展名
    if not allowed_file(file.filename):
        return jsonify({'success': False, 'message': '不支持的文件格式，仅支持: doc, docx, pdf, ppt, pptx'}), 400

    # 验证文件大小
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)

    if file_size > MAX_FILE_SIZE:
        return jsonify({'success': False, 'message': f'文件大小超过限制（最大{MAX_FILE_SIZE // 1024 // 1024}MB）'}), 400

    try:
        # 从原始文件名提取扩展名；secure_filename 对中文名可能仅返回 "pdf"（无点）
        # 这里保留原始文件名用于展示，保存时仍使用系统生成的安全文件名
        file_ext = file.filename.rsplit('.', 1)[1].lower()
        original_filename = file.filename.replace('\\', '/').split('/')[-1].strip()
        if not original_filename:
            original_filename = secure_filename(file.filename) or f"upload.{file_ext}"

        # 获取当前该类型文档的最新版本
        if doc_type == 'other_materials':
            latest_doc = DeliveryDocument.query.filter_by(
                customer_id=customer_id,
                doc_type=doc_type
            ).order_by(DeliveryDocument.version.desc()).first()
        else:
            latest_doc = DeliveryDocument.query.filter_by(
                customer_id=customer_id,
                doc_type=doc_type,
                is_latest=True
            ).first()

        # "其他材料"允许多份，不删除旧文件
        if doc_type != 'other_materials' and latest_doc:
            old_file_path = latest_doc.file_path
            if os.path.exists(old_file_path):
                try:
                    os.remove(old_file_path)
                except Exception as e:
                    print(f'删除旧文件失败: {e}')

        # 生成新文件名: customer_id_doctype_timestamp.ext（无版本号）
        timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        new_filename = f"{customer_id}_{doc_type}_{timestamp}.{file_ext}"

        # 保存文件
        upload_folder = get_upload_folder()
        file_path = os.path.join(upload_folder, new_filename)
        file.save(file_path)

        # 删除旧版本的数据库记录（只保留最新版本）
        if doc_type != 'other_materials' and latest_doc:
            db.session.delete(latest_doc)

        # 版本号：其他材料递增，其它类型固定为1（只保留最新）
        next_version = 1
        if doc_type == 'other_materials' and latest_doc:
            next_version = (latest_doc.version or 1) + 1

        # 创建新的文档记录
        description = request.form.get('description', '').strip()

        new_doc = DeliveryDocument(
            customer_id=customer_id,
            doc_type=doc_type,
            file_name=original_filename,
            file_path=file_path,
            file_size=file_size,
            file_ext=file_ext,
            uploaded_by_type='teacher',
            uploaded_by_id=teacher.user_id,  # 使用 User.id
            uploaded_by_name=(teacher.user.username if teacher and teacher.user else current_user.username),
            version=next_version,
            is_latest=True,
            description=description
        )

        db.session.add(new_doc)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'{DOC_TYPE_NAMES[doc_type]}上传成功',
            'document': {
                'id': new_doc.id,
                'file_name': new_doc.file_name,
                'version': new_doc.version,
                'file_size': new_doc.file_size,
                'created_at': new_doc.created_at.strftime('%Y-%m-%d %H:%M:%S')
            }
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'上传失败: {str(e)}'}), 500


@teacher_bp.route('/documents/<int:doc_id>/download')
@teacher_required
def download_document(doc_id):
    """下载文档"""
    # 获取老师信息
    teacher = current_user.teacher_profile
    if not teacher:
        flash('未找到老师信息', 'error')
        return redirect(url_for('auth.login'))

    doc = DeliveryDocument.query.get_or_404(doc_id)

    # 验证权限：老师只能下载自己学生的文档
    student = Customer.query.get_or_404(doc.customer_id)
    if student.tutor_user_id != teacher.user_id:
        flash('您没有权限下载该文档', 'error')
        return redirect(url_for('teacher.student_list'))

    # 检查文件是否存在
    if not os.path.exists(doc.file_path):
        flash('文件不存在', 'error')
        return redirect(url_for('teacher.student_detail', customer_id=doc.customer_id))

    return send_file(doc.file_path, as_attachment=True, download_name=doc.file_name)


@teacher_bp.route('/documents/<int:doc_id>/delete', methods=['POST'])
@teacher_required
def delete_document(doc_id):
    """删除文档"""
    # 获取老师信息
    teacher = current_user.teacher_profile
    if not teacher:
        return jsonify({'success': False, 'message': '未找到老师信息'}), 403

    doc = DeliveryDocument.query.get_or_404(doc_id)

    # 验证权限：只有上传者可以删除
    if doc.uploaded_by_type != 'teacher' or doc.uploaded_by_id != teacher.user_id:
        return jsonify({'success': False, 'message': '您没有权限删除该文档'}), 403

    # 验证学生是否属于当前老师
    student = Customer.query.get_or_404(doc.customer_id)
    if student.tutor_user_id != teacher.user_id:
        return jsonify({'success': False, 'message': '您没有权限删除该文档'}), 403

    try:
        # 删除物理文件
        if os.path.exists(doc.file_path):
            os.remove(doc.file_path)

        # 删除数据库记录
        doc_type_name = DOC_TYPE_NAMES.get(doc.doc_type, '文档')
        db.session.delete(doc)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'{doc_type_name}删除成功'
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'删除失败: {str(e)}'}), 500


@teacher_bp.route('/students/<int:customer_id>/documents/<doc_type>')
@teacher_required
def get_documents(customer_id, doc_type):
    """获取某类型的所有文档版本"""
    # 获取老师信息
    teacher = current_user.teacher_profile
    if not teacher:
        return jsonify({'success': False, 'message': '未找到老师信息'}), 403

    # 验证学生是否属于当前老师
    student = Customer.query.get_or_404(customer_id)
    if student.tutor_user_id != teacher.user_id:
        return jsonify({'success': False, 'message': '您没有权限访问该学生的文档'}), 403

    # 获取该类型的所有文档，按版本倒序
    documents = DeliveryDocument.query.filter_by(
        customer_id=customer_id,
        doc_type=doc_type
    ).order_by(DeliveryDocument.version.desc()).all()

    docs_data = [{
        'id': doc.id,
        'file_name': doc.file_name,
        'version': doc.version,
        'is_latest': doc.is_latest,
        'file_size': doc.file_size,
        'uploaded_by_name': doc.uploaded_by_name,
        'created_at': doc.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        'description': doc.description
    } for doc in documents]

    return jsonify({
        'success': True,
        'documents': docs_data
    })


@teacher_bp.route('/students/<int:customer_id>/update-course-progress', methods=['POST'])
@teacher_required
def update_course_progress(customer_id):
    """更新课程进度"""
    teacher = current_user.teacher_profile
    if not teacher:
        return jsonify({'success': False, 'message': '未找到老师信息'})

    # 验证学生是否属于该老师
    student = Customer.query.get_or_404(customer_id)
    if student.tutor_user_id != teacher.user_id:
        return jsonify({'success': False, 'message': '无权操作此学生'})

    data = request.get_json() or {}

    # 更新课题名称
    student.thesis_name = data.get('thesis_name')

    default_total_sessions = student.lead.contract_total_sessions if student.lead and student.lead.contract_total_sessions else 6

    # 更新或创建课程交付记录
    delivery = student.tutoring_delivery
    if not delivery:
        delivery = TutoringDelivery(
            customer_id=customer_id,
            total_sessions=default_total_sessions,
            completed_sessions=0,
            remaining_sessions=default_total_sessions
        )
        db.session.add(delivery)

    # 辅导老师不能修改总课程数，总课程数由销售维护
    total_sessions = delivery.total_sessions or default_total_sessions
    completed_sessions = data.get('completed_sessions', 0)
    try:
        completed_sessions = int(completed_sessions)
    except (TypeError, ValueError):
        return jsonify({'success': False, 'message': '已完成数量格式错误'}), 400

    if completed_sessions < 0:
        return jsonify({'success': False, 'message': '已完成数量不能为负数'}), 400
    if completed_sessions > total_sessions:
        return jsonify({'success': False, 'message': '已完成数量不能大于总课程数量'}), 400

    delivery.total_sessions = total_sessions
    delivery.completed_sessions = completed_sessions
    delivery.update_remaining_sessions()

    db.session.commit()

    return jsonify({'success': True, 'message': '保存成功'})

