from app import app, db
from models import User, Attendance
from datetime import datetime, timedelta, timezone

def check_and_notify():
    # 1. الدخول في سياق التطبيق لكي نتمكن من قراءة قاعدة البيانات
    with app.app_context():
        # 2. حساب التاريخ المنطقي (كما في الموقع)
        yemen_tz = timezone(timedelta(hours=3))
        now_in_yemen = datetime.now(yemen_tz)
        logical_today = (now_in_yemen - timedelta(hours=6)).date()
        
        # 3. جلب جميع المناديب النشطين
        active_mandoobs = User.query.filter_by(role='mandoob', is_active=True).all()
        
        # 4. جلب أرقام الشقق التي تم تحضير طلابها اليوم (سواء من المندوب أو الإدارة)
        prepared_apartments = set(
            row[0] for row in db.session.query(Student.apartment_number)
            .join(Attendance, Attendance.student_id == Student.id)
            .filter(Attendance.date == logical_today)
            .distinct().all()
        )
        
        # 5. استخراج المناديب الذين لم يتم تحضير شققهم اليوم
        lazy_mandoobs = [
            m for m in active_mandoobs 
            if m.student and m.student.apartment_number not in prepared_apartments
        ]
        
        if not lazy_mandoobs:
            print("الجميع قام بالتحضير، لا يوجد متأخرين!")
            return

        # 6. إرسال التنبيهات
        for mandoob in lazy_mandoobs:
            apt = mandoob.student.apartment_number if mandoob.student else "غير معروف"
            message = f"🚨 تذكير هام يا {mandoob.username}!\nلم تقم برفع كشف التحضير لشقة ({apt}) حتى الآن. يرجى الدخول للنظام والتحضير قبل الساعة 3 فجراً."
            
            print(f"يجب إرسال تنبيه إلى: {mandoob.username} - شقة: {apt}")
            

if __name__ == '__main__':
    check_and_notify()