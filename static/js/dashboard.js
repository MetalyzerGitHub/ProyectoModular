(function() {
    // Elementos del DOM
    const userMenuButton = document.getElementById('userMenuButton');
    const menuDesplegable = document.getElementById('menuDesplegable');
    const cerrarSesion = document.getElementById('cerrarSesion');
    const miCuenta = document.getElementById('miCuenta');
    const displayUserName = document.getElementById('displayUserName');
    const mensajeBienvenida = document.getElementById('mensajeBienvenida');
    const nivelUsuario = document.getElementById('nivelUsuario');
    const barraProgreso = document.getElementById('barraProgreso');
    const progresoTexto = document.getElementById('progresoTexto');
    const leccionRapida = document.getElementById('leccionRapida');
    const hangman = document.getElementById('hangman');
    const match = document.getElementById('match');
    const quiz = document.getElementById('quiz');
    const unscramble = document.getElementById('unscramble');
    
    // Obtener nombre de usuario del elemento HTML (enviado por Flask)
    // No usar localStorage, Flask maneja la sesión
    let usuario = displayUserName ? displayUserName.textContent : 'Invitado';
    
    // Mostrar mensaje de bienvenida
    if (mensajeBienvenida) {
        mensajeBienvenida.textContent = `¡Bienvenido/a, ${usuario}!`;
    }
    
    // Valores dinámicos de nivel y progreso (simulados)
    const nivelActual = 3;
    const progresoActual = 65; // porcentaje
    
    if (nivelUsuario) nivelUsuario.textContent = nivelActual;
    if (barraProgreso) barraProgreso.style.width = progresoActual + '%';
    if (progresoTexto) progresoTexto.textContent = progresoActual + '% al Nivel ' + (nivelActual + 1);
    
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
    
    // Manejar cierre de sesión - REDIRIGIR A RUTA FLASK
    if (cerrarSesion) {
        cerrarSesion.addEventListener('click', function() {
            // Redirigir a la ruta de logout de Flask
            window.location.href = '/logout';
        });
    }
    
    // Manejar clic en "Mi cuenta"
    if (miCuenta) {
        miCuenta.addEventListener('click', function() {
            // Redirigir a la página de perfil (si existe)
            window.location.href = '/perfil';
            // O mostrar un modal
            // alert('Aquí iría la configuración de la cuenta de ' + usuario);
            menuDesplegable.classList.remove('active');
        });
    }
    
    // Manejar clic en "Lección Rápida"
    if (leccionRapida) {
        leccionRapida.addEventListener('click', function() {
            // Aquí puedes redirigir a una lección aleatoria
            window.location.href = '/leccion-rapida';
        });
    }

        // Manejar clic en "Hangman"
    if (hangman) {
        hangman.addEventListener('click', function() {
            // Aquí puedes redirigir a una lección aleatoria
            window.location.href = '/hangman';
        });
    }

        // Manejar clic en "Match"
    if (match) {
        match.addEventListener('click', function() {
            // Aquí puedes redirigir a una lección aleatoria
            window.location.href = '/match';
        });
    }

       // Manejar clic en "Quiz"
    if (quiz) {
        quiz.addEventListener('click', function() {
            // Aquí puedes redirigir a una lección aleatoria
            window.location.href = '/quiz';
        });
    }

    // Manejar clic en "Unscramble"
    if (unscramble) {
        unscramble.addEventListener('click', function() {
            // Aquí puedes redirigir a una lección aleatoria
            window.location.href = '/unscramble';
        });
    }

    // Función para mostrar mensajes flash (si los hay)
    function showFlashMessage(message, type) {
        // Crear elemento de alerta
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show position-fixed top-0 end-0 m-3`;
        alertDiv.style.zIndex = '9999';
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        document.body.appendChild(alertDiv);
        
        // Auto-cerrar después de 5 segundos
        setTimeout(() => {
            alertDiv.remove();
        }, 5000);
    }
})();