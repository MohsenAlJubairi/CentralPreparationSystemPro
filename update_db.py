from app import app, db
# استيراد جميع النماذج ليتعرف عليها النظام قبل التحديث
from models import User, Student, Attendance, PushSubscription

def update_database():
    with app.app_context():
        print("⏳ جارِ الاتصال بقاعدة البيانات...")
        # هذا الأمر سينشئ جدول PushSubscription الجديد ولن يمس الجداول القديمة
        db.create_all()
        print("✅ تم تحديث قاعدة البيانات وإنشاء الجداول الجديدة بنجاح!")

if __name__ == '__main__':
    update_database()