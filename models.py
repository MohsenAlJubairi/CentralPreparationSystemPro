from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False) # 'admin' or 'mandoob'
    is_active = db.Column(db.Boolean, default=True)
    
    # استبدال العمود name بـ student_id
    # nullable=True يسمح بأن يكون القيمة NULL إذا كان المستخدم 'admin'
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=True)
    
    # علاقة لجلب بيانات الطالب بسهولة من كائن المستخدم
    student = db.relationship('Student', backref=db.backref('user', uselist=False), foreign_keys=[student_id])

    # ملاحظة ذكية: بما أننا حذفنا حقل name، سنقوم بعمل دالة ترجع الاسم ديناميكياً
    # لكي لا تضطر لتعديل كل الملفات التي تستخدم current_user.name
    @property
    def name(self):
        if self.role == 'admin':
            return "مدير النظام"
        return self.student.full_name if self.student else self.username

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    apartment_number = db.Column(db.Integer, nullable=False)
    room_number = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default='فعال')
    
    # ملاحظة: يمكنك الإبقاء على user_id هنا أو حذفه، 
    # لكن التعديل الجديد في User.student_id هو الذي سيتحكم في الربط الآن.

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    date = db.Column(db.Date, default=datetime.utcnow)
    status = db.Column(db.String(20), nullable=False)
    recorded_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    note = db.Column(db.String(255), nullable=True) # إضافة هذا السطر