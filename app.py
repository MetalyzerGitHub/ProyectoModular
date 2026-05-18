import os
import time
from flask import Flask, render_template, request, redirect, session, flash, url_for
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
import random
import math

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")

con = mysql.connector.connect(
    host=os.getenv("MYSQLHOST"),
    user=os.getenv("MYSQLUSER"),
    password=os.getenv("MYSQLPASSWORD"),
    database=os.getenv("MYSQLDATABASE")
)

# =============================================================
# MOTOR DE APRENDIZAJE ADAPTATIVO  (IRT + K-factor dinámico)
# =============================================================
#
# Modelo: 2PL Item Response Theory (IRT)
#   P(éxito | skill θ, dificultad β) = 1 / (1 + exp(−a·(θ − β)))
#   • θ (skill)  ∈ [0, 1]  – habilidad estimada del usuario
#   • β (difficulty) ∈ [0, 1]  – dificultad de la palabra
#   • a (discrimination) – constante que controla la pendiente
#
# Cuando θ ≈ β  →  P ≈ 0.5  (objetivo: ~50 % de aciertos)
#
# Actualización por gradiente (ascenso de log-verosimilitud):
#   θ_nuevo = θ + K · (real − esperado)
#   donde K decae con el número de intentos acumulados.
#
# K dinámico:
#   K(n) = K_MIN + (K_MAX − K_MIN) · exp(−n / HALFLIFE)
#   • n=0:  K ≈ K_MAX  → aprendizaje rápido (ubicación inicial)
#   • n→∞: K → K_MIN  → ajuste fino gradual
# =============================================================

DISCRIMINATION = 2.5   # Pendiente de la curva logística
K_MAX = 0.28           # Tasa de aprendizaje máxima (usuarios nuevos)
K_MIN = 0.04           # Tasa de aprendizaje mínima (usuarios experimentados)
K_HALFLIFE = 20        # Intentos hasta que K cae a la mitad del rango


def irt_probability(skill: float, difficulty: float) -> float:
    """
    Modelo IRT de 2 parámetros.
    Retorna P(correcto | skill, difficulty).
    P = 0.5 exactamente cuando skill == difficulty.
    """
    return 1.0 / (1.0 + math.exp(-DISCRIMINATION * (skill - difficulty)))


def dynamic_k(attempt_count: int) -> float:
    """
    Tasa de aprendizaje decreciente.
    Alta al inicio (ubicación rápida), baja después (ajuste fino).
    """
    return K_MIN + (K_MAX - K_MIN) * math.exp(-attempt_count / K_HALFLIFE)


def get_user_attempt_count(user_id: int) -> int:
    """Número total de intentos del usuario (para calcular K dinámico)."""
    cursor = con.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM intentos WHERE fk_usuario = %s", (user_id,)
    )
    count = cursor.fetchone()[0]
    cursor.close()
    return int(count)


def update_user_skill(user_id: int, word_difficulty: float, success: bool):
    """
    Actualiza el skill del usuario mediante gradiente IRT con K dinámico.

    Fórmula:  θ_nuevo = θ + K(n) · (real − P(correcto | θ, β))

    - Si el usuario acierta una palabra difícil (para él): sube bastante.
    - Si falla una palabra fácil (para él): baja bastante.
    - Aciertos/fallos en el umbral de habilidad tienen efecto moderado.
    """
    word_difficulty = float(word_difficulty)
    cursor = con.cursor()
    cursor.execute(
        "SELECT skill FROM usuarios WHERE id_usuario = %s", (user_id,)
    )
    row = cursor.fetchone()
    if not row:
        cursor.close()
        return

    current_skill = float(row[0]) if row[0] is not None else 0.5
    n = get_user_attempt_count(user_id)
    k = dynamic_k(n)
    expected = irt_probability(current_skill, word_difficulty)
    actual = 1.0 if success else 0.0

    new_skill = current_skill + k * (actual - expected)
    new_skill = max(0.0, min(1.0, new_skill))

    cursor.execute(
        "UPDATE usuarios SET skill = %s WHERE id_usuario = %s",
        (new_skill, user_id)
    )
    con.commit()
    cursor.close()


