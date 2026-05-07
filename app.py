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
    host=os.getenv("MYSQL_HOST"),
    user=os.getenv("MYSQL_USER"),
    password=os.getenv("MYSQL_PASSWORD"),
    database=os.getenv("MYSQL_DB")
)

# ----------------- FUNCIONES AUXILIARES -----------------

def get_game_id(cursor, game_name):
    """Obtiene el id_juego de la tabla juegos según su nombre."""
    cursor.execute("SELECT id_juego FROM juegos WHERE nombre = %s", (game_name,))
    row = cursor.fetchone()
    return row[0] if row else None

def select_adaptive_word(user_id):
    """
    Selecciona una palabra adaptada al nivel del usuario.
    Retorna un diccionario con los datos de la palabra (o None si falla la consulta).
    """
    cursor = con.cursor(dictionary=True)
    cursor.execute("SELECT skill FROM usuarios WHERE id_usuario = %s", (user_id,))
    user = cursor.fetchone()
    skill = float(user["skill"]) if user and user["skill"] is not None else 0.5

    lower = max(0.0, skill - 0.15)
    upper = min(1.0, skill + 0.15)

    query = """
        SELECT w.*,
               (1.0 - ABS(w.difficulty - %s)) * 
               CASE WHEN i.max_correcto = 1 THEN 0.5 ELSE 2.0 END AS weight
        FROM words w
        LEFT JOIN (
            SELECT fk_palabra, MAX(CASE WHEN correcto = 1 THEN 1 ELSE 0 END) as max_correcto
            FROM intentos
            WHERE fk_usuario = %s
            GROUP BY fk_palabra
        ) i ON w.id_word = i.fk_palabra
        WHERE w.difficulty BETWEEN %s AND %s
        ORDER BY weight * RAND() DESC
        LIMIT 1
    """
    cursor.execute(query, (skill, user_id, lower, upper))
    word = cursor.fetchone()
    cursor.close()

    if word:
        if "difficulty" in word:
            word["difficulty"] = float(word["difficulty"])
        return word
    return None

def random_word():
    """Fallback: selecciona una palabra aleatoria de la base de datos."""
    cursor = con.cursor(dictionary=True)
    cursor.execute("SELECT * FROM words ORDER BY RAND() LIMIT 1")
    word = cursor.fetchone()
    cursor.close()
    if word and "difficulty" in word:
        word["difficulty"] = float(word["difficulty"])
    return word

def update_user_skill(user_id, word_difficulty, success, alpha=0.1):
    """
    Actualiza el skill del usuario tras un intento.
    """
    word_difficulty = float(word_difficulty)
    cursor = con.cursor()
    cursor.execute("SELECT skill FROM usuarios WHERE id_usuario = %s", (user_id,))
    row = cursor.fetchone()
    if not row:
        cursor.close()
        return
    current_skill = float(row[0]) if row[0] is not None else 0.5
    if success:
        new_skill = current_skill + alpha * (word_difficulty - current_skill)
    else:
        new_skill = current_skill - alpha * (current_skill - word_difficulty)
    new_skill = max(0.0, min(1.0, new_skill))
    cursor.execute("UPDATE usuarios SET skill = %s WHERE id_usuario = %s", (new_skill, user_id))
    con.commit()
    cursor.close()

def increment_user_level(user_id, amount=0.1):
    """Aumenta el nivel del usuario en una cantidad fija por acierto."""
    cursor = con.cursor()
    cursor.execute("UPDATE usuarios SET nivel = nivel + %s WHERE id_usuario = %s", (amount, user_id))
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
        cursor.execute("SELECT id_usuario FROM usuarios WHERE nombre_usuario = %s", (nombre,))
        usuario_existente = cursor.fetchone()
        if usuario_existente:
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
        cursor.execute("SELECT id_usuario, nombre_usuario, contrasena_hash FROM usuarios WHERE nombre_usuario = %s", (nombre,))
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
    nivel_decimal = float(result[0]) if result and result[0] is not None else 0.0
    return nivel_decimal

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
    if "usuario" in session:
        nivel_decimal = obtener_nivel()
        nivel = int(nivel_decimal)
        return render_template("perfil.html",
                               usuario=session["usuario"],
                               nivel=nivel,
                               progreso=int((nivel_decimal - nivel) * 100),
                               nivel_siguiente=nivel + 1)
    flash("Por favor inicia sesión primero", "error")
    return redirect("/")

