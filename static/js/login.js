(function() {
    // Elementos del DOM
    const modal = document.getElementById('registroModal');
    const registerTop = document.getElementById('registerTopBtn');
    const registerBottom = document.getElementById('registerBottomLink');
    const closeModal = document.getElementById('closeModalBtn');
    const loginForm = document.getElementById('loginForm');
    const registerForm = document.getElementById('registerForm');
    
    // Función para abrir el modal
    function abrirModal(e) {
        if (e) e.preventDefault();
        modal.classList.add('active');
        document.body.style.overflow = 'hidden';
    }
    
    // Función para cerrar el modal
    function cerrarModal() {
        modal.classList.remove('active');
        document.body.style.overflow = 'auto';
    }
    
    // Event Listeners
    if (registerTop) {
        registerTop.addEventListener('click', abrirModal);
    }
    
    if (registerBottom) {
        registerBottom.addEventListener('click', abrirModal);
    }
    
    if (closeModal) {
        closeModal.addEventListener('click', cerrarModal);
    }
    
    // Cerrar modal si se hace clic fuera del contenido
    modal.addEventListener('click', function(e) {
        if (e.target === modal) {
            cerrarModal();
        }
    });
    
    // Cerrar modal con tecla ESC
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && modal.classList.contains('active')) {
            cerrarModal();
        }
    });
    
    // Mostrar mensajes flash (si existen)
    function showFlashMessages() {
        // Esta función puede ser implementada para mostrar mensajes flash
        // usando Bootstrap toasts o alerts
    }
})();