# ------------------------------------------------------------------
# SELECCIÓN ADAPTATIVA DE PALABRAS
# ------------------------------------------------------------------
#
# Peso de cada palabra = peso_gaussiano × peso_novedad
#
# peso_gaussiano = exp(−GAUSS_K · (difficulty − skill)²)
#   • Máximo cuando difficulty ≈ skill  → P(éxito) ≈ 0.5
#   • GAUSS_K controla qué tan estricta es la selección alrededor del skill
#
# peso_novedad:
#   • Nunca vista:              3.0×  (exploración)
#   • Vista y fallada alguna vez: 2.0×  (refuerzo)
#   • Vista y acertada alguna vez: 0.6×  (repaso ocasional)
#
# La selección final = ORDER BY (peso_gaussiano × peso_novedad × RAND())
# Esto da variedad estocástica respetando la distribución de pesos.
# ------------------------------------------------------------------

GAUSS_K = 8.0          # Foco gaussiano: a ±0.35 del skill, peso cae ~37 %
SEARCH_WINDOW = 0.35   # Ventana de búsqueda en torno al skill del usuario


def select_adaptive_word(user_id: int, exclude_ids: set = None):
    """
    Selecciona una palabra adaptada al nivel del usuario.

    Parámetros:
        user_id    – ID del usuario en sesión.
        exclude_ids – conjunto de id_word a excluir (para lecciones con
                      múltiples palabras sin repetición).

    Retorna un diccionario con los datos de la palabra, o None si no hay
    candidatos.
    """
    cursor = con.cursor(dictionary=True)
    cursor.execute(
        "SELECT skill FROM usuarios WHERE id_usuario = %s", (user_id,)
    )
    user = cursor.fetchone()
    cursor.close()
    skill = float(user["skill"]) if user and user["skill"] is not None else 0.5

    lower = max(0.0, skill - SEARCH_WINDOW)
    upper = min(1.0, skill + SEARCH_WINDOW)

    # Cláusula de exclusión dinámica
    exclude_clause = ""
    exclude_params = []
    if exclude_ids:
        placeholders = ", ".join(["%s"] * len(exclude_ids))
        exclude_clause = f"AND w.id_word NOT IN ({placeholders})"
        exclude_params = list(exclude_ids)

    query = f"""
        SELECT w.*,
               EXP(-%s * POW(w.difficulty - %s, 2)) *
               CASE
                   WHEN i.max_correcto IS NULL THEN 3.0
                   WHEN i.max_correcto = 0    THEN 2.0
                   ELSE 0.6
               END AS adapt_weight
        FROM words w
        LEFT JOIN (
            SELECT fk_palabra,
                   MAX(CASE WHEN correcto = 1 THEN 1 ELSE 0 END) AS max_correcto
            FROM intentos
            WHERE fk_usuario = %s
            GROUP BY fk_palabra
        ) i ON w.id_word = i.fk_palabra
        WHERE w.difficulty BETWEEN %s AND %s
        {exclude_clause}
        ORDER BY adapt_weight * RAND() DESC
        LIMIT 1
    """
    params = [GAUSS_K, skill, user_id, lower, upper] + exclude_params

    cursor = con.cursor(dictionary=True)
    cursor.execute(query, params)
    word = cursor.fetchone()
    cursor.close()

    if word:
        word["difficulty"] = float(word["difficulty"])
        return word
    return None


def random_word_excluding(exclude_ids: set = None):
    """Fallback: palabra aleatoria, opcionalmente excluyendo IDs específicos."""
    cursor = con.cursor(dictionary=True)
    if exclude_ids:
        placeholders = ", ".join(["%s"] * len(exclude_ids))
        cursor.execute(
            f"SELECT * FROM words WHERE id_word NOT IN ({placeholders}) "
            f"ORDER BY RAND() LIMIT 1",
            list(exclude_ids)
        )
    else:
        cursor.execute("SELECT * FROM words ORDER BY RAND() LIMIT 1")
    word = cursor.fetchone()
    cursor.close()
    if word and "difficulty" in word:
        word["difficulty"] = float(word["difficulty"])
    return word


