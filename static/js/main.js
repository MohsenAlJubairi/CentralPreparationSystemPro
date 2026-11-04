// دالة الوضع الليلي
function toggleDarkMode() {
    document.documentElement.classList.toggle('dark');
    const isDark = document.documentElement.classList.contains('dark');
    localStorage.setItem('theme', isDark ? 'dark' : 'light');
    
    const icon = document.getElementById('theme-icon');
    if (icon) {
        if (isDark) {
            icon.classList.replace('fa-moon', 'fa-sun');
        } else {
            icon.classList.replace('fa-sun', 'fa-moon');
        }
    }
}

// دالة فتح وإغلاق النوافذ المنبثقة (Modals)
function toggleModal(modalID) {
    const modal = document.getElementById(modalID);
    if(modal) {
        modal.classList.toggle('hidden');
        modal.classList.toggle('flex');
    }
}

// دالة فتح وإغلاق القائمة الجانبية في وضع الجوال
function toggleMobileSidebar(forceState) {
    const sidebar = document.getElementById('main-sidebar');
    const overlay = document.getElementById('sidebar-overlay');
    if (!sidebar) return;

    const isOpen = typeof forceState === 'boolean' 
        ? forceState 
        : !sidebar.classList.contains('sidebar-open');

    if (isOpen) {
        sidebar.classList.add('sidebar-open');
        if (overlay) overlay.classList.remove('hidden');
        document.body.classList.add('overflow-hidden');
    } else {
        sidebar.classList.remove('sidebar-open');
        if (overlay) overlay.classList.add('hidden');
        document.body.classList.remove('overflow-hidden');
    }
}

// إغلاق القائمة عند الضغط على مفتاح Escape
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        toggleMobileSidebar(false);
    }
});

// إغلاق القائمة تلقائياً عند تكبير الشاشة لسطح المكتب
window.addEventListener('resize', function() {
    if (window.innerWidth >= 768) {
        toggleMobileSidebar(false);
    }
});
