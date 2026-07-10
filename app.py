from flask import Flask, redirect, url_for
from flask_login import LoginManager, current_user
from werkzeug.security import generate_password_hash
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect
# تأكد من استدعاء جميع الجداول هنا
from models import db, User, Student, Attendance, PushSubscription
from routes import register_routes
from flask_admin import Admin, AdminIndexView
from flask_admin.contrib.sqla import ModelView
import os
from datetime import timedelta
from dotenv import load_dotenv

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# تحميل متغيرات البيئة من ملف .env في نفس مجلد app.py
load_dotenv(os.path.join(BASE_DIR, '.env'))

# تحديد المسار الدقيق للمشروع على جهازك
app = Flask(__name__)

# إعدادات Web Push Notifications
app.config['VAPID_PUBLIC_KEY'] = os.environ.get('VAPID_PUBLIC_KEY', '')
app.config['VAPID_PRIVATE_KEY'] = os.environ.get('VAPID_PRIVATE_KEY', '')
app.config['VAPID_CLAIM_EMAIL'] = os.environ.get('VAPID_CLAIM_EMAIL', '') 

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'instance', 'dormitory.db')

# === إعدادات الأمان ===
_secret_key = os.environ.get('SECRET_KEY', '')
if not _secret_key or _secret_key == 'default_secret_fallback':
    import secrets
    _secret_key = secrets.token_hex(32)
    print("[تحذير أمني] SECRET_KEY غير مُعيَّن في ملف .env! تم توليد مفتاح مؤقت - يرجى تعيين SECRET_KEY في .env لضمان الثبات.")
app.config['SECRET_KEY'] = _secret_key

# أمان الجلسة (Session Security)
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=12)
app.config['SESSION_COOKIE_HTTPONLY'] = True   # يمنع JS من قراءة الكوكيز
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # حماية من CSRF عبر المتصفح
app.config['WTF_CSRF_TIME_LIMIT'] = 3600       # صلاحية توكن CSRF ساعة واحدة

# 1. ربط قاعدة البيانات بالتطبيق
db.init_app(app)

# === تهيئة نظامَي الأمان ===
# حماية CSRF (تطلب توكن سري في كل طلب POST)
csrf = CSRFProtect(app)

# تحديد معدل الطلبات (Rate Limiter) - الدفاع ضد Brute Force
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[],        # لا حد افتراضي - يُطبَّق بشكل انتقائي على المسارات الحساسة فقط
    storage_uri="memory://"   # تخزين في الذاكرة (مناسب لـ PythonAnywhere)
)

# 2. إعدادات تسجيل الدخول
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = "الرجاء تسجيل الدخول أولاً."

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ==========================================
# تعريف فئات الحماية أولاً (يجب أن تكون قبل التهيئة)
# ==========================================
class DeveloperModelView(ModelView):
    def is_accessible(self):
        return current_user.is_authenticated and current_user.role == 'developer'

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('login'))

class DeveloperAdminIndexView(AdminIndexView):
    def is_accessible(self):
        return current_user.is_authenticated and current_user.role == 'developer'

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('login'))

# ==========================================
# تهيئة لوحة التحكم بعد تعريف الفئات
# ==========================================
admin_panel = Admin(
    app, 
    name='لوحة تحكم قواعد البيانات', 
    url='/dev_admin',
    index_view=DeveloperAdminIndexView(url='/dev_admin')
)

# ربط جداول النظام باللوحة
admin_panel.add_view(DeveloperModelView(User, db))
admin_panel.add_view(DeveloperModelView(Student, db))
admin_panel.add_view(DeveloperModelView(Attendance, db))
admin_panel.add_view(DeveloperModelView(PushSubscription, db))

# 3. تسجيل المسارات (الروابط) من ملف routes.py
# تمرير Limiter و CSRF للمسارات
register_routes(app, limiter, csrf)

# 4. بناء الجداول 
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=False)