def random_word():
    """Alias de fallback sin exclusiones."""
    return random_word_excluding()


def get_word_by_id(word_id: int):
    """Obtiene una palabra por su clave primaria."""
    cursor = con.cursor(dictionary=True)
    cursor.execute("SELECT * FROM words WHERE id_word = %s", (word_id,))
    word = cursor.fetchone()
    cursor.close()
    if word and "difficulty" in word:
        word["difficulty"] = float(word["difficulty"])
    return word


# ------------------------------------------------------------------
# PRE-SELECCIÓN DE PALABRAS PARA LECCIÓN RÁPIDA
# ------------------------------------------------------------------
#
# En lugar de seleccionar palabras en el momento de cada minijuego,
# las palabras se eligen todas al inicio de la lección y se almacenan
# en sesión. Beneficios:
#   1. No hay repetición de palabras entre minijuegos.
#   2. La selección refleja el skill del usuario en un único momento.
#   3. Cada juego simplemente lee "su" palabra pre-asignada.
#
# Formato en sesión:
#   session['leccion_word_ids'] = {
#       'hangman':   id_word (int),
#       'match':     [id_word1, id_word2, id_word3],
#       'quiz':      id_word (int),
#       'unscramble': id_word (int),
#   }
# ------------------------------------------------------------------

def preselect_leccion_words(user_id: int, games: list) -> dict:
    """
    Pre-selecciona las palabras necesarias para todos los minijuegos de
    una lección, garantizando que no se repita ninguna palabra.

    Retorna un dict {nombre_juego: id_word | [id_word, ...]}
    """
    used_ids: set = set()
    selection: dict = {}

    for game in games:
        if game == "match":
            ids = []
            for _ in range(3):
                word = select_adaptive_word(user_id, exclude_ids=used_ids)
                if not word:
                    word = random_word_excluding(exclude_ids=used_ids)
                if word:
                    ids.append(word["id_word"])
                    used_ids.add(word["id_word"])
            selection["match"] = ids
        else:
            word = select_adaptive_word(user_id, exclude_ids=used_ids)
            if not word:
                word = random_word_excluding(exclude_ids=used_ids)
            if word:
                selection[game] = word["id_word"]
                used_ids.add(word["id_word"])

    return selection


# ------------------------------------------------------------------
# FUNCIONES AUXILIARES GENERALES
# ------------------------------------------------------------------

def get_game_id(cursor, game_name: str):
    """
    Obtiene el id_juego de la tabla juegos (comparación sin distinción
    de mayúsculas/minúsculas para mayor robustez).
    """
    cursor.execute(
        "SELECT id_juego FROM juegos WHERE LOWER(nombre) = LOWER(%s)",
        (game_name,)
    )
    row = cursor.fetchone()
    return row[0] if row else None


def increment_user_level(user_id: int, amount: float = 0.1):
    """Aumenta el nivel del usuario en una cantidad fija por acierto."""
    cursor = con.cursor()
    cursor.execute(
        "UPDATE usuarios SET nivel = nivel + %s WHERE id_usuario = %s",
        (amount, user_id)
    )
    con.commit()
    cursor.close()


################### RUTAS ###################

# INDEX
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/register", methods=["POST"])
def register():
    nombre = request.form["nombre"]
    password = request.form["password"]
    cursor = None
    try:
        cursor = con.cursor()
        cursor.execute(
            "SELECT id_usuario FROM usuarios WHERE nombre_usuario = %s", (nombre,)
        )
        if cursor.fetchone():
            flash("El usuario ya existe. Elige otro nombre.", "error")
            return redirect("/")
        hash_password = generate_password_hash(password)
        cursor.execute(
            "INSERT INTO usuarios (nombre_usuario, contrasena_hash) VALUES (%s, %s)",
            (nombre, hash_password)
        )
        con.commit()
        flash("Cuenta creada correctamente. Ahora puedes iniciar sesión.", "success")
    except Exception as e:
        print(f"Error en registro: {e}")
        flash("Error al crear la cuenta. Intenta de nuevo.", "error")
        if con:
            con.rollback()
    finally:
        if cursor:
            cursor.close()
    return redirect("/")


