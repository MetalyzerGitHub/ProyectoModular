import os
from flask import Flask, render_template, request, redirect, session, flash, url_for
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
import random
import math


load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")

con=mysql.connector.connect(
    host=os.getenv("MYSQL_HOST"),
    user=os.getenv("MYSQL_USER"),
    password=os.getenv("MYSQL_PASSWORD"),
    database=os.getenv("MYSQL_DB")
)


################### RUTAS ###################

@app.route("/test-db")  ### PRUEBA DE CONEXION, QUITAR DESPUES
def test_db():
    try:
        cursor = con.cursor()
        cursor.execute("SHOW TABLES")
        tables=cursor.fetchall()
        cursor.close()
        return "Conexión a MySQL exitosa!"
    except Exception as e:
        return f"Error de conexión: {e}"

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
        
        # Verificar si ya existe
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

@app.route("/dashboard")
def dashboard():
    if "usuario" in session:
        return render_template("dashboard.html", usuario=session["usuario"])
    flash("Por favor inicia sesión primero", "error")
    return redirect("/")

# Perfil de usuario

@app.route("/perfil")
def perfil():
    if "usuario" in session:
        return render_template("perfil.html", usuario=session["usuario"])
    flash("Por favor inicia sesión primero", "error")
    return redirect("/")

@app.route("/leccion-rapida")
def leccion_rapida():
    if "usuario" in session:
        # Aquí puedes implementar lógica para seleccionar una lección aleatoria
        flash("¡Comenzando lección rápida!", "success")
        return redirect("/dashboard")  # O redirigir a una lección específica
    return redirect("/")

######## ACTIVIDADES ########

@app.route("/hangman")
def hangman():
    cursor = con.cursor(dictionary=True)

    cursor.execute("SELECT * FROM words WHERE id_word < 10 ORDER BY RAND() LIMIT 1")
    #cursor.execute("SELECT * FROM words WHERE id_word =1")
    word = cursor.fetchone()

    cursor.close()

    # Guardar estado en sesión
    session["word"] = word["spelling"].lower()
    session["meaning"] = word["meaning"]
    session["img_path"] = word["img_path"]
    session["guessed"] = []
    session["attempts"] = 6
    session["game_over"] = False
    session["won"] = False

    #if not os.path.exists(session["img_path"]):
    #    session["img_path"] = "images/Placeholder.webp"

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
            session["guessed"] = guessed   # <- REASIGNAR


            if letter not in word:
                session["attempts"] -= 1

        # Verificar victoria
        if all(l in session["guessed"] for l in word):
            session["game_over"] = True
            session["won"] = True

        # Verificar derrota
        if session["attempts"] <= 0:
            session["game_over"] = True

    # Construir palabra mostrada
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
        usuario=session["usuario"]
    )

@app.route("/hangman/surrender")
def hangman_surrender():
    session["game_over"] = True
    session["won"] = False
    return redirect(url_for("hangman_play"))


@app.route("/match")
def match():
    cursor = con.cursor(dictionary=True)

    cursor.execute("SELECT id_word, spelling, meaning FROM words ORDER BY RAND() LIMIT 3")
    words = cursor.fetchall()

    cursor.close()

    # Guardar respuestas correctas
    session["match_words"] = words

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
                "is_correct": is_correct
            })

        session.pop("match_words", None)

        return render_template(
            "match_result.html",
            results=results,
            score=score,
            total=len(words),
            usuario=session["usuario"]
        )

    # Mezclar significados
    meanings = [w["meaning"] for w in words]
    random.shuffle(meanings)

    return render_template(
        "match.html",
        words=words,
        meanings=meanings,
        usuario=session["usuario"]
    )

@app.route("/quiz")
def quiz():
    cursor = con.cursor(dictionary=True)

    # 1 palabra correcta
    cursor.execute("SELECT * FROM words ORDER BY RAND() LIMIT 1")
    correct_word = cursor.fetchone()

    part = correct_word["part_of_speech"]

    # 2 palabras incorrectas de la misma categoría
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

    return render_template(
        "quiz.html",
        meaning=correct_word["meaning"],
        options=options,
        answered=False,
        usuario=session["usuario"]
    )

@app.route("/quiz/answer", methods=["POST"])
def quiz_answer():
    selected = int(request.form.get("option"))
    correct = session.get("quiz_correct")

    is_correct = selected == correct

    # Volvemos a reconstruir las opciones
    cursor = con.cursor(dictionary=True)

    cursor.execute("SELECT id_word, spelling FROM words WHERE id_word = %s", (correct,))
    correct_word = cursor.fetchone()

    cursor.execute("""
        SELECT id_word, spelling FROM words 
        WHERE part_of_speech = (
            SELECT part_of_speech FROM words WHERE id_word = %s
        )
        AND id_word != %s
        ORDER BY RAND()
        LIMIT 2
    """, (correct, correct))

    wrong_words = cursor.fetchall()

    cursor.close()

    options = [correct_word] + wrong_words
    random.shuffle(options)

    return render_template(
        "quiz.html",
        meaning=request.form.get("meaning"),
        options=options,
        answered=True,
        selected=selected,
        correct=correct,
        is_correct=is_correct,
        usuario=session["usuario"]
    )


@app.route("/unscramble")
def unscramble():

    cursor = con.cursor(dictionary=True)

    cursor.execute("SELECT * FROM words ORDER BY RAND() LIMIT 1")
    word = cursor.fetchone()

    cursor.close()

    letters = list(word["spelling"])
    random.shuffle(letters)

    attempts = math.ceil(len(word["spelling"]) / 3)

    session["uns_word"] = word["spelling"]
    session["uns_meaning"] = word["meaning"]
    session["uns_attempts"] = attempts

    return render_template(
        "unscramble.html",
        letters=letters,
        attempts=attempts,
        result=None,
        usuario=session["usuario"]
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

    letters = list(correct_word)
    random.shuffle(letters)

    return render_template(
        "unscramble.html",
        letters=letters,
        attempts=session["uns_attempts"],
        result=result,
        correct_word=correct_word,
        meaning=meaning, 
        usuario=session["usuario"]
    )

# CERRAR SESION

@app.route("/logout")
def logout():
    session.clear()
    flash("Sesión cerrada correctamente", "success")
    return redirect("/")

# MAIN

if __name__ == "__main__":
    app.run(debug=True)
