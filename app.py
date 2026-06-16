from flask import Flask, redirect, url_for
from flask_login import LoginManager, current_user
from werkzeug.security import generate_password_hash
# تأكد من استدعاء جميع الجداول هنا
from models import db, User, Student, Attendance, PushSubscription
from routes import register_routes
from flask_admin import Admin, AdminIndexView
from flask_admin.contrib.sqla import ModelView
import os

# تحديد المسار الدقيق للمشروع على جهازك
app = Flask(__name__)

# إعدادات Web Push Notifications
app.config['VAPID_PUBLIC_KEY'] =  'BGKcO7m8HS9JfRP7S6I3aKEm-Zzu8optzsN_C8IzXv2e35OxzsvlL46Ya2oZGDVx1YSQgjS51QOSyH6Vlmo9Vrs'
app.config['VAPID_PRIVATE_KEY'] = 'gKtVzn7uAF25e1PqW4pna2l4CEEfWOnZX5MH1jyGo0M'
app.config['VAPID_CLAIM_EMAIL'] = 'mailto:ga@gmail.com' 

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'instance', 'dormitory.db')
app.config['SECRET_KEY'] = 'super_secret_key_123'

# 1. ربط قاعدة البيانات بالتطبيق
db.init_app(app)

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
admin_panel.add_view(DeveloperModelView(User, db.session))
admin_panel.add_view(DeveloperModelView(Student, db.session))
admin_panel.add_view(DeveloperModelView(Attendance, db.session))
admin_panel.add_view(DeveloperModelView(PushSubscription, db.session))

# 3. تسجيل المسارات (الروابط) من ملف routes.py
register_routes(app)

# 4. بناء الجداول 
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=False)