@app.route("/login", methods=["POST"])
def login():
    nombre = request.form["nombre"]
    password = request.form["password"]
    cursor = None
    try:
        cursor = con.cursor()
        cursor.execute(
            "SELECT id_usuario, nombre_usuario, contrasena_hash "
            "FROM usuarios WHERE nombre_usuario = %s",
            (nombre,)
        )
        usuario = cursor.fetchone()
        if usuario and check_password_hash(usuario[2], password):
            session["usuario"] = usuario[1]
            session["user_id"] = usuario[0]
            return redirect("/dashboard")
        else:
            flash("Usuario o contraseña incorrectos", "error")
    except Exception as e:
        print(f"Error en login: {e}")
        flash("Error al iniciar sesión. Intenta de nuevo.", "error")
    finally:
        if cursor:
            cursor.close()
    return redirect("/")


######## DASHBOARD ########

def obtener_nivel():
    cursor = None
    try:
        cursor = con.cursor()
        cursor.execute(
            "SELECT nivel FROM usuarios WHERE id_usuario = %s",
            (session["user_id"],)
        )
        result = cursor.fetchone()
    except Exception as e:
        print(f"Error al obtener nivel: {e}")
        result = None
    finally:
        if cursor:
            cursor.close()
    return float(result[0]) if result and result[0] is not None else 0.0


@app.route("/dashboard")
def dashboard():
    if "usuario" not in session:
        flash("Por favor inicia sesión primero", "error")
        return redirect("/")
    nivel_decimal = obtener_nivel()
    nivel = int(nivel_decimal)
    return render_template(
        "dashboard.html",
        usuario=session["usuario"],
        nivel=nivel,
        progreso=int((nivel_decimal - nivel) * 100),
        nivel_siguiente=nivel + 1
    )


@app.route("/perfil")
def perfil():
    if "usuario" not in session:
        flash("Por favor inicia sesión primero", "error")
        return redirect("/")
    nivel_decimal = obtener_nivel()
    nivel = int(nivel_decimal)
    return render_template(
        "perfil.html",
        usuario=session["usuario"],
        nivel=nivel,
        progreso=int((nivel_decimal - nivel) * 100),
        nivel_siguiente=nivel + 1
    )


######## LECCIÓN RÁPIDA ########

@app.route("/leccion-rapida")
def leccion_rapida():
    if "usuario" not in session:
        flash("Inicia sesión primero", "error")
        return redirect("/")

    all_games = ["hangman", "match", "quiz", "unscramble"]
    k = random.choice([3, 4])
    games = random.sample(all_games, k=k)

    # Pre-selección de palabras para toda la lección
    word_ids = preselect_leccion_words(session["user_id"], games)

    session["leccion_mode"] = True
    session["leccion_games"] = games
    session["leccion_index"] = 0
    session["leccion_results"] = []
    session["leccion_result_recorded"] = False
    session["leccion_word_ids"] = word_ids          # ← palabras pre-asignadas
    session["leccion_game_start"] = time.time()

    return redirect(url_for(_game_route(games[0])))


@app.route("/leccion/next")
def leccion_next():
    if not session.get("leccion_mode"):
        return redirect(url_for("dashboard"))

    session["leccion_index"] += 1
    games = session["leccion_games"]
    idx = session["leccion_index"]

    if idx >= len(games):
        return redirect(url_for("leccion_summary"))

    session["leccion_result_recorded"] = False
    session["leccion_game_start"] = time.time()
    return redirect(url_for(_game_route(games[idx])))


def _game_route(game_name: str) -> str:
    """Mapea nombre de juego a nombre de función de ruta Flask."""
    return {
        "hangman": "hangman",
        "match":   "match",
        "quiz":    "quiz",
        "unscramble": "unscramble",
    }.get(game_name, "dashboard")


