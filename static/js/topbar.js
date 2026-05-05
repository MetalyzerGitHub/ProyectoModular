// static/js/topbar.js
(function () {
    const userMenuButton  = document.getElementById('userMenuButton');
    const menuDesplegable = document.getElementById('menuDesplegable');
    const miCuenta        = document.getElementById('miCuenta');
    const cerrarSesion    = document.getElementById('cerrarSesion');
    
    // Toggle del menú desplegable
    if (userMenuButton) {
        userMenuButton.addEventListener('click', function (e) {
            e.stopPropagation();
            menuDesplegable.classList.toggle('active');
        });
    }

    // Cerrar menú al hacer clic fuera
    document.addEventListener('click', function (e) {
        if (!userMenuButton?.contains(e.target) && !menuDesplegable?.contains(e.target)) {
            menuDesplegable?.classList.remove('active');
        }
    });

    // Prevenir que clics dentro del menú lo cierren
    if (menuDesplegable) {
        menuDesplegable.addEventListener('click', function(e) {
            e.stopPropagation();
        });
    }

    // Manejar cierre de sesión
    if (cerrarSesion) {
        cerrarSesion.addEventListener('click', () => window.location.href = '/logout');
    }

    // Manejar clic en "Mi cuenta"
    if (miCuenta) {
        miCuenta.addEventListener('click', function () {
            window.location.href = '/perfil';
            menuDesplegable.classList.remove('active');
        });
    }
})();