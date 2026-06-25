from app import app, db
from models import User  # تأكد أن اسم ملف الموديلز صحيح لديك
from werkzeug.security import generate_password_hash

with app.app_context():
    print("⏳ جاري إنشاء حساب مطور للطوارئ...")
    
    UserName = 'dev'
    # سنستخدم اسم 'dev' بدلاً من 'admin' لتجنب أي تعارض مع النظام
    existing = User.query.filter_by(username=UserName).first()
    
    if not existing:
        hashed_password = generate_password_hash('123456', method='pbkdf2:sha256')
        
        # إنشاء حساب بصلاحية developer
        new_dev = User(
            # أزلنا حقل name لتجنب الخطأ السابق
            username=UserName,
            password=hashed_password,
            role='developer',
            is_active=True
        )
        
        db.session.add(new_dev)
        db.session.commit()
        
        print("✅ تمت العملية بنجاح!")
        print("-------------------------------")
        print(f"👤 اسم المستخدم: {UserName}")
        print("🔑 كلمة المرور: 123456")
        print("-------------------------------")
    else:
        # إذا كان الحساب موجوداً مسبقاً، سنقوم بتحديث صلاحياته وكلمة المرور فقط
        existing.role = 'developer'
        existing.password = generate_password_hash('123456', method='pbkdf2:sha256')
        db.session.commit()
        print("⚠️ الحساب كان موجوداً! تم تحديثه ليصبح 'مطور' وتمت إعادة تعيين الباسورد إلى 123456")