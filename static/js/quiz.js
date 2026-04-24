(function() {
    // Elementos del menú
    const userMenuButton = document.getElementById('userMenuButton');
    const menuDesplegable = document.getElementById('menuDesplegable');
    const miCuenta = document.getElementById('miCuenta');
    const cerrarSesion = document.getElementById('cerrarSesion');
    
    // Toggle del menú desplegable
    if (userMenuButton) {
        userMenuButton.addEventListener('click', function(e) {
            e.stopPropagation();
            menuDesplegable.classList.toggle('active');
        });
    }
    
    // Cerrar menú al hacer clic fuera
    document.addEventListener('click', function(e) {
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
    
    // Manejar clic en "Mi cuenta"
    if (miCuenta) {
        miCuenta.addEventListener('click', function(e) {
            e.preventDefault();
            window.location.href = '/perfil';
        });
    }
    
    // Manejar cierre de sesión
    if (cerrarSesion) {
        cerrarSesion.addEventListener('click', function(e) {
            e.preventDefault();
            window.location.href = '/logout';
        });
    }

    // Animación para las opciones
    const options = document.querySelectorAll('.option-item');
    options.forEach((option, index) => {
        option.style.animation = `fadeIn 0.3s ease ${index * 0.1}s both`;
    });
})();