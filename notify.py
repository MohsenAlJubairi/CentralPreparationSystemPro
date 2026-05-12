from app import app, db
from models import User, Attendance
from datetime import datetime, timedelta, timezone

def check_and_notify():
    # 1. الدخول في سياق التطبيق لكي نتمكن من قراءة قاعدة البيانات
    with app.app_context():
        # 2. حساب التاريخ المنطقي (كما فعلنا في الموقع)
        yemen_tz = timezone(timedelta(hours=3))
        now_in_yemen = datetime.now(yemen_tz)
        logical_today = (now_in_yemen - timedelta(hours=3)).date()
        
        # 3. جلب جميع المناديب النشطين
        active_mandoobs = User.query.filter_by(role='mandoob', is_active=True).all()
        
        # 4. جلب معرفات المناديب الذين قاموا بالتحضير اليوم
        submitted_records = Attendance.query.filter_by(date=logical_today).all()
        submitted_mandoob_ids = {record.recorded_by for record in submitted_records}
        
        # 5. استخراج المناديب الذين لم يحضروا
        lazy_mandoobs = [m for m in active_mandoobs if m.id not in submitted_mandoob_ids]
        
        if not lazy_mandoobs:
            print("الجميع قام بالتحضير، لا يوجد متأخرين!")
            return

        # 6. إرسال التنبيهات
        for mandoob in lazy_mandoobs:
            apt = mandoob.student.apartment_number if mandoob.student else "غير معروف"
            message = f"🚨 تذكير هام يا {mandoob.username}!\nلم تقم برفع كشف التحضير لشقة ({apt}) حتى الآن. يرجى الدخول للنظام والتحضير قبل الساعة 3 فجراً."
            
            print(f"يجب إرسال تنبيه إلى: {mandoob.username} - شقة: {apt}")
            
            # (هنا سنضع كود إرسال رسالة التيليجرام لاحقاً)

if __name__ == '__main__':
    check_and_notify()