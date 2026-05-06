(function() {    
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