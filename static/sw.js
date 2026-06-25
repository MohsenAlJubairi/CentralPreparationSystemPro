// تم تغيير رقم الإصدار لإجبار المتصفح على تحديث الكاش
const CACHE_NAME = 'bazara-cache-v3';

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
        vibrate: [200, 100, 200]
    };
    event.waitUntil(self.registration.showNotification(data.title, options));
});