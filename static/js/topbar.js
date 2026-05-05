// static/js/topbar.js
(function () {
    const userMenuButton  = document.getElementById('userMenuButton');
    const menuDesplegable = document.getElementById('menuDesplegable');
    const cerrarSesion    = document.getElementById('cerrarSesion');
    const miCuenta        = document.getElementById('miCuenta');

    if (userMenuButton) {
        userMenuButton.addEventListener('click', function (e) {
            e.stopPropagation();
            menuDesplegable.classList.toggle('active');
        });
    }

    document.addEventListener('click', function (e) {
        if (!userMenuButton?.contains(e.target) && !menuDesplegable?.contains(e.target)) {
            menuDesplegable?.classList.remove('active');
        }
    });

    if (cerrarSesion) {
        cerrarSesion.addEventListener('click', () => window.location.href = '/logout');
    }

    if (miCuenta) {
        miCuenta.addEventListener('click', function () {
            window.location.href = '/perfil';
            menuDesplegable.classList.remove('active');
        });
    }
})();