(function () {
    const displayUserName   = document.getElementById('displayUserName');
    const mensajeBienvenida = document.getElementById('mensajeBienvenida');
    const leccionRapida     = document.getElementById('leccionRapida');
    const hangman           = document.getElementById('hangman');
    const match             = document.getElementById('match');
    const quiz              = document.getElementById('quiz');
    const unscramble        = document.getElementById('unscramble');

    // Mensaje de bienvenida (lee el nombre del topbar que renderiza Flask)
    const usuario = displayUserName ? displayUserName.textContent.trim() : 'Invitado';
    if (mensajeBienvenida) {
        mensajeBienvenida.textContent = `¡Bienvenido/a, ${usuario}!`;
    }

    // Navegación
    if (leccionRapida) {
        leccionRapida.addEventListener('click', () => window.location.href = '/leccion-rapida');
    }
    if (hangman) {
        hangman.addEventListener('click', () => window.location.href = '/hangman');
    }
    if (match) {
        match.addEventListener('click', () => window.location.href = '/match');
    }
    if (quiz) {
        quiz.addEventListener('click', () => window.location.href = '/quiz');
    }
    if (unscramble) {
        unscramble.addEventListener('click', () => window.location.href = '/unscramble');
    }
})();