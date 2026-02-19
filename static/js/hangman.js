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
            window.location.href = '/logout';
        });
    }
    
    // Auto-focus en el input de letra
    const letterInput = document.querySelector('.letter-input');
    if (letterInput) {
        letterInput.focus();
    }
    
    // Validar que solo se ingresen letras
    const form = document.querySelector('form');
    if (form) {
        form.addEventListener('submit', function(e) {
            const input = document.querySelector('.letter-input');
            const letter = input.value.trim().toLowerCase();
            
            if (!letter.match(/^[a-z]$/)) {
                e.preventDefault();
                alert('Por favor, ingresa solo una letra (a-z)');
                input.value = '';
                input.focus();
            }
        });
    }
})();