@app.route("/leccion/cancel")
def leccion_cancel():
    _clear_leccion_session()
    return redirect(url_for("dashboard"))


@app.route("/leccion/summary")
def leccion_summary():
    if not session.get("leccion_mode"):
        return redirect(url_for("dashboard"))
    results = session.get("leccion_results", [])
    total_time = sum(r.get("time", 0) for r in results)
    return render_template(
        "leccion_summary.html",
        results=results,
        total_time=round(total_time, 1),
        usuario=session["usuario"]
    )


@app.route("/leccion/finish")
def leccion_finish():
    _clear_leccion_session()
    return redirect(url_for("dashboard"))


def _clear_leccion_session():
    for key in [
        "leccion_mode", "leccion_games", "leccion_index",
        "leccion_results", "leccion_result_recorded",
        "leccion_game_start", "leccion_word_ids",
    ]:
        session.pop(key, None)


######## ACTIVIDADES ########

# ── HANGMAN ──────────────────────────────────────────────────────

@app.route("/hangman")
def hangman():
    if "usuario" not in session:
        flash("Inicia sesión primero", "error")
        return redirect("/")

    # En modo lección, usar la palabra pre-asignada
    if session.get("leccion_mode") and "leccion_word_ids" in session:
        wid = session["leccion_word_ids"].get("hangman")
        word = get_word_by_id(wid) if wid else None
    else:
        word = select_adaptive_word(session["user_id"])

    if not word:
        word = random_word()
    if not word:
        flash("No hay palabras disponibles", "error")
        return redirect(url_for("dashboard"))

    wlen = word["wlen"]
    # Intentos: base logarítmica en función de la longitud
    max_attempts = math.ceil(1 + math.log(wlen + 1) * 2)

    session["word"] = word["spelling"].lower()
    session["meaning"] = word["meaning"]
    session["img_path"] = word["img_path"]
    session["guessed"] = []
    session["attempts"] = max_attempts
    session["total_attempts"] = max_attempts
    session["game_over"] = False
    session["won"] = False
    session["word_id"] = word["id_word"]
    session["word_difficulty"] = float(word["difficulty"])

    return redirect(url_for("hangman_play"))


@app.route("/hangman/play", methods=["GET", "POST"])
def hangman_play():
    if "word" not in session:
        return redirect(url_for("hangman"))

    word = session["word"]

    if request.method == "POST" and not session["game_over"]:
        letter = request.form["letter"].lower()
        guessed = session.get("guessed", [])
        if letter not in guessed:
            guessed.append(letter)
            session["guessed"] = guessed
            if letter not in word:
                session["attempts"] -= 1

        if all(l in session["guessed"] for l in word):
            session["game_over"] = True
            session["won"] = True
        if session["attempts"] <= 0:
            session["game_over"] = True

    if session["game_over"] and not session.get("leccion_result_recorded"):
        start = session.get("leccion_game_start", time.time())
        elapsed = round(time.time() - start, 1)
        won = session["won"]
        total_att = session["total_attempts"]
        remaining = session["attempts"]
        attempts_used = (total_att - remaining + 1) if won else total_att

        cursor_db = None
        try:
            cursor_db = con.cursor()
            game_id = get_game_id(cursor_db, "Hangman")
            if game_id:
                cursor_db.execute(
                    """INSERT INTO intentos
                       (fk_usuario, fk_palabra, fk_juego, correcto, tiempo, numero_intentos)
                       VALUES (%s, %s, %s, %s, %s, %s)""",
                    (session["user_id"], session["word_id"], game_id,
                     won, int(elapsed), attempts_used)
                )
                con.commit()
                update_user_skill(
                    session["user_id"],
                    float(session.get("word_difficulty", 0.5)),
                    won
                )
                if won:
                    increment_user_level(session["user_id"])
        except Exception as e:
            print(f"Error insertando intento Hangman: {e}")
            con.rollback()
        finally:
            if cursor_db:
                cursor_db.close()

        if session.get("leccion_mode"):
            session["leccion_results"].append({
                "game": "Ahorcado",
                "result": "Ganado" if won else "Perdido",
                "attempts_used": attempts_used,
                "total_attempts": total_att,
                "time": elapsed,
            })
        session["leccion_result_recorded"] = True
        session.modified = True

    display_word = " ".join(l if l in session["guessed"] else "_" for l in word)

    return render_template(
        "hangman.html",
        display_word=display_word,
        attempts=session["attempts"],
        game_over=session["game_over"],
        won=session["won"],
        word=word,
        img_path=session["img_path"],
        usuario=session["usuario"],
        leccion_mode=session.get("leccion_mode", False)
    )


