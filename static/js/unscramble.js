(function() {
    const userMenuButton = document.getElementById('userMenuButton');
    const menuDesplegable = document.getElementById('menuDesplegable');
    const miCuenta = document.getElementById('miCuenta');
    const cerrarSesion = document.getElementById('cerrarSesion');

    if (userMenuButton) {
        userMenuButton.addEventListener('click', function(e) {
            e.stopPropagation();
            menuDesplegable.classList.toggle('active');
        });
    }
    document.addEventListener('click', function(e) {
        if (!userMenuButton?.contains(e.target) && !menuDesplegable?.contains(e.target)) {
            menuDesplegable?.classList.remove('active');
        }
    });
    if (menuDesplegable) {
        menuDesplegable.addEventListener('click', function(e) { e.stopPropagation(); });
    }
    if (miCuenta) {
        miCuenta.addEventListener('click', function(e) {
            e.preventDefault();
            window.location.href = '/perfil';
        });
    }
    if (cerrarSesion) {
        cerrarSesion.addEventListener('click', function(e) {
            e.preventDefault();
            window.location.href = '/logout';
        });
    }
})();

// ===== LÓGICA DE ARRASTRE =====
let dragged = null;

const dropzone = document.getElementById("dropzone");
const lettersContainer = document.getElementById("letters");

// Hace que una letra sea draggable y registra sus eventos
function makeDraggable(el, fromDropzone) {
    el.setAttribute('draggable', 'true');
    el.style.cursor = 'grab';

    el.addEventListener('dragstart', function(e) {
        dragged = el;
        setTimeout(() => el.style.opacity = '0.4', 0);
    });

    el.addEventListener('dragend', function(e) {
        el.style.opacity = '1';
        dragged = null;
    });

    // Reordenar dentro del dropzone: al pasar sobre otra letra
    if (fromDropzone) {
        el.addEventListener('dragover', function(e) {
            e.preventDefault();
            if (!dragged || dragged === el) return;
            // Solo reordenar si ambos están en el dropzone
            if (dropzone.contains(dragged) && dropzone.contains(el)) {
                const rect = el.getBoundingClientRect();
                const midX = rect.left + rect.width / 2;
                if (e.clientX < midX) {
                    dropzone.insertBefore(dragged, el);
                } else {
                    dropzone.insertBefore(dragged, el.nextSibling);
                }
            }
        });
    }
}

// Inicializar letras del contenedor original
document.querySelectorAll('#letters .letter').forEach(el => makeDraggable(el, false));

// --- DROPZONE: recibir letras desde el contenedor original ---
dropzone.addEventListener('dragover', function(e) {
    e.preventDefault();
    dropzone.style.backgroundColor = 'rgba(27, 47, 79, 0.08)';
});

dropzone.addEventListener('dragleave', function(e) {
    // Solo quitar el estilo si el cursor salió del dropzone completamente
    if (!dropzone.contains(e.relatedTarget)) {
        dropzone.style.backgroundColor = '';
    }
});

dropzone.addEventListener('drop', function(e) {
    e.preventDefault();
    dropzone.style.backgroundColor = '';

    if (!dragged) return;

    // Si viene del contenedor original, moverla al dropzone
    if (lettersContainer.contains(dragged)) {
        const placeholder = dropzone.querySelector('.text-muted');
        if (placeholder) placeholder.remove();

        lettersContainer.removeChild(dragged);
        makeDraggable(dragged, true); // ahora es reordenable
        dropzone.appendChild(dragged);
    }
    // Si ya estaba en el dropzone, el reorden lo maneja el dragover de cada letra
});

// --- CONTENEDOR ORIGINAL: recibir letras de vuelta desde el dropzone ---
lettersContainer.addEventListener('dragover', function(e) {
    e.preventDefault();
});

lettersContainer.addEventListener('drop', function(e) {
    e.preventDefault();
    if (!dragged || !dropzone.contains(dragged)) return;

    dropzone.removeChild(dragged);
    makeDraggable(dragged, false); // deja de ser reordenable entre sí
    lettersContainer.appendChild(dragged);

    // Restaurar placeholder si el dropzone quedó vacío
    if (dropzone.querySelectorAll('.letter').length === 0) {
        const ph = document.createElement('span');
        ph.className = 'text-muted';
        ph.style.opacity = '0.5';
        ph.textContent = 'Arrastra las letras aquí';
        dropzone.appendChild(ph);
    }
});

// --- Verificar palabra ---
function prepareWord() {
    const letters = document.querySelectorAll('#dropzone .letter');
    let word = '';
    letters.forEach(l => word += l.innerText.trim());

    if (word.length === 0) {
        alert('Por favor, ordena las letras en el área inferior');
        return false;
    }

    document.getElementById('user_word').value = word;
    return true;
}

window.prepareWord = prepareWord;