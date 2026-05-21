(function () {

    const container = document.getElementById('letters');
    if (!container) return;

    let selected = null;   // letra seleccionada (clic-clic)
    let dragged  = null;   // letra en arrastre


    // ── PERSISTENCIA DEL ORDEN ──────────────────────────────

    const STORAGE_KEY = 'unscramble_order';

    function saveOrder() {
        const order = [...container.querySelectorAll('.letter')]
            .map(el => el.textContent.trim());
        sessionStorage.setItem(STORAGE_KEY, JSON.stringify(order));
    }

    function restoreOrder() {
        const raw = sessionStorage.getItem(STORAGE_KEY);
        if (!raw) return;

        const saved = JSON.parse(raw);
        const els   = [...container.querySelectorAll('.letter')];

        // Verificar que el conjunto de letras sea el mismo
        const sortFn    = arr => [...arr].sort().join('');
        const current   = sortFn(els.map(el => el.textContent.trim()));
        const savedSort = sortFn(saved);
        if (current !== savedSort) {
            sessionStorage.removeItem(STORAGE_KEY);
            return;
        }

        // Construir mapa char → [elementos]
        const map = {};
        els.forEach(el => {
            const ch = el.textContent.trim();
            (map[ch] = map[ch] || []).push(el);
        });

        // Reordenar el DOM
        saved.forEach(ch => {
            if (map[ch]?.length) {
                container.appendChild(map[ch].shift());
            }
        });
    }


    // ── INTERCAMBIO POR CLIC ────────────────────────────────

    function swapElements(a, b) {
        const aNext = a.nextSibling;
        const bNext = b.nextSibling;

        if (aNext === b) {
            container.insertBefore(b, a);
        } else if (bNext === a) {
            container.insertBefore(a, b);
        } else {
            container.insertBefore(b, aNext);
            container.insertBefore(a, bNext);
        }
    }

    function handleClick(el) {
        if (selected === el) {
            // Segundo clic sobre la misma: deseleccionar
            el.classList.remove('selected');
            selected = null;
            return;
        }

        if (selected) {
            swapElements(selected, el);
            selected.classList.remove('selected');
            selected = null;
        } else {
            selected = el;
            el.classList.add('selected');
        }
    }


    // ── REORDENAMIENTO POR ARRASTRE ─────────────────────────

    function handleDragOver(target, e) {
        e.preventDefault();
        if (!dragged || dragged === target) return;

        const rect = target.getBoundingClientRect();
        const mid  = rect.left + rect.width / 2;

        container.insertBefore(
            dragged,
            e.clientX < mid ? target : target.nextSibling
        );
    }

    // Al soltar sobre el contenedor (espacio vacío al final)
    container.addEventListener('dragover', e => e.preventDefault());
    container.addEventListener('drop', function (e) {
        e.preventDefault();
        if (dragged && e.target === container) {
            container.appendChild(dragged);
        }
    });


    // ── INICIALIZAR CADA LETRA ──────────────────────────────

    function initLetter(el) {
        el.setAttribute('draggable', 'true');

        el.addEventListener('click', () => handleClick(el));

        el.addEventListener('dragstart', function () {
            dragged = el;
            // Cancelar selección pendiente para evitar conflicto
            if (selected) {
                selected.classList.remove('selected');
                selected = null;
            }
            setTimeout(() => el.classList.add('dragging'), 0);
        });

        el.addEventListener('dragend', function () {
            el.classList.remove('dragging');
            dragged = null;
        });

        el.addEventListener('dragover', e => handleDragOver(el, e));
        el.addEventListener('drop',     e => e.preventDefault());
    }

    container.querySelectorAll('.letter').forEach(initLetter);

    // Restaurar orden si venimos de un intento fallido
    restoreOrder();


    // ── VERIFICAR PALABRA ───────────────────────────────────

    function prepareWord() {
        const letters = container.querySelectorAll('.letter');
        let word = '';
        letters.forEach(l => (word += l.textContent.trim()));

        if (!word) {
            alert('No hay letras para verificar');
            return false;
        }

        saveOrder();   // persistir para el próximo render (retry)
        document.getElementById('user_word').value = word;
        return true;
    }

    window.prepareWord = prepareWord;

})();