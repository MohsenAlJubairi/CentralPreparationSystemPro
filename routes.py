from flask import render_template, request, redirect, url_for, flash
from flask_login import login_user, login_required, logout_user, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from models import db, User, Student, Attendance
from datetime import date, datetime
from io import BytesIO
import pandas as pd

def register_routes(app):

    if 'ALLOW_DATE_CHANGE' not in app.config:
        app.config['ALLOW_DATE_CHANGE'] = False

    # =========================================================================
    # 1. مسارات المصادقة (تسجيل الدخول والخروج)
    # =========================================================================
    @app.route('/')
    def home():
        return redirect(url_for('login'))


    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if current_user.is_authenticated:
            if current_user.role == 'admin': 
                return redirect(url_for('admin_dashboard'))
            else: 
                return redirect(url_for('mandoob_dashboard'))

        if current_user.is_authenticated:
            if current_user.role == 'developer':
                return redirect(url_for('manage_admins')) # توجيه المطور
            elif current_user.role == 'admin':
                return redirect(url_for('admin_dashboard')) # توجيه الأدمن
            else:
                return redirect(url_for('mandoob_dashboard')) # توجيه المندوب

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
                
                if user.role == 'admin': 
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

        if not file:
            flash('الرجاء اختيار ملف إكسل أولاً', 'error')
            return redirect(url_for('manage_students'))

        try:
            df = pd.read_excel(BytesIO(file.read()))
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
                flash('تم أرشفة العام السابق: تحويل الطلاب إلى "مفصول" وتعطيل المناديب القدامى.', 'info')

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

                new_student = Student(
                    full_name=f_name,
                    apartment_number=apt_val,
                    room_number=room_val,
                    status='فعال'
                )
                db.session.add(new_student)
                added_count += 1

            if added_count > 0:
                db.session.commit()
                flash(f'تم استيراد {added_count} طالب بنجاح! (يرجى تعيين المناديب يدوياً من صفحة الشقق)', 'success')
            else:
                db.session.rollback()
                flash('لم يتم استيراد أي طالب! تأكد من أن الملف يحتوي على بيانات صحيحة تحت الأعمدة المحددة.', 'error')

        except Exception as e:
            db.session.rollback()
            flash(f'حدث خطأ أثناء قراءة الملف: {e}', 'error')

        return redirect(url_for('manage_students'))

    # =========================================================================
    # 2. لوحة تحكم الإدارة (الرئيسية والإحصائيات)
    # =========================================================================
    @app.route('/admin')
    @login_required
    def admin_dashboard():
        # إضافة هذا السطر لكسر الحلقة
        if current_user.role == 'developer':
            return redirect(url_for('manage_admins'))


        if current_user.role != 'admin':
            flash('تحذير أمني: محاولة وصول غير مصرح بها لمنطقة إدارية!', 'error')
            return redirect(url_for('mandoob_dashboard'))
            
        today = date.today()
        
        total_students = Student.query.filter(Student.status.in_(['فعال', 'نشط', 'موجود', 'في إجازة'])).count()
        present_count = Attendance.query.filter_by(date=today, status='حاضر').count()
        absent_count = Attendance.query.filter_by(date=today, status='غائب').count()
        excused_count = Attendance.query.filter_by(date=today, status='مستأذن').count()
        leave_count = Student.query.filter_by(status='في إجازة').count()
        
        from datetime import datetime
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
            
        students = student_query.order_by(Student.apartment_number, Student.room_number).all()
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
                att_dict_notes[r.student_id] = {} # تجهيز مفتاح الطالب

            att_dict[r.student_id][r.date] = r.status
            att_dict_notes[r.student_id][r.date] = r.note # 👈 تخزين الملاحظة

        if status_filter != 'all':
            filtered_students = []
            for s in students:
                has_status = any(att_dict.get(s.id, {}).get(d) == status_filter for d in dates)
                if has_status:
                    filtered_students.append(s)
            students = filtered_students

        return render_template('admin.html', 
                               current_user=current_user,
                               total_students=total_students,
                               present_count=present_count,
                               absent_count=absent_count,
                               excused_count=excused_count,
                               leave_count=leave_count,
                               att_dict_notes=att_dict_notes, # 👈 تمرير القاموس للواجهة
                               dates=dates,
                               students=students,
                               att_dict=att_dict,
                               selected_start=start_date_str,
                               selected_end=end_date_str,
                               selected_status=status_filter,
                               selected_apts=apt_filters,
                               selected_rooms=room_filters,
                               allow_date_change=app.config.get('ALLOW_DATE_CHANGE', False))

    @app.route('/toggle_date_change', methods=['POST'])
    @login_required
    def toggle_date_change():
        if current_user.role != 'admin':
            return redirect(url_for('mandoob_dashboard'))
        
        current_status = app.config.get('ALLOW_DATE_CHANGE', False)
        app.config['ALLOW_DATE_CHANGE'] = not current_status
        
        if app.config['ALLOW_DATE_CHANGE']:
            flash('تم السماح بتغيير التاريخ للمناديب بنجاح.', 'success')
        else:
            flash('تم إغلاق صلاحية تغيير التاريخ للمناديب.', 'error')
            
        return redirect(url_for('admin_dashboard'))

    # =========================================================================
    # 3. إدارة الطلاب (عرض وإضافة وتعديل)
    # =========================================================================
    
    def get_filtered_students(filter_type):
        """دالة خاصة لجلب الطلاب من الداتابيس بناءً على الفلتر لتوفير أداء السيرفر"""
        query = Student.query
        if filter_type == 'مفصول':
            return query.filter_by(status='مفصول').order_by(Student.apartment_number, Student.room_number).all()
        elif filter_type == 'تخرج':
            return query.filter_by(status='تخرج').order_by(Student.apartment_number, Student.room_number).all()
        elif filter_type == 'في إجازة': # <-- تم إضافة هذا الشرط المفقود
            return query.filter_by(status='في إجازة').order_by(Student.apartment_number, Student.room_number).all()
        elif filter_type == 'all':
            return query.order_by(Student.apartment_number, Student.room_number).all()
        else:
            # الافتراضي (active): الفعالون فقط (بدون المجازين)
            return query.filter(Student.status.in_(['فعال', 'نشط', 'موجود'])).order_by(Student.apartment_number, Student.room_number).all()



    @app.route('/students', methods=['GET', 'POST'])
    @login_required
    def manage_students():
        if current_user.role != 'admin':
            flash('تحذير أمني: محاولة وصول غير مصرح بها لمنطقة إدارية!', 'error')
            return redirect(url_for('mandoob_dashboard'))
       
        if request.method == 'POST':
            new_student = Student(
                full_name=request.form.get('full_name'),
                apartment_number=int(request.form.get('apartment_number')),
                room_number=int(request.form.get('room_number')),
                status='فعال'
            )
            db.session.add(new_student)
            db.session.commit()
            flash('تم إضافة الطالب بنجاح!', 'success')
            return redirect(url_for('manage_students'))

        # قراءة الفلتر من الرابط، وإذا كان فارغاً يتم تطبيق الفلتر الافتراضي (active)
        # قراءة الفلتر من الرابط
        view_filter = request.args.get('view', 'active')
        print("====== الفلتر الحالي هو: ======", view_filter) # أضف هذا السطر
        filtered_students = get_filtered_students(view_filter)
        
        # أضفنا current_view لكي نرسله للواجهة
        return render_template('students.html', 
                               current_user=current_user, 
                               students=filtered_students,
                               current_view=view_filter)

    @app.route('/edit_student/<int:student_id>', methods=['POST'])
    @login_required
    def edit_student(student_id):
        if current_user.role != 'admin':
            flash('تحذير أمني: محاولة وصول غير مصرح بها لمنطقة إدارية!', 'error')
            return redirect(url_for('mandoob_dashboard'))
        
        student = Student.query.get_or_404(student_id)
        old_status = student.status
        new_status = request.form.get('status')

        student.full_name = request.form.get('full_name')
        student.apartment_number = int(request.form.get('apartment_number'))
        student.room_number = int(request.form.get('room_number'))
        student.status = new_status

        # المنطق الذكي: إذا تم فصل الطالب أو تخرجه، نعطل حسابه كمندوب فوراً
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
            flash('تحذير أمني: محاولة وصول غير مصرح بها لمنطقة إدارية!', 'error')
            return redirect(url_for('mandoob_dashboard'))
       
        # فلترة في الداتابيس لاستبعاد المفصولين
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
            flash('تحذير أمني: محاولة وصول غير مصرح بها لمنطقة إدارية!', 'error')
            return redirect(url_for('mandoob_dashboard'))
       
        # فلترة في الداتابيس للطلاب الفعالين في هذه الشقة فقط
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
            flash('تحذير أمني: محاولة وصول غير مصرح بها لمنطقة إدارية!', 'error')
            return redirect(url_for('mandoob_dashboard'))        
        
        # التأكد من جلب المناديب المرتبطين بطلاب فعالين فقط (فلترة عبر join)
        all_mandoobs = User.query.filter_by(role='mandoob').join(Student).filter(
            Student.status.in_(['فعال', 'نشط', 'موجود', 'في إجازة'])
        ).order_by(Student.apartment_number, Student.room_number).all()
        
        return render_template('mandoob_management.html', mandoobs=all_mandoobs)

    @app.route('/toggle_mandoob/<int:user_id>')
    @login_required
    def toggle_mandoob(user_id):
        if current_user.role != 'admin':
            flash('تحذير أمني: محاولة وصول غير مصرح بها لمنطقة إدارية!', 'error')
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
                            flash(f'لا يمكن تفعيل المندوب ({user.name}) لأن شقة {student.apartment_number} لديها مندوب نشط حالياً!', 'error')
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
            flash('غير مصرح لك بهذا الإجراء.', 'error')
            return redirect(url_for('mandoob_dashboard'))

        student = Student.query.get_or_404(student_id)
        apt_num = student.apartment_number

        # 1. استلام اسم المستخدم وكلمة المرور من الفورم (Text boxes) الخاص بك
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        if not username or not password:
            flash('يرجى إدخال اسم المستخدم وكلمة المرور!', 'error')
            return redirect(request.referrer or url_for('manage_apartments'))

        # 2. التحقق من أن اسم المستخدم غير مستخدم من قبل طالب آخر
        existing_username = User.query.filter_by(username=username).first()

        # 3. التأكد من عدم وجود مندوب نشط لنفس الشقة
        existing_mandoob = User.query.join(Student).filter(
            Student.apartment_number == apt_num,
            User.role == 'mandoob',
            User.is_active == True
        ).first()

        if existing_mandoob and existing_mandoob.student_id != student.id:
            flash(f'عذراً! الشقة {apt_num} لديها مندوب نشط حالياً.', 'error')
            return redirect(request.referrer or url_for('manage_apartments'))

        # 4. التحقق إذا كان الطالب لديه حساب سابق
        user = User.query.filter_by(student_id=student.id).first()
        
        if user:
            # التحقق إذا كان اسم المستخدم الجديد محجوز لغيره
            if existing_username and existing_username.id != user.id:
                flash('اسم المستخدم هذا محجوز مسبقاً، يرجى اختيار اسم آخر.', 'error')
                return redirect(request.referrer or url_for('manage_apartments'))
                
            # تحديث الحساب القديم بالبيانات الجديدة
            user.is_active = True
            user.role = 'mandoob'
            user.username = username
            user.password = generate_password_hash(password, method='pbkdf2:sha256')
            db.session.commit()
            flash(f'تم تفعيل وتحديث حساب {student.full_name} بنجاح.', 'success')
        else:
            if existing_username:
                flash('اسم المستخدم هذا محجوز مسبقاً، يرجى اختيار اسم آخر.', 'error')
                return redirect(request.referrer or url_for('manage_apartments'))
                
            # إنشاء حساب مندوب جديد تماماً بالبيانات المدخلة
            new_user = User(
                username=username,
                password=generate_password_hash(password, method='pbkdf2:sha256'),
                role='mandoob',
                student_id=student.id,
                is_active=True
            )
            db.session.add(new_user)
            db.session.commit()
            flash(f'تم تعيين {student.full_name} كمندوب بنجاح.', 'success')

        return redirect(request.referrer or url_for('manage_apartments'))
    
    @app.route('/reset_password/<int:user_id>', methods=['POST'])
    @login_required
    def reset_password(user_id):
        if current_user.role != 'admin':
            return "غير مصرح", 403
            
        new_pw = request.form.get('new_password')
        if not new_pw or len(new_pw) < 6:
            flash('كلمة المرور يجب أن تكون 6 أحرف على الأقل.', 'error')
            return redirect(url_for('manage_mandoobs'))
            
        user = User.query.get_or_404(user_id)
        user.password = generate_password_hash(new_pw, method='pbkdf2:sha256')
        db.session.commit()
        
        flash(f'تم تغيير كلمة مرور المندوب {user.name} بنجاح.', 'success')
        return redirect(url_for('manage_mandoobs'))

    @app.route('/revoke_mandoob/<int:student_id>', methods=['POST'])
    @login_required
    def revoke_mandoob(student_id):
        if current_user.role != 'admin':
            return "غير مصرح", 403
            
        user = User.query.filter_by(student_id=student_id, role='mandoob').first()
        if user:
            user.is_active = False # تعطيل الحساب بدلاً من حذفه لضمان عدم ضياع السجلات
            db.session.commit()
            flash('تم سحب صلاحية المندوب وتعطيل الحساب بنجاح.', 'success')
        else:
            flash('هذا الطالب ليس لديه حساب مندوب أصلاً.', 'info')
            
        return redirect(request.referrer or url_for('manage_apartments'))

    # =========================================================================
    # 6. لوحة المندوب (واجهة التحضير للجوال)
    # =========================================================================
    @app.route('/mandoob')
    @login_required
    def mandoob_dashboard():
        if current_user.role == 'developer':
            return redirect(url_for('manage_admins'))
            
        if current_user.role == 'admin':
            return redirect(url_for('admin_dashboard'))

        if current_user.role != 'mandoob':
            flash('تحذير أمني: هذه الصفحة مخصصة للمناديب فقط!', 'error')
            return redirect(url_for('admin_dashboard'))
        
        mandoob_student = current_user.student
        if not mandoob_student:
            return "حسابك غير مرتبط بأي شقة حالياً. راجع الإدارة.", 400
            
        apt_num = mandoob_student.apartment_number
        students = Student.query.filter(
            Student.apartment_number == apt_num,
            Student.status.in_(['فعال', 'نشط', 'موجود', 'في إجازة'])
        ).order_by(Student.room_number).all()
        
        today = date.today()
        existing_records = Attendance.query.filter_by(recorded_by=current_user.id, date=today).all()
        att_dict = {r.student_id: r.status for r in existing_records}
        
        already_recorded = len(existing_records) > 0
        
        return render_template('mandoob.html', 
                               students=students, 
                               apt_num=apt_num, 
                               already_recorded=already_recorded,
                               att_dict=att_dict,
                               today=today,
                               allow_date_change=app.config.get('ALLOW_DATE_CHANGE', False))

    @app.route('/submit_attendance', methods=['POST'])
    @login_required
    def submit_attendance():
        if current_user.role != 'mandoob':
            return redirect(url_for('admin_dashboard'))
            
        from datetime import datetime
        record_date_str = request.form.get('record_date')
        record_date = datetime.strptime(record_date_str, '%Y-%m-%d').date() if record_date_str else date.today()
            
        for key, value in request.form.items():
            if key.startswith('student_'):
                student_id = int(key.split('_')[1])
                status_value = value
                # جلب الملاحظة المرتبطة بهذا الطالب
                note_value = request.form.get(f'note_{student_id}', '').strip()
                
                existing_record = Attendance.query.filter_by(student_id=student_id, date=record_date).first()
                
                if existing_record:
                    existing_record.status = status_value
                    existing_record.note = note_value # تحديث الملاحظة
                    existing_record.recorded_by = current_user.id
                else:
                    new_record = Attendance(student_id=student_id, date=record_date, 
                                            status=status_value, note=note_value, # حفظ الملاحظة
                                            recorded_by=current_user.id)
                    db.session.add(new_record)


        db.session.commit()
        flash(f'تم حفظ كشف التحضير لتاريخ {record_date} بنجاح!', 'success')
        return redirect(url_for('mandoob_dashboard'))





        # -------------------------------------------------------------------------
    # منطقة المطور (Developer Area)
    # -------------------------------------------------------------------------
    @app.route('/manage_admins')
    @login_required
    def manage_admins():
        if current_user.role != 'developer':
            return "غير مصرح لك بدخول هذه الصفحة.", 403
            
        # جلب كل حسابات الإدارة والمطورين لعرضها
        admins = User.query.filter(User.role.in_(['admin', 'developer'])).all()
        return render_template('manage_admins.html', admins=admins)

    @app.route('/add_admin', methods=['POST'])
    @login_required
    def add_admin():
        if current_user.role != 'developer':
            return "غير مصرح", 403
            
        username = request.form.get('username')
        password = request.form.get('password')
        role = request.form.get('role') # قراءة الصلاحية (admin أو developer)
        
        if User.query.filter_by(username=username).first():
            flash('اسم المستخدم موجود مسبقاً!', 'error')
        else:
            new_admin = User(
                username=username,
                password=generate_password_hash(password, method='pbkdf2:sha256'),
                role=role,
                is_active=True
            )
            db.session.add(new_admin)
            db.session.commit()
            flash('تم إضافة الحساب بنجاح.', 'success')
            
        return redirect(url_for('manage_admins'))

    @app.route('/edit_admin/<int:admin_id>', methods=['POST'])
    @login_required
    def edit_admin(admin_id):
        if current_user.role != 'developer':
            return "غير مصرح", 403
            
        admin = User.query.get_or_404(admin_id)
        new_username = request.form.get('username').strip()
        
        # التحقق من أن الاسم الجديد غير محجوز لشخص آخر
        existing_user = User.query.filter(User.username == new_username, User.id != admin_id).first()
        if existing_user:
            flash('اسم المستخدم هذا محجوز لحساب آخر! يرجى اختيار اسم مختلف.', 'error')
            return redirect(url_for('manage_admins'))
            
        admin.username = new_username
        admin.role = request.form.get('role') # تحديث الصلاحية
        
        new_password = request.form.get('password')
        if new_password and len(new_password) >= 6:
            admin.password = generate_password_hash(new_password, method='pbkdf2:sha256')
            
        db.session.commit()
        flash('تم تحديث بيانات الحساب بنجاح.', 'success')
        return redirect(url_for('manage_admins'))

    @app.route('/delete_admin/<int:admin_id>', methods=['POST'])
    @login_required
    def delete_admin(admin_id):
        if current_user.role != 'developer':
            return "غير مصرح", 403
            
        # منع المطور من حذف حسابه الشخصي عن طريق الخطأ
        if current_user.id == admin_id:
            flash('لا يمكنك حذف حسابك الشخصي الذي تستخدمه الآن!', 'error')
            return redirect(url_for('manage_admins'))
            
        admin = User.query.get_or_404(admin_id)
        db.session.delete(admin)
        db.session.commit()
        
        flash('تم حذف الحساب نهائياً.', 'success')
        return redirect(url_for('manage_admins'))