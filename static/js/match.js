(function () {
    // ── USER MENU ──────────────────────────────────────────────────────────────
    const userMenuButton = document.getElementById('userMenuButton');
    const menuDesplegable = document.getElementById('menuDesplegable');
    const miCuenta = document.getElementById('miCuenta');
    const cerrarSesion = document.getElementById('cerrarSesion');

    if (userMenuButton) {
        userMenuButton.addEventListener('click', function (e) {
            e.stopPropagation();
            menuDesplegable.classList.toggle('active');
        });
    }
    document.addEventListener('click', function (e) {
        if (!userMenuButton?.contains(e.target) && !menuDesplegable?.contains(e.target)) {
            menuDesplegable?.classList.remove('active');
        }
    });
    if (menuDesplegable) {
        menuDesplegable.addEventListener('click', e => e.stopPropagation());
    }
    if (miCuenta) miCuenta.addEventListener('click', () => (window.location.href = '/perfil'));
    if (cerrarSesion) cerrarSesion.addEventListener('click', () => (window.location.href = '/logout'));

    // ── MATCHING GAME ──────────────────────────────────────────────────────────
    const svg = document.getElementById('linesSvg');
    if (!svg) return; // Result page – nothing to do

    const arena = document.getElementById('matchArena');
    const submitBtn = document.getElementById('submitBtn');
    const resetBtn = document.getElementById('resetBtn');
    const progressFill = document.getElementById('progressFill');
    const connectedCount = document.getElementById('connectedCount');

    const leftCards = Array.from(document.querySelectorAll('.left-card'));
    const rightCards = Array.from(document.querySelectorAll('.right-card'));
    const totalWords = leftCards.length;

    // State
    let selectedLeft = null;       // currently highlighted left card
    let connections = {};          // { leftId: { rightEl, meaning, lineEl } }
    let lineColors = {};           // { leftId: color }

    const PALETTE = [
        '#3b82f6', '#10b981', '#f59e0b', '#ef4444',
        '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16'
    ];
    let colorIdx = 0;

    function nextColor() {
        const c = PALETTE[colorIdx % PALETTE.length];
        colorIdx++;
        return c;
    }

    // ── Geometry helpers ──────────────────────────────────────────────────────
    function getAnchor(el, side) {
        const arenaRect = arena.getBoundingClientRect();
        const rect = el.getBoundingClientRect();
        const y = rect.top - arenaRect.top + rect.height / 2;
        const x = side === 'right'
            ? rect.right - arenaRect.left
            : rect.left - arenaRect.left;
        return { x, y };
    }

    function buildPath(x1, y1, x2, y2) {
        const cx = (x1 + x2) / 2;
        return `M ${x1} ${y1} C ${cx} ${y1}, ${cx} ${y2}, ${x2} ${y2}`;
    }

    function drawLine(leftEl, rightEl, color) {
        const a = getAnchor(leftEl, 'right');
        const b = getAnchor(rightEl, 'left');

        const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        path.setAttribute('d', buildPath(a.x, a.y, b.x, b.y));
        path.setAttribute('stroke', color);
        path.setAttribute('stroke-width', '3');
        path.setAttribute('fill', 'none');
        path.setAttribute('stroke-linecap', 'round');
        path.setAttribute('opacity', '0.85');
        path.classList.add('connection-line');

        svg.appendChild(path);
        return path;
    }

    function updateLine(lineEl, leftEl, rightEl) {
        const a = getAnchor(leftEl, 'right');
        const b = getAnchor(rightEl, 'left');
        lineEl.setAttribute('d', buildPath(a.x, a.y, b.x, b.y));
    }

    function redrawAllLines() {
        for (const [leftId, conn] of Object.entries(connections)) {
            const leftEl = document.getElementById('left_' + leftId);
            updateLine(conn.lineEl, leftEl, conn.rightEl);
        }
    }

    // ── State management ──────────────────────────────────────────────────────
    function updateProgress() {
        const done = Object.keys(connections).length;
        connectedCount.textContent = done;
        progressFill.style.width = (done / totalWords * 100) + '%';
        submitBtn.disabled = done < totalWords;
    }

    function applyAnswers() {
        for (const [leftId, conn] of Object.entries(connections)) {
            const inp = document.getElementById('answer_' + leftId);
            if (inp) inp.value = conn.meaning;
        }
    }

    function removeConnection(leftId) {
        const conn = connections[leftId];
        if (!conn) return;
        conn.lineEl.remove();
        conn.rightEl.classList.remove('connected', 'matched');
        conn.rightEl.style.removeProperty('--conn-color');
        delete connections[leftId];

        const leftEl = document.getElementById('left_' + leftId);
        leftEl.classList.remove('connected');
        leftEl.style.removeProperty('--conn-color');
    }

    function connect(leftCard, rightCard) {
        const leftId = leftCard.dataset.id;
        const meaning = rightCard.dataset.meaning;

        // If right card is already connected to another left, remove that connection
        for (const [id, conn] of Object.entries(connections)) {
            if (conn.rightEl === rightCard && id !== leftId) {
                removeConnection(id);
                break;
            }
        }

        // Remove existing connection for this left card
        if (connections[leftId]) removeConnection(leftId);

        // Assign / reuse color
        if (!lineColors[leftId]) lineColors[leftId] = nextColor();
        const color = lineColors[leftId];

        const lineEl = drawLine(leftCard, rightCard, color);

        connections[leftId] = { rightEl: rightCard, meaning, lineEl };

        leftCard.classList.add('connected');
        leftCard.style.setProperty('--conn-color', color);
        rightCard.classList.add('connected');
        rightCard.style.setProperty('--conn-color', color);

        applyAnswers();
        updateProgress();

        // Animate the line in
        lineEl.style.strokeDasharray = lineEl.getTotalLength?.() || 300;
        lineEl.style.strokeDashoffset = lineEl.getTotalLength?.() || 300;
        lineEl.style.transition = 'stroke-dashoffset 0.35s ease';
        requestAnimationFrame(() => { lineEl.style.strokeDashoffset = 0; });
    }

    function clearSelection() {
        if (selectedLeft) {
            selectedLeft.classList.remove('selected');
            selectedLeft = null;
        }
    }

    // ── Click handlers ────────────────────────────────────────────────────────
    leftCards.forEach(card => {
        card.addEventListener('click', () => {
            if (selectedLeft === card) {
                clearSelection();
                return;
            }
            clearSelection();
            selectedLeft = card;
            card.classList.add('selected');
        });
    });

    rightCards.forEach(card => {
        card.addEventListener('click', () => {
            if (!selectedLeft) return;
            connect(selectedLeft, card);
            clearSelection();
        });
    });

    // Reset button
    resetBtn?.addEventListener('click', () => {
        const leftIds = Object.keys(connections);
        leftIds.forEach(id => removeConnection(id));
        clearSelection();
        lineColors = {};
        colorIdx = 0;
        updateProgress();
    });

    // Redraw lines on resize
    window.addEventListener('resize', redrawAllLines);

    // ── Form validation ───────────────────────────────────────────────────────
    document.getElementById('matchForm')?.addEventListener('submit', function (e) {
        const unanswered = leftCards.filter(c => !connections[c.dataset.id]);
        if (unanswered.length > 0) {
            e.preventDefault();
            unanswered.forEach(c => c.classList.add('shake'));
            setTimeout(() => unanswered.forEach(c => c.classList.remove('shake')), 600);
        }
    });
})();