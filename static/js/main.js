// دالة الوضع الليلي
function toggleDarkMode() {
    document.documentElement.classList.toggle('dark');
    const icon = document.getElementById('theme-icon');
    if (icon) {
        if (document.documentElement.classList.contains('dark')) {
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