@app.route("/hangman/surrender")
def hangman_surrender():
    session["game_over"] = True
    session["won"] = False
    return redirect(url_for("hangman_play"))


# ── MATCH ─────────────────────────────────────────────────────────

@app.route("/match")
def match():
    if "usuario" not in session:
        flash("Inicia sesión primero", "error")
        return redirect("/")

    # En modo lección, recuperar palabras pre-asignadas
    if session.get("leccion_mode") and "leccion_word_ids" in session:
        pre_ids = session["leccion_word_ids"].get("match", [])
        chosen_words = [get_word_by_id(wid) for wid in pre_ids]
        chosen_words = [w for w in chosen_words if w]  # filtrar None
    else:
        chosen_words = []

    # Completar con selección adaptativa si faltan palabras
    if len(chosen_words) < 3:
        used = {w["id_word"] for w in chosen_words}
        while len(chosen_words) < 3:
            word = select_adaptive_word(session["user_id"], exclude_ids=used)
            if not word:
                word = random_word_excluding(exclude_ids=used)
            if not word:
                break
            chosen_words.append(word)
            used.add(word["id_word"])

    words = [
        {
            "id_word": w["id_word"],
            "spelling": w["spelling"],
            "meaning": w["meaning"],
            "difficulty": float(w["difficulty"]),
        }
        for w in chosen_words
    ]
    session["match_words"] = words
    session["match_difficulties"] = [w["difficulty"] for w in words]
    return redirect(url_for("match_play"))


@app.route("/match/play", methods=["GET", "POST"])
def match_play():
    if "match_words" not in session:
        return redirect(url_for("match"))

    words = session["match_words"]

    if request.method == "POST":
        score = 0
        results = []
        for word in words:
            selected = request.form.get(str(word["id_word"]))
            correct = word["meaning"]
            is_correct = selected == correct
            if is_correct:
                score += 1
            results.append({
                "spelling": word["spelling"],
                "correct": correct,
                "selected": selected,
                "is_correct": is_correct,
                "id_word": word["id_word"],
                "difficulty": word["difficulty"],
            })

        start = session.get("leccion_game_start", time.time())
        elapsed = round(time.time() - start, 1)

        cursor_db = None
        try:
            cursor_db = con.cursor()
            game_id = get_game_id(cursor_db, "Match")
            if game_id:
                for w, r in zip(words, results):
                    cursor_db.execute(
                        """INSERT INTO intentos
                           (fk_usuario, fk_palabra, fk_juego, correcto, tiempo, numero_intentos)
                           VALUES (%s, %s, %s, %s, %s, %s)""",
                        (session["user_id"], w["id_word"], game_id,
                         r["is_correct"], int(elapsed), 1)
                    )
                    update_user_skill(
                        session["user_id"], w["difficulty"], r["is_correct"]
                    )
                    if r["is_correct"]:
                        increment_user_level(session["user_id"])
                con.commit()
        except Exception as e:
            print(f"Error insertando intentos Match: {e}")
            con.rollback()
        finally:
            if cursor_db:
                cursor_db.close()

        if session.get("leccion_mode"):
            session["leccion_results"].append({
                "game": "Emparejar",
                "result": f"{score}/{len(words)} correctas",
                "score": score,
                "total": len(words),
                "time": elapsed,
            })
            session["leccion_result_recorded"] = True
            session.modified = True

        session.pop("match_words", None)
        return render_template(
            "match_result.html",
            results=results,
            score=score,
            total=len(words),
            usuario=session["usuario"],
            leccion_mode=session.get("leccion_mode", False)
        )

    meanings = [w["meaning"] for w in words]
    random.shuffle(meanings)
    return render_template(
        "match.html",
        words=words,
        meanings=meanings,
        usuario=session["usuario"],
        leccion_mode=session.get("leccion_mode", False)
    )