######## LECCIÓN RÁPIDA ########

@app.route("/leccion-rapida")
def leccion_rapida():
    if "usuario" not in session:
        flash("Inicia sesión primero", "error")
        return redirect("/")
    
    all_games = ['hangman', 'match', 'quiz', 'unscramble']
    k = random.choice([3, 4])
    games = random.sample(all_games, k=k)
    
    session['leccion_mode'] = True
    session['leccion_games'] = games
    session['leccion_index'] = 0
    session['leccion_results'] = []
    session['leccion_result_recorded'] = False
    
    first_game = games[0]
    session['leccion_game_start'] = time.time()
    if first_game == 'hangman':
        return redirect(url_for('hangman'))
    elif first_game == 'match':
        return redirect(url_for('match'))
    elif first_game == 'quiz':
        return redirect(url_for('quiz'))
    elif first_game == 'unscramble':
        return redirect(url_for('unscramble'))
    else:
        return redirect(url_for('dashboard'))

@app.route("/leccion/next")
def leccion_next():
    if not session.get("leccion_mode"):
        return redirect(url_for("dashboard"))
    
    session["leccion_index"] += 1
    games = session["leccion_games"]
    idx = session["leccion_index"]
    
    if idx >= len(games):
        return redirect(url_for("leccion_summary"))
    
    next_game = games[idx]
    session["leccion_result_recorded"] = False
    session["leccion_game_start"] = time.time()
    
    if next_game == 'hangman':
        return redirect(url_for('hangman'))
    elif next_game == 'match':
        return redirect(url_for('match'))
    elif next_game == 'quiz':
        return redirect(url_for('quiz'))
    elif next_game == 'unscramble':
        return redirect(url_for('unscramble'))
    else:
        return redirect(url_for("leccion_summary"))

@app.route("/leccion/cancel")
def leccion_cancel():
    for key in ["leccion_mode", "leccion_games", "leccion_index",
                "leccion_results", "leccion_result_recorded", "leccion_game_start"]:
        session.pop(key, None)
    return redirect(url_for("dashboard"))

@app.route("/leccion/summary")
def leccion_summary():
    if not session.get("leccion_mode"):
        return redirect(url_for("dashboard"))
    results = session.get("leccion_results", [])
    total_time = sum(r.get("time", 0) for r in results)
    return render_template("leccion_summary.html",
                           results=results,
                           total_time=round(total_time, 1),
                           usuario=session["usuario"])

@app.route("/leccion/finish")
def leccion_finish():
    for key in ["leccion_mode", "leccion_games", "leccion_index",
                "leccion_results", "leccion_result_recorded", "leccion_game_start"]:
        session.pop(key, None)
    return redirect(url_for("dashboard"))

######## ACTIVIDADES ########

