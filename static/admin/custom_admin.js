// MyVisaCrm.com - Inject a prominent power-off logout button into admin navbar
document.addEventListener('DOMContentLoaded', function() {
    var navbar = document.querySelector('#jazzy-navbar .navbar-nav.ms-auto');
    if (!navbar) return;

    // Get the CSRF token
    function getCsrfToken() {
        // Try from existing forms
        var csrfInput = document.querySelector('[name=csrfmiddlewaretoken]');
        if (csrfInput) return csrfInput.value;

        // Try from cookie
        var name = 'csrftoken';
        var cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            var cookies = document.cookie.split(';');
            for (var i = 0; i < cookies.length; i++) {
                var cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue || '';
    }

    // Create the power button
    var li = document.createElement('li');
    li.className = 'nav-item d-flex align-items-center';
    li.innerHTML = 
        '<form method="post" action="/admin/logout/" style="display:inline;margin:0;padding:0;">' +
            '<input type="hidden" name="csrfmiddlewaretoken" value="' + getCsrfToken() + '">' +
            '<button type="submit" class="logout-power-btn" title="Cerrar sesión / Log out">' +
                '<i class="fas fa-power-off"></i>' +
            '</button>' +
        '</form>';

    navbar.appendChild(li);
});
