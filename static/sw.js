// تم تغيير رقم الإصدار لإجبار المتصفح على تحديث الكاش
const CACHE_NAME = 'bazara-cache-v5';

const urlsToCache = [
    '/static/manifest.json',
    '/static/Images/logo.png',
    '/offline.html' // إضافة صفحة الأوفلاين للقائمة
];

self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => {
                return cache.addAll(urlsToCache);
            })
    );
    self.skipWaiting();
});

self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys().then(cacheNames => {
            return Promise.all(
                cacheNames.map(cacheName => {
                    if (cacheName !== CACHE_NAME) {
                        return caches.delete(cacheName);
                    }
                })
            );
        })
    );
    self.clients.claim();
});

self.addEventListener('fetch', event => {
    const req = event.request;
    const url = new URL(req.url);

    if (url.pathname.startsWith('/static/')) {
        // استراتيجية الملفات الثابتة
        event.respondWith(
            caches.match(req).then(cachedRes => {
                return cachedRes || fetch(req).then(networkRes => {
                    return caches.open(CACHE_NAME).then(cache => {
                        cache.put(req, networkRes.clone());
                        return networkRes;
                    });
                });
            })
        );
    } else {
        // استراتيجية الصفحات المتغيرة مع صفحة بديلة عند انقطاع الإنترنت
        event.respondWith(
            fetch(req).catch(() => {
                // إذا فشل الاتصال وكان المستخدم يطلب صفحة HTML
                if (req.headers.get('accept').includes('text/html')) {
                    return caches.match('/offline.html');
                }
            })
        );
    }
});

// كود الإشعارات
self.addEventListener('push', function(event) {
    const data = event.data ? event.data.json() : {title: "تنبيه", body: "لديك إشعار جديد"};
    const options = {
        body: data.body,
        icon: '/static/Images/logo.png',
        badge: '/static/Images/logo.png',
        dir: 'rtl',
        vibrate: [300, 100, 400, 100, 400], // اهتزاز أقوى وأطول للفت الانتباه
        requireInteraction: true, // يجعله منبثقاً في الأعلى (Heads-up) ولا يختفي حتى يلمسه
        silent: false, // لضمان تشغيل صوت الإشعار الافتراضي للهاتف
        tag: 'mandoob-alert', // لعدم تكرار الإشعارات وتحديث الإشعار القديم
        data: { url: '/' }
    };
    event.waitUntil(self.registration.showNotification(data.title, options));
});

// عند الضغط على الإشعار، يفتح التطبيق مباشرة
self.addEventListener('notificationclick', function(event) {
    event.notification.close();
    event.waitUntil(
        clients.matchAll({ type: 'window' }).then(windowClients => {
            // إذا كان التطبيق مفتوحاً في الخلفية، اجلبه للمقدمة
            for (let i = 0; i < windowClients.length; i++) {
                const client = windowClients[i];
                if (client.url === '/' && 'focus' in client) {
                    return client.focus();
                }
            }
            // إذا لم يكن مفتوحاً، افتح نافذة جديدة
            if (clients.openWindow) {
                return clients.openWindow('/');
            }
        })
    );
});