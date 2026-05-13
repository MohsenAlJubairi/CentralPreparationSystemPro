self.addEventListener('push', function(event) {
    if (event.data) {
        const data = event.data.json();
        const options = {
            body: data.body,
            icon: '/static/Images/logo.png', // أيقونة السكن الخاصة بك التي أصلحناها
            badge: '/static/Images/logo.png',
            dir: 'rtl',
            vibrate: [200, 100, 200] // جعل الهاتف يهتز عند وصول الإشعار
        };
        event.waitUntil(
            self.registration.showNotification(data.title, options)
        );
    }
});

self.addEventListener('notificationclick', function(event) {
    event.notification.close();
    // فتح موقع التحضير عند الضغط على الإشعار
    event.waitUntil(clients.openWindow('/mandoob')); 
});