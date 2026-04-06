
document.addEventListener('DOMContentLoaded', function() {
    const esBtn = document.getElementById('lang-es');
    const enBtn = document.getElementById('lang-en');
    const body = document.body;

    function setLanguage(lang) {
        if (lang === 'en') {
            body.classList.add('en');
            esBtn.classList.remove('active');
            enBtn.classList.add('active');
        } else {
            body.classList.remove('en');
            esBtn.classList.add('active');
            enBtn.classList.remove('active');
        }
        localStorage.setItem('preferredLang', lang);
    }

    esBtn.addEventListener('click', () => setLanguage('es'));
    enBtn.addEventListener('click', () => setLanguage('en'));

    // Check for saved preference
    const savedLang = localStorage.getItem('preferredLang');
    if (savedLang) {
        setLanguage(savedLang);
    }

    // Auto-open login modal if there are errors
    const loginError = document.querySelector('.invalid-feedback');
    if (loginError) {
        const modalEl = document.getElementById('loginModal');
        if (modalEl) {
            const loginModal = new bootstrap.Modal(modalEl);
            loginModal.show();
        }
    }
});
