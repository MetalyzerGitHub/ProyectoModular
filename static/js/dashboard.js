(function () {

    const displayUserName =
        document.getElementById('displayUserName');

    const mensajeBienvenida =
        document.getElementById('mensajeBienvenida');

    const leccionRapida =
        document.getElementById('leccionRapida');

    // Welcome message
    const usuario = displayUserName
        ? displayUserName.textContent.trim()
        : 'Invitado';

    if (mensajeBienvenida) {
        mensajeBienvenida.textContent =
            `¡Bienvenido/a, ${usuario}!`;
    }

    // Quick lesson
    if (leccionRapida) {
        leccionRapida.addEventListener('click', () => {
            window.location.href = '/leccion-rapida';
        });
    }

    // Activity buttons
    [
        ['hangman', '/hangman'],
        ['hangmanMobile', '/hangman'],

        ['match', '/match'],
        ['matchMobile', '/match'],

        ['quiz', '/quiz'],
        ['quizMobile', '/quiz'],

        ['unscramble', '/unscramble'],
        ['unscrambleMobile', '/unscramble']

    ].forEach(([id, route]) => {

        const el = document.getElementById(id);

        if (el) {
            el.addEventListener('click', () => {
                window.location.href = route;
            });
        }
    });

})();