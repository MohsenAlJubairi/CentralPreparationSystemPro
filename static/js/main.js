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