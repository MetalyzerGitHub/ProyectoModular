(function () {
    const form   = document.getElementById('hangman-form');
    const hidden = document.getElementById('hidden-letter');

    if (!form || !hidden) return;   // pantalla de resultado: nada que hacer

    // Clic en cualquier tecla disponible
    document.querySelectorAll('.key-btn:not(:disabled)').forEach(function (btn) {
        btn.addEventListener('click', function () {
            const letter = btn.dataset.letter;

            // Deshabilitar inmediatamente para evitar doble envío
            btn.disabled = true;
            btn.classList.add('key-used');

            hidden.value = letter;
            form.submit();
        });
    });

    // Soporte de teclado físico (opcional pero cómodo)
    document.addEventListener('keydown', function (e) {
        const key = e.key.toLowerCase();
        if (!/^[a-z]$/.test(key)) return;

        const btn = document.querySelector(
            '.key-btn[data-letter="' + key + '"]:not(:disabled)'
        );
        if (btn) btn.click();
    });
})();