# ── QUIZ ──────────────────────────────────────────────────────────

@app.route("/quiz")
def quiz():
    if "usuario" not in session:
        flash("Inicia sesión primero", "error")
        return redirect("/")

    # En modo lección, usar la palabra pre-asignada
    if session.get("leccion_mode") and "leccion_word_ids" in session:
        wid = session["leccion_word_ids"].get("quiz")
        correct_word = get_word_by_id(wid) if wid else None
    else:
        correct_word = select_adaptive_word(session["user_id"])

    if not correct_word:
        correct_word = random_word()
    if not correct_word:
        flash("No hay palabras disponibles", "error")
        return redirect(url_for("dashboard"))

    part = correct_word["part_of_speech"]
    cursor = con.cursor(dictionary=True)
    cursor.execute(
        """SELECT * FROM words
           WHERE part_of_speech = %s AND id_word != %s
           ORDER BY RAND() LIMIT 2""",
        (part, correct_word["id_word"])
    )
    wrong_words = cursor.fetchall()
    cursor.close()

    options = [correct_word] + wrong_words
    random.shuffle(options)

    session["quiz_correct"] = correct_word["id_word"]
    session["quiz_option_ids"] = [opt["id_word"] for opt in options]
    session["quiz_word_id"] = correct_word["id_word"]
    session["quiz_word_difficulty"] = float(correct_word["difficulty"])

    return render_template(
        "quiz.html",
        meaning=correct_word["meaning"],
        options=options,
        answered=False,
        usuario=session["usuario"],
        leccion_mode=session.get("leccion_mode", False)
    )


