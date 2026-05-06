(function() {
    // Animación para las opciones
    const options = document.querySelectorAll('.option-item');
    options.forEach((option, index) => {
        option.style.animation = `fadeIn 0.3s ease ${index * 0.1}s both`;
    });
})();