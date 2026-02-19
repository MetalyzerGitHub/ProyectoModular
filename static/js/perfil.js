(function() {
    // Elementos del menú
    const userMenuButton = document.getElementById('userMenuButton');
    const menuDesplegable = document.getElementById('menuDesplegable');
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
    
    // Manejar cierre de sesión
    if (cerrarSesion) {
        cerrarSesion.addEventListener('click', function() {
            // Redirigir al logout de Flask
            window.location.href = '/logout';
        });
    }
    
    // Opcional: animación suave al cargar
    window.addEventListener('load', function() {
        const perfilCard = document.querySelector('.perfil-glass-card');
        if (perfilCard) {
            perfilCard.style.opacity = '0';
            perfilCard.style.transform = 'translateY(20px)';
            
            setTimeout(() => {
                perfilCard.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
                perfilCard.style.opacity = '1';
                perfilCard.style.transform = 'translateY(0)';
            }, 100);
        }
    });
})();