@app.route("/quiz/answer", methods=["POST"])
def quiz_answer():
    selected = int(request.form.get("option"))
    correct = session.get("quiz_correct")
    is_correct = selected == correct

    cursor = con.cursor(dictionary=True)
    option_ids = session.get("quiz_option_ids", [])
    placeholders = ", ".join(["%s"] * len(option_ids))
    cursor.execute(
        f"SELECT id_word, spelling FROM words WHERE id_word IN ({placeholders})",
        tuple(option_ids)
    )
    words = cursor.fetchall()
    cursor.close()

    word_map = {w["id_word"]: w for w in words}
    options = [word_map[i] for i in option_ids if i in word_map]

    start = session.get("leccion_game_start", time.time())
    elapsed = round(time.time() - start, 1)

    cursor_db = None
    try:
        cursor_db = con.cursor()
        game_id = get_game_id(cursor_db, "Quiz")
        if game_id:
            word_id = session.get("quiz_word_id")
            difficulty = float(session.get("quiz_word_difficulty", 0.5))
            cursor_db.execute(
                """INSERT INTO intentos
                   (fk_usuario, fk_palabra, fk_juego, correcto, tiempo, numero_intentos)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (session["user_id"], word_id, game_id,
                 is_correct, int(elapsed), 1)
            )
            con.commit()
            update_user_skill(session["user_id"], difficulty, is_correct)
            if is_correct:
                increment_user_level(session["user_id"])
    except Exception as e:
        print(f"Error insertando intento Quiz: {e}")
        con.rollback()
    finally:
        if cursor_db:
            cursor_db.close()

    if session.get("leccion_mode"):
        session["leccion_results"].append({
            "game": "Quiz",
            "result": "Correcto" if is_correct else "Incorrecto",
            "attempts": 1,
            "time": elapsed,
        })
        session["leccion_result_recorded"] = True
        session.modified = True

    return render_template(
        "quiz.html",
        meaning=request.form.get("meaning"),
        options=options,
        answered=True,
        selected=selected,
        correct=correct,
        is_correct=is_correct,
        usuario=session["usuario"],
        leccion_mode=session.get("leccion_mode", False)
    )


# ── UNSCRAMBLE ────────────────────────────────────────────────────

@app.route("/unscramble")
def unscramble():
    if "usuario" not in session:
        flash("Inicia sesión primero", "error")
        return redirect("/")

    # En modo lección, usar la palabra pre-asignada
    if session.get("leccion_mode") and "leccion_word_ids" in session:
        wid = session["leccion_word_ids"].get("unscramble")
        word = get_word_by_id(wid) if wid else None
    else:
        word = select_adaptive_word(session["user_id"])

    if not word:
        word = random_word()
    if not word:
        flash("No hay palabras disponibles", "error")
        return redirect(url_for("dashboard"))

    letters = list(word["spelling"])
    random.shuffle(letters)

    wlen = word["wlen"]
    attempts = math.ceil(math.log(wlen + 1) * 2)

    session["uns_word"] = word["spelling"]
    session["uns_meaning"] = word["meaning"]
    session["uns_attempts"] = attempts
    session["uns_initial_attempts"] = attempts
    session["uns_word_id"] = word["id_word"]
    session["uns_word_difficulty"] = float(word["difficulty"])

    return render_template(
        "unscramble.html",
        letters=letters,
        attempts=attempts,
        result=None,
        usuario=session["usuario"],
        leccion_mode=session.get("leccion_mode", False)
    )


@app.route("/unscramble/check", methods=["POST"])
def unscramble_check():
    user_word = request.form.get("user_word")
    correct_word = session.get("uns_word")
    meaning = session.get("uns_meaning")
    attempts = session.get("uns_attempts")

    if user_word.lower() == correct_word.lower():
        result = "correct"
    else:
        attempts -= 1
        session["uns_attempts"] = attempts
        result = "retry" if attempts > 0 else "fail"

    if result in ("correct", "fail"):
        start = session.get("leccion_game_start", time.time())
        elapsed = round(time.time() - start, 1)
        total_att = session.get("uns_initial_attempts", attempts)
        remaining = session.get("uns_attempts", 0)
        is_correct = result == "correct"
        attempts_used = (total_att - remaining + 1) if is_correct else total_att

        cursor_db = None
        try:
            cursor_db = con.cursor()
            game_id = get_game_id(cursor_db, "Word Unscramble")
            if game_id:
                word_id = session.get("uns_word_id")
                difficulty = float(session.get("uns_word_difficulty", 0.5))
                cursor_db.execute(
                    """INSERT INTO intentos
                       (fk_usuario, fk_palabra, fk_juego, correcto, tiempo, numero_intentos)
                       VALUES (%s, %s, %s, %s, %s, %s)""",
                    (session["user_id"], word_id, game_id,
                     is_correct, int(elapsed), attempts_used)
                )
                con.commit()
                update_user_skill(session["user_id"], difficulty, is_correct)
                if is_correct:
                    increment_user_level(session["user_id"])
        except Exception as e:
            print(f"Error insertando intento Unscramble: {e}")
            con.rollback()
        finally:
            if cursor_db:
                cursor_db.close()

        if session.get("leccion_mode"):
            session["leccion_results"].append({
                "game": "Palabra Revuelta",
                "result": "Correcto" if is_correct else "Fallido",
                "attempts_used": attempts_used,
                "total_attempts": total_att,
                "time": elapsed,
            })
            session["leccion_result_recorded"] = True
            session.modified = True

    letters = list(correct_word)
    random.shuffle(letters)

    return render_template(
        "unscramble.html",
        letters=letters,
        attempts=session["uns_attempts"],
        result=result,
        correct_word=correct_word,
        meaning=meaning,
        usuario=session["usuario"],
        leccion_mode=session.get("leccion_mode", False)
    )


# CERRAR SESIÓN
@app.route("/logout")
def logout():
    session.clear()
    flash("Sesión cerrada correctamente", "success")
    return redirect("/")


if __name__ == "__main__":
    app.run(debug=True)