@app.route("/hangman")
def hangman():
    word = select_adaptive_word(session["user_id"])
    if not word:
        word = random_word()
    if not word:
        flash("No hay palabras disponibles", "error")
        return redirect(url_for("dashboard"))

    session["word"] = word["spelling"].lower()
    session["meaning"] = word["meaning"]
    session["img_path"] = word["img_path"]
    session["guessed"] = []
    session["attempts"] = 3
    session["total_attempts"] = session["attempts"]
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
        elapsed = round(time.time() - start, 1) if start else 0
        won = session["won"]
        total_att = session["total_attempts"]
        remaining = session["attempts"]

        if won:
            attempts_used = (total_att - remaining) + 1
        else:
            attempts_used = total_att

        cursor_db = None
        try:
            cursor_db = con.cursor()
            game_id = get_game_id(cursor_db, "hangman")
            if game_id:
                word_id = session.get("word_id")
                cursor_db.execute(
                    """INSERT INTO intentos (fk_usuario, fk_palabra, fk_juego, correcto, tiempo, numero_intentos)
                       VALUES (%s, %s, %s, %s, %s, %s)""",
                    (session["user_id"], word_id, game_id, won, int(elapsed), attempts_used)
                )
                con.commit()
                difficulty = float(session.get("word_difficulty", 0.5))
                update_user_skill(session["user_id"], difficulty, won)
                if won:
                    increment_user_level(session["user_id"])   # <-- AQUÍ
        except Exception as e:
            print(f"Error insertando intento Hangman: {e}")
            con.rollback()
        finally:
            if cursor_db:
                cursor_db.close()

        if session.get("leccion_mode"):
            result = {
                "game": "Ahorcado",
                "result": "Ganado" if won else "Perdido",
                "attempts_used": attempts_used,
                "total_attempts": total_att,
                "time": elapsed
            }
            session["leccion_results"].append(result)
        session["leccion_result_recorded"] = True
        session.modified = True

    display_word = ""
    for l in word:
        if l in session["guessed"]:
            display_word += l + " "
        else:
            display_word += "_ "

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

@app.route("/match")
def match():
    chosen_words = []
    for _ in range(3):
        word = select_adaptive_word(session["user_id"])
        if word and word["id_word"] not in [w["id_word"] for w in chosen_words]:
            chosen_words.append(word)
    if len(chosen_words) < 3:
        cursor = con.cursor(dictionary=True)
        needed = 3 - len(chosen_words)
        existing_ids = tuple([w["id_word"] for w in chosen_words]) if chosen_words else (-1,)
        placeholders = ','.join(['%s'] * len(existing_ids))
        cursor.execute(
            f"SELECT id_word, spelling, meaning, difficulty FROM words WHERE id_word NOT IN ({placeholders}) ORDER BY RAND() LIMIT %s",
            (*existing_ids, needed)
        )
        extra_words = cursor.fetchall()
        cursor.close()
        for w in extra_words:
            w["difficulty"] = float(w["difficulty"])
        chosen_words.extend(extra_words)
    words = [{"id_word": w["id_word"], "spelling": w["spelling"], "meaning": w["meaning"], "difficulty": float(w["difficulty"])} for w in chosen_words]
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
                "difficulty": word["difficulty"]
            })

        start = session.get("leccion_game_start", time.time())
        elapsed = round(time.time() - start, 1) if start else 0

        cursor_db = None
        try:
            cursor_db = con.cursor()
            game_id = get_game_id(cursor_db, "match")
            if game_id:
                for w, r in zip(words, results):
                    is_word_correct = r["is_correct"]
                    cursor_db.execute(
                        """INSERT INTO intentos (fk_usuario, fk_palabra, fk_juego, correcto, tiempo, numero_intentos)
                           VALUES (%s, %s, %s, %s, %s, %s)""",
                        (session["user_id"], w["id_word"], game_id, is_word_correct, int(elapsed), 1)
                    )
                    update_user_skill(session["user_id"], w["difficulty"], is_word_correct)
                    if is_word_correct:
                        increment_user_level(session["user_id"])   # <-- AQUÍ
                con.commit()
        except Exception as e:
            print(f"Error insertando intentos Match: {e}")
            con.rollback()
        finally:
            if cursor_db:
                cursor_db.close()

        if session.get("leccion_mode"):
            result_data = {
                "game": "Emparejar",
                "result": f"{score}/{len(words)} correctas",
                "score": score,
                "total": len(words),
                "time": elapsed
            }
            session["leccion_results"].append(result_data)
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

