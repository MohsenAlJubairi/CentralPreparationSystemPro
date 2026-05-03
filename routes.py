from flask import render_template, request, redirect, url_for, flash
from flask_login import login_user, login_required, logout_user, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from models import db, User, Student, Attendance
from datetime import date, datetime
from io import BytesIO
from urllib.parse import urlparse, urljoin
from sqlalchemy.exc import IntegrityError
import pandas as pd
import json
import os

# =========================================================================
# دوال مساعدة للأمان والتكوين
# =========================================================================
SETTINGS_FILE = 'settings.json'

def get_setting(key, default):
    """قراءة الإعدادات من ملف لتجنب مشاكل Thread-Safety في بيئة الإنتاج"""
    if not os.path.exists(SETTINGS_FILE): return default
    try:
        with open(SETTINGS_FILE, 'r') as f:
            return json.load(f).get(key, default)
    except: return default

def set_setting(key, value):
    """حفظ الإعدادات بأمان"""
    settings = {}
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r') as f:
                settings = json.load(f)
        except: pass
    settings[key] = value
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(settings, f)

def is_safe_url(target):
    """التحقق من الروابط لمنع ثغرات Open Redirect"""
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc

# =========================================================================

def register_routes(app):

    # ملاحظة: لتفعيل CSRF، قم بتثبيت flask_wtf وإلغاء تعليق الأسطر التالية، 
    # ثم أضف {{ csrf_token() }} في جميع نماذج HTML.
    # from flask_wtf.csrf import CSRFProtect
    # csrf = CSRFProtect(app)

    # =========================================================================
    # 1. مسارات المصادقة (تسجيل الدخول والخروج)
    # =========================================================================
    @app.route('/')
    def home():
        return redirect(url_for('login'))

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if current_user.is_authenticated:
            if current_user.role == 'developer':
                return redirect(url_for('manage_admins')) 
            elif current_user.role == 'admin':
                return redirect(url_for('admin_dashboard')) 
            else:
                return redirect(url_for('mandoob_dashboard')) 

        if request.method == 'POST':
            username = request.form.get('username')
            password = request.form.get('password')
            remember = True if request.form.get('remember') else False
            
            user = User.query.filter_by(username=username).first()
            
            if user and check_password_hash(user.password, password):
                if not user.is_active:
                    flash('تم تعطيل حسابك. راجع إدارة السكن.', 'error')
                    return render_template('login.html')
                    
                login_user(user, remember=remember)
                
                if user.role == 'developer':
                    return redirect(url_for('manage_admins'))
                elif user.role == 'admin': 
                    return redirect(url_for('admin_dashboard'))
                else: 
                    return redirect(url_for('mandoob_dashboard'))
            else:
                flash('اسم المستخدم أو كلمة المرور غير صحيحة', 'error')
        return render_template('login.html')

    @app.route('/logout')
    @login_required
    def logout():
        logout_user()
        flash('تم تسجيل الخروج بنجاح.', 'success')
        return redirect(url_for('login'))

    @app.route('/import_students', methods=['POST'])
    @login_required
    def import_students():
        if current_user.role != 'admin':
            return "غير مصرح", 403

        file = request.files.get('excel_file')
        import_mode = request.form.get('import_mode') 
        col_name = request.form.get('col_name', 'الاسم').strip()
        col_apt = request.form.get('col_apt', 'رقم الشقة').strip()
        col_room = request.form.get('col_room', 'رقم الغرفة').strip()

        if not file or not file.filename.endswith(('.xls', '.xlsx')):
            flash('الرجاء اختيار ملف إكسل صالح أولاً', 'error')
            return redirect(url_for('manage_students'))

        try:
            # حماية من استنزاف الذاكرة (DoS) - التوقف عند 5 ميغابايت
            file_bytes = file.read(5 * 1024 * 1024) 
            if len(file.read(1)) > 0: 
                flash('حجم الملف كبير جداً! الحد الأقصى المسموح به هو 5 ميغابايت.', 'error')
                return redirect(url_for('manage_students'))
                
            df = pd.read_excel(BytesIO(file_bytes))
            df.columns = df.columns.str.strip()

            if col_name not in df.columns or col_apt not in df.columns:
                available_cols = " ، ".join(df.columns.astype(str))
                flash(f'خطأ: لم يتم العثور على عمود "{col_name}" أو "{col_apt}". الأعمدة الموجودة في ملفك هي: ({available_cols})', 'error')
                return redirect(url_for('manage_students'))

            df.dropna(how='all', inplace=True)

            if import_mode == 'clear':
                Student.query.update({'status': 'مفصول'})
                User.query.filter(User.role == 'mandoob').update({'is_active': False})
                db.session.commit()
                flash('تم أرشفة العام السابق بنجاح.', 'info')

            added_count = 0
            for _, row in df.iterrows():
                f_name = str(row.get(col_name, '')).strip()
                a_num = row.get(col_apt)
                r_num = row.get(col_room)

                if pd.isna(a_num) or not f_name or f_name.lower() in ['nan', 'none', 'null', '']: 
                    continue

                try:
                    apt_val = int(float(a_num))
                    room_val = int(float(r_num)) if pd.notna(r_num) and str(r_num).strip() != '' else 0
                except ValueError:
                    continue

                new_student = Student(full_name=f_name, apartment_number=apt_val, room_number=room_val, status='فعال')
                db.session.add(new_student)
                added_count += 1

            if added_count > 0:
                db.session.commit()
                flash(f'تم استيراد {added_count} طالب بنجاح!', 'success')
            else:
                db.session.rollback()
                flash('لم يتم استيراد أي طالب! تأكد من صحة البيانات.', 'error')

        except Exception as e:
            db.session.rollback()
            flash('حدث خطأ أثناء قراءة الملف تأكد من التنسيق.', 'error')

        return redirect(url_for('manage_students'))

    # =========================================================================
    # 2. لوحة تحكم الإدارة (الرئيسية والإحصائيات)
    # =========================================================================
    @app.route('/admin')
    @login_required
    def admin_dashboard():
        if current_user.role == 'developer':
            return redirect(url_for('manage_admins'))
        if current_user.role != 'admin':
            flash('تحذير أمني: محاولة وصول غير مصرح بها!', 'error')
            return redirect(url_for('mandoob_dashboard'))
            
        today = date.today()
        
        total_students = Student.query.filter(Student.status.in_(['فعال', 'نشط', 'موجود', 'في إجازة'])).count()
        present_count = Attendance.query.filter_by(date=today, status='حاضر').count()
        absent_count = Attendance.query.filter_by(date=today, status='غائب').count()
        excused_count = Attendance.query.filter_by(date=today, status='مستأذن').count()
        leave_count = Student.query.filter_by(status='في إجازة').count()
        
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')
        status_filter = request.args.get('status', 'all') 
        apt_filters = request.args.getlist('apartments')
        room_filters = request.args.getlist('rooms')

        if start_date_str and end_date_str:
            s_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            e_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            dates_query = db.session.query(Attendance.date).filter(Attendance.date >= s_date, Attendance.date <= e_date).distinct().order_by(Attendance.date.desc()).all()
        else:
            dates_query = db.session.query(Attendance.date).distinct().order_by(Attendance.date.desc()).limit(7).all()
            
        dates = [d[0] for d in dates_query]
        dates.sort() 
        
        student_query = Student.query.filter(Student.status.in_(['فعال', 'نشط', 'موجود', 'في إجازة']))
        if apt_filters:
            student_query = student_query.filter(Student.apartment_number.in_([int(a) for a in apt_filters]))
        if room_filters:
            student_query = student_query.filter(Student.room_number.in_([int(r) for r in room_filters]))
            
        # حماية الذاكرة بوضع حد (Limit) معقول إذا زادت البيانات
        students = student_query.order_by(Student.apartment_number, Student.room_number).limit(500).all()
        student_ids = [s.id for s in students]
        
        attendance_records = Attendance.query.filter(
            Attendance.date.in_(dates),
            Attendance.student_id.in_(student_ids)
        ).all() if dates and student_ids else []
        
        att_dict = {}
        att_dict_notes = {}

        for r in attendance_records:
            if r.student_id not in att_dict:
                att_dict[r.student_id] = {}
                att_dict_notes[r.student_id] = {} 

            att_dict[r.student_id][r.date] = r.status
            att_dict_notes[r.student_id][r.date] = r.note 

        if status_filter != 'all':
            filtered_students = [s for s in students if any(att_dict.get(s.id, {}).get(d) == status_filter for d in dates)]
            students = filtered_students

        allow_date = get_setting('ALLOW_DATE_CHANGE', False)

        return render_template('admin.html', 
                               current_user=current_user,
                               total_students=total_students,
                               present_count=present_count,
                               absent_count=absent_count,
                               excused_count=excused_count,
                               leave_count=leave_count,
                               att_dict_notes=att_dict_notes,
                               dates=dates,
                               students=students,
                               att_dict=att_dict,
                               selected_start=start_date_str,
                               selected_end=end_date_str,
                               selected_status=status_filter,
                               selected_apts=apt_filters,
                               selected_rooms=room_filters,
                               allow_date_change=allow_date)

    @app.route('/toggle_date_change', methods=['POST'])
    @login_required
    def toggle_date_change():
        if current_user.role != 'admin':
            return redirect(url_for('mandoob_dashboard'))
        
        current_status = get_setting('ALLOW_DATE_CHANGE', False)
        set_setting('ALLOW_DATE_CHANGE', not current_status)
        
        if not current_status:
            flash('تم السماح بتغيير التاريخ للمناديب بنجاح.', 'success')
        else:
            flash('تم إغلاق صلاحية تغيير التاريخ للمناديب.', 'error')
            
        return redirect(url_for('admin_dashboard'))

    # =========================================================================
    # 3. إدارة الطلاب (عرض وإضافة وتعديل)
    # =========================================================================
    def get_filtered_students(filter_type):
        query = Student.query
        if filter_type == 'مفصول':
            return query.filter_by(status='مفصول').order_by(Student.apartment_number, Student.room_number).limit(500).all()
        elif filter_type == 'تخرج':
            return query.filter_by(status='تخرج').order_by(Student.apartment_number, Student.room_number).limit(500).all()
        elif filter_type == 'في إجازة': 
            return query.filter_by(status='في إجازة').order_by(Student.apartment_number, Student.room_number).limit(500).all()
        elif filter_type == 'all':
            return query.order_by(Student.apartment_number, Student.room_number).limit(500).all()
        else:
            return query.filter(Student.status.in_(['فعال', 'نشط', 'موجود'])).order_by(Student.apartment_number, Student.room_number).limit(500).all()

    @app.route('/students', methods=['GET', 'POST'])
    @login_required
    def manage_students():
        if current_user.role != 'admin':
            return redirect(url_for('mandoob_dashboard'))
       
        if request.method == 'POST':
            new_student = Student(
                full_name=request.form.get('full_name').strip(),
                apartment_number=int(request.form.get('apartment_number')),
                room_number=int(request.form.get('room_number')),
                status='فعال'
            )
            db.session.add(new_student)
            db.session.commit()
            flash('تم إضافة الطالب بنجاح!', 'success')
            return redirect(url_for('manage_students'))

        view_filter = request.args.get('view', 'active')
        filtered_students = get_filtered_students(view_filter)
        
        return render_template('students.html', 
                               current_user=current_user, 
                               students=filtered_students,
                               current_view=view_filter)

    @app.route('/edit_student/<int:student_id>', methods=['POST'])
    @login_required
    def edit_student(student_id):
        if current_user.role != 'admin':
            return redirect(url_for('mandoob_dashboard'))
        
        student = Student.query.get_or_404(student_id)
        new_status = request.form.get('status')

        student.full_name = request.form.get('full_name').strip()
        student.apartment_number = int(request.form.get('apartment_number'))
        student.room_number = int(request.form.get('room_number'))
        student.status = new_status

        if new_status in ['مفصول', 'تخرج']:
            user = User.query.filter_by(student_id=student.id).first()
            if user:
                user.is_active = False

        db.session.commit()
        flash('تم تحديث بيانات الطالب بنجاح!', 'success')
        return redirect(url_for('manage_students'))

    # =========================================================================
    # 4. إدارة الشقق
    # =========================================================================
    @app.route('/apartments')
    @login_required
    def manage_apartments():
        if current_user.role != 'admin':
            return redirect(url_for('mandoob_dashboard'))
       
        students = Student.query.filter(Student.status.in_(['فعال', 'نشط', 'موجود', 'في إجازة'])).order_by(Student.apartment_number, Student.room_number).all()
        apartments_data = {i: {'count': 0, 'mandoob': None} for i in range(2, 13)}
        
        for student in students:
            apt = student.apartment_number
            if apt in apartments_data:
                apartments_data[apt]['count'] += 1
                if student.user and student.user.role == 'mandoob' and student.user.is_active:
                    apartments_data[apt]['mandoob'] = student
                        
        return render_template('apartments.html', apartments=apartments_data)

    @app.route('/apartment/<int:apt_num>')
    @login_required
    def view_apartment(apt_num):
        if current_user.role != 'admin':
            return redirect(url_for('mandoob_dashboard'))
       
        students = Student.query.filter(
            Student.apartment_number == apt_num,
            Student.status.in_(['فعال', 'نشط', 'موجود', 'في إجازة'])
        ).order_by(Student.room_number).all()
        
        mandoob = None
        for student in students:
            if student.user and student.user.role == 'mandoob' and student.user.is_active:
                mandoob = student
                break
                    
        return render_template('apartment_details.html', apt_num=apt_num, students=students, mandoob=mandoob)

    # =========================================================================
    # 5. إدارة المناديب (تفعيل، تعطيل، وتعيين)
    # =========================================================================
    @app.route('/mandoobs')
    @login_required
    def manage_mandoobs():
        if current_user.role != 'admin':
            return redirect(url_for('mandoob_dashboard'))        
        
        all_mandoobs = User.query.filter_by(role='mandoob').join(Student).filter(
            Student.status.in_(['فعال', 'نشط', 'موجود', 'في إجازة'])
        ).order_by(Student.apartment_number, Student.room_number).all()
        
        return render_template('mandoob_management.html', mandoobs=all_mandoobs)

    @app.route('/toggle_mandoob/<int:user_id>')
    @login_required
    def toggle_mandoob(user_id):
        if current_user.role != 'admin':
            return redirect(url_for('mandoob_dashboard'))        
        
        user = User.query.get_or_404(user_id)
        
        if not user.is_active:
            student = user.student
            if student:
                apt_students = Student.query.filter(
                    Student.apartment_number == student.apartment_number,
                    Student.status.in_(['فعال', 'نشط', 'موجود', 'في إجازة'])
                ).all()
                for s in apt_students:
                    if s.user and s.id != student.id:
                        if s.user.role == 'mandoob' and s.user.is_active:
                            flash(f'لا يمكن تفعيل المندوب لأن شقة {student.apartment_number} لديها مندوب نشط!', 'error')
                            return redirect(url_for('manage_mandoobs'))

        user.is_active = not user.is_active
        db.session.commit()
        
        status_text = "تفعيل" if user.is_active else "تعطيل"
        flash(f'تم {status_text} حساب {user.name} بنجاح.', 'success')
        return redirect(url_for('manage_mandoobs'))

    @app.route('/assign_mandoob/<int:student_id>', methods=['POST'])
    @login_required
    def assign_mandoob(student_id):
        if current_user.role != 'admin':
            return redirect(url_for('mandoob_dashboard'))
            
        target = request.referrer
        if not target or not is_safe_url(target):
            target = url_for('manage_apartments')

        student = Student.query.get_or_404(student_id)
        apt_num = student.apartment_number

        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        if not username or not password:
            flash('يرجى إدخال اسم المستخدم وكلمة المرور!', 'error')
            return redirect(target)

        existing_username = User.query.filter_by(username=username).first()

        existing_mandoob = User.query.join(Student).filter(
            Student.apartment_number == apt_num,
            User.role == 'mandoob',
            User.is_active == True
        ).first()

        if existing_mandoob and existing_mandoob.student_id != student.id:
            flash(f'عذراً! الشقة {apt_num} لديها مندوب نشط حالياً.', 'error')
            return redirect(target)

        user = User.query.filter_by(student_id=student.id).first()
        
        try:
            if user:
                if existing_username and existing_username.id != user.id:
                    flash('اسم المستخدم محجوز مسبقاً.', 'error')
                    return redirect(target)
                    
                user.is_active = True
                user.role = 'mandoob'
                user.username = username
                user.password = generate_password_hash(password, method='pbkdf2:sha256')
                db.session.commit()
                flash(f'تم تفعيل وتحديث حساب المندوب بنجاح.', 'success')
            else:
                if existing_username:
                    flash('اسم المستخدم محجوز مسبقاً.', 'error')
                    return redirect(target)
                    
                new_user = User(
                    username=username,
                    password=generate_password_hash(password, method='pbkdf2:sha256'),
                    role='mandoob',
                    student_id=student.id,
                    is_active=True
                )
                db.session.add(new_user)
                db.session.commit()
                flash(f'تم تعيين المندوب بنجاح.', 'success')
                
        except IntegrityError:
            db.session.rollback()
            flash('حدث خطأ في قاعدة البيانات، قد يكون اسم المستخدم محجوزاً.', 'error')

        return redirect(target)
    
    @app.route('/reset_password/<int:user_id>', methods=['POST'])
    @login_required
    def reset_password(user_id):
        if current_user.role not in ['admin', 'developer']:
            return "غير مصرح", 403
            
        user = User.query.get_or_404(user_id)
        
        # حماية من ثغرة IDOR: منع الأدمن من تغيير كلمة مرور المطور
        if current_user.role == 'admin' and user.role == 'developer':
            flash('غير مصرح لك بتعديل حسابات المطورين.', 'error')
            return redirect(url_for('manage_mandoobs'))

        new_pw = request.form.get('new_password')
        if not new_pw or len(new_pw) < 6:
            flash('كلمة المرور يجب أن تكون 6 أحرف على الأقل.', 'error')
            return redirect(url_for('manage_mandoobs'))
            
        user.password = generate_password_hash(new_pw, method='pbkdf2:sha256')
        db.session.commit()
        
        flash(f'تم تغيير كلمة المرور بنجاح.', 'success')
        return redirect(url_for('manage_mandoobs'))

    @app.route('/revoke_mandoob/<int:student_id>', methods=['POST'])
    @login_required
    def revoke_mandoob(student_id):
        if current_user.role != 'admin':
            return "غير مصرح", 403
            
        target = request.referrer
        if not target or not is_safe_url(target):
            target = url_for('manage_apartments')
            
        user = User.query.filter_by(student_id=student_id, role='mandoob').first()
        if user:
            user.is_active = False 
            db.session.commit()
            flash('تم سحب صلاحية المندوب وتعطيل الحساب بنجاح.', 'success')
        else:
            flash('هذا الطالب ليس لديه حساب مندوب أصلاً.', 'info')
            
        return redirect(target)

    # =========================================================================
    # 6. لوحة المندوب (واجهة التحضير)
    # =========================================================================
    @app.route('/mandoob')
    @login_required
    def mandoob_dashboard():
        if current_user.role == 'developer':
            return redirect(url_for('manage_admins'))
        if current_user.role == 'admin':
            return redirect(url_for('admin_dashboard'))

        if current_user.role != 'mandoob':
            return redirect(url_for('login'))
        
        mandoob_student = current_user.student
        if not mandoob_student:
            return "حسابك غير مرتبط بأي شقة حالياً.", 400
            
        apt_num = mandoob_student.apartment_number
        students = Student.query.filter(
            Student.apartment_number == apt_num,
            Student.status.in_(['فعال', 'نشط', 'موجود', 'في إجازة'])
        ).order_by(Student.room_number).all()
        
        today = date.today()
        existing_records = Attendance.query.filter_by(recorded_by=current_user.id, date=today).all()
        att_dict = {r.student_id: r.status for r in existing_records}
        
        already_recorded = len(existing_records) > 0
        allow_date = get_setting('ALLOW_DATE_CHANGE', False)
        
        return render_template('mandoob.html', 
                               students=students, 
                               apt_num=apt_num, 
                               already_recorded=already_recorded,
                               att_dict=att_dict,
                               today=today,
                               allow_date_change=allow_date)

    @app.route('/submit_attendance', methods=['POST'])
    @login_required
    def submit_attendance():
        if current_user.role != 'mandoob':
            return redirect(url_for('login'))
            
        from datetime import datetime
        record_date_str = request.form.get('record_date')
        record_date = datetime.strptime(record_date_str, '%Y-%m-%d').date() if record_date_str else date.today()
        
        # حماية IDOR: جلب معرفات الطلاب المسموح للمندوب بالتحضير لهم فقط
        mandoob_apt = current_user.student.apartment_number
        allowed_student_ids = {s.id for s in Student.query.filter_by(apartment_number=mandoob_apt).all()}
        VALID_STATUSES = {'حاضر', 'غائب', 'مستأذن', 'مأجز'}
        
        submitted_data = {}
        
        for key, value in request.form.items():
            if key.startswith('student_'):
                try:
                    student_id = int(key.split('_')[1])
                except ValueError:
                    continue
                
                status_value = value.strip()
                
                # التحقق الصارم (Mass Assignment و IDOR)
                if status_value not in VALID_STATUSES or student_id not in allowed_student_ids:
                    continue
                    
                note_value = request.form.get(f'note_{student_id}', '').strip()[:255]
                submitted_data[student_id] = {'status': status_value, 'note': note_value}
        
        if not submitted_data:
            return redirect(url_for('mandoob_dashboard'))

        # إصلاح استنزاف الموارد N+1: جلب السجلات الموجودة في استعلام واحد
        existing_records = Attendance.query.filter(
            Attendance.student_id.in_(submitted_data.keys()),
            Attendance.date == record_date
        ).all()
        
        record_dict = {r.student_id: r for r in existing_records}
        
        # التحديث والإضافة المجمعة
        for s_id, data in submitted_data.items():
            if s_id in record_dict:
                record_dict[s_id].status = data['status']
                record_dict[s_id].note = data['note']
                record_dict[s_id].recorded_by = current_user.id
            else:
                new_record = Attendance(
                    student_id=s_id, date=record_date, 
                    status=data['status'], note=data['note'], 
                    recorded_by=current_user.id
                )
                db.session.add(new_record)

        db.session.commit()
        flash(f'تم حفظ كشف التحضير لتاريخ {record_date} بنجاح!', 'success')
        return redirect(url_for('mandoob_dashboard'))

    # =========================================================================
    # 7. منطقة المطور (Developer Area)
    # =========================================================================
    @app.route('/manage_admins')
    @login_required
    def manage_admins():
        if current_user.role != 'developer':
            return "غير مصرح لك بدخول هذه الصفحة.", 403
            
        admins = User.query.filter(User.role.in_(['admin', 'developer'])).all()
        return render_template('manage_admins.html', admins=admins)

    @app.route('/add_admin', methods=['POST'])
    @login_required
    def add_admin():
        if current_user.role != 'developer':
            return "غير مصرح", 403
            
        username = request.form.get('username').strip()
        password = request.form.get('password')
        role = request.form.get('role') 
        
        if User.query.filter_by(username=username).first():
            flash('اسم المستخدم موجود مسبقاً!', 'error')
        else:
            try:
                new_admin = User(
                    username=username,
                    password=generate_password_hash(password, method='pbkdf2:sha256'),
                    role=role,
                    is_active=True
                )
                db.session.add(new_admin)
                db.session.commit()
                flash('تم إضافة الحساب بنجاح.', 'success')
            except IntegrityError:
                db.session.rollback()
                flash('اسم المستخدم محجوز، يرجى المحاولة مرة أخرى.', 'error')
            
        return redirect(url_for('manage_admins'))

    @app.route('/edit_admin/<int:admin_id>', methods=['POST'])
    @login_required
    def edit_admin(admin_id):
        if current_user.role != 'developer':
            return "غير مصرح", 403
            
        admin = User.query.get_or_404(admin_id)
        new_username = request.form.get('username').strip()
        
        existing_user = User.query.filter(User.username == new_username, User.id != admin_id).first()
        if existing_user:
            flash('اسم المستخدم محجوز لحساب آخر! يرجى اختيار اسم مختلف.', 'error')
            return redirect(url_for('manage_admins'))
            
        admin.username = new_username
        admin.role = request.form.get('role') 
        
        new_password = request.form.get('password')
        if new_password and len(new_password) >= 6:
            admin.password = generate_password_hash(new_password, method='pbkdf2:sha256')
            
        try:
            db.session.commit()
            flash('تم تحديث بيانات الحساب بنجاح.', 'success')
        except IntegrityError:
            db.session.rollback()
            flash('حدث خطأ في قاعدة البيانات أثناء التحديث.', 'error')
            
        return redirect(url_for('manage_admins'))

    @app.route('/delete_admin/<int:admin_id>', methods=['POST'])
    @login_required
    def delete_admin(admin_id):
        if current_user.role != 'developer':
            return "غير مصرح", 403
            
        if current_user.id == admin_id:
            flash('لا يمكنك حذف حسابك الشخصي الذي تستخدمه الآن!', 'error')
            return redirect(url_for('manage_admins'))
            
        admin = User.query.get_or_404(admin_id)
        db.session.delete(admin)
        db.session.commit()
        
        flash('تم حذف الحساب نهائياً.', 'success')
        return redirect(url_for('manage_admins'))