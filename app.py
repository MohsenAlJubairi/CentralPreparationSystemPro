from flask import Flask
from flask_login import LoginManager
from werkzeug.security import generate_password_hash
from models import db, User
from routes import register_routes

# تحديد المسار الدقيق للمشروع على جهازك
app = Flask(__name__)
import os
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

# 3. تسجيل المسارات (الروابط) من ملف routes.py
register_routes(app)

# 4. بناء الجداول وإنشاء مدير افتراضي
with app.app_context():
    #db.drop_all()  # فك التعليق عن هذا السطر لمرة واحدة فقط لمسح الجداول القديمة
    db.create_all()
    if not User.query.filter_by(username='admin').first():
        hashed_password = generate_password_hash('admin123', method='pbkdf2:sha256')
        new_admin = User(username='admin', password=hashed_password, role='admin')
        db.session.add(new_admin)
        db.session.commit()
        print("✅ تم إنشاء حساب مدير افتراضي بنجاح!")

if __name__ == '__main__':
    app.run(debug=True)

# إعدادات Web Push Notifications
app.config['VAPID_PUBLIC_KEY'] =  'BGKcO7m8HS9JfRP7S6I3aKEm-Zzu8optzsN_C8IzXv2e35OxzsvlL46Ya2oZGDVx1YSQgjS51QOSyH6Vlmo9Vrs'
app.config['VAPID_PRIVATE_KEY'] = 'gKtVzn7uAF25e1PqW4pna2l4CEEfWOnZX5MH1jyGo0M'
app.config['VAPID_CLAIM_EMAIL'] = 'ga@gmail.com' # بريد وهمي أو حقيقي للإدارة