@app.route("/quiz")
def quiz():
    correct_word = select_adaptive_word(session["user_id"])
    if not correct_word:
        correct_word = random_word()
    if not correct_word:
        flash("No hay palabras disponibles", "error")
        return redirect(url_for("dashboard"))

    part = correct_word["part_of_speech"]
    cursor = con.cursor(dictionary=True)
    cursor.execute("""
        SELECT * FROM words 
        WHERE part_of_speech = %s 
        AND id_word != %s
        ORDER BY RAND() 
        LIMIT 2
    """, (part, correct_word["id_word"]))
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
    options = [word_map[id] for id in option_ids if id in word_map]

    start = session.get("leccion_game_start", time.time())
    elapsed = round(time.time() - start, 1) if start else 0

    cursor_db = None
    try:
        cursor_db = con.cursor()
        game_id = get_game_id(cursor_db, "quiz")
        if game_id:
            word_id = session.get("quiz_word_id")
            difficulty = float(session.get("quiz_word_difficulty", 0.5))
            cursor_db.execute(
                """INSERT INTO intentos (fk_usuario, fk_palabra, fk_juego, correcto, tiempo, numero_intentos)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (session["user_id"], word_id, game_id, is_correct, int(elapsed), 1)
            )
            con.commit()
            update_user_skill(session["user_id"], difficulty, is_correct)
            if is_correct:
                increment_user_level(session["user_id"])    # <-- AQUÍ
    except Exception as e:
        print(f"Error insertando intento Quiz: {e}")
        con.rollback()
    finally:
        if cursor_db:
            cursor_db.close()

    if session.get("leccion_mode"):
        result_data = {
            "game": "Quiz",
            "result": "Correcto" if is_correct else "Incorrecto",
            "attempts": 1,
            "time": elapsed
        }
        session["leccion_results"].append(result_data)
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

@app.route("/unscramble")
def unscramble():
    word = select_adaptive_word(session["user_id"])
    if not word:
        word = random_word()
    if not word:
        flash("No hay palabras disponibles", "error")
        return redirect(url_for("dashboard"))

    letters = list(word["spelling"])
    random.shuffle(letters)

    attempts = math.ceil(len(word["spelling"]) / 3)

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
        if attempts <= 0:
            result = "fail"
        else:
            result = "retry"

    if result in ("correct", "fail"):
        start = session.get("leccion_game_start", time.time())
        elapsed = round(time.time() - start, 1) if start else 0
        total_att = session.get("uns_initial_attempts", attempts)
        remaining = session.get("uns_attempts", 0)

        if result == "correct":
            attempts_used = (total_att - remaining) + 1
        else:
            attempts_used = total_att

        cursor_db = None
        try:
            cursor_db = con.cursor()
            game_id = get_game_id(cursor_db, "unscramble")
            if game_id:
                word_id = session.get("uns_word_id")
                difficulty = float(session.get("uns_word_difficulty", 0.5))
                is_correct = (result == "correct")
                cursor_db.execute(
                    """INSERT INTO intentos (fk_usuario, fk_palabra, fk_juego, correcto, tiempo, numero_intentos)
                       VALUES (%s, %s, %s, %s, %s, %s)""",
                    (session["user_id"], word_id, game_id, is_correct, int(elapsed), attempts_used)
                )
                con.commit()
                update_user_skill(session["user_id"], difficulty, is_correct)
                if is_correct:
                    increment_user_level(session["user_id"])   # <-- AQUÍ
        except Exception as e:
            print(f"Error insertando intento Unscramble: {e}")
            con.rollback()
        finally:
            if cursor_db:
                cursor_db.close()

        if session.get("leccion_mode"):
            result_data = {
                "game": "Palabra Revuelta",
                "result": "Correcto" if result == "correct" else "Fallido",
                "attempts_used": attempts_used,
                "total_attempts": total_att,
                "time": elapsed
            }
            session["leccion_results"].append(result_data)
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