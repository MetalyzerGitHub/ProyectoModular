(function() {
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