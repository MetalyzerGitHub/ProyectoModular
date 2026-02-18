import os
from flask import Flask, render_template, request, redirect, session, flash, url_for
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")

con=mysql.connector.connect(
    host=os.getenv("MYSQL_HOST"),
    user=os.getenv("MYSQL_USER"),
    password=os.getenv("MYSQL_PASSWORD"),
    database=os.getenv("MYSQL_DB")
)

###     PRUEBA RAPIDA QUITAR DESPUES
try:
    cur = con.cursor()
    print("Conexión exitosa")
except Exception as e:
    print("Error real:", e)

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

######## DASHBOARD

@app.route("/dashboard")
def dashboard():
    if "usuario" in session:
        return render_template("dashboard.html", usuario=session["usuario"])
    flash("Por favor inicia sesión primero", "error")
    return redirect("/")

# Placeholder

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

# Placeholder routes for activities
@app.route("/hangman")
def hangman():
    if "usuario" in session:
        return render_template("hangman.html", usuario=session["usuario"])
    return redirect("/")

@app.route("/match")
def match():
    if "usuario" in session:
        return render_template("match.html", usuario=session["usuario"])
    return redirect("/")

@app.route("/quiz")
def quiz():
    if "usuario" in session:
        return render_template("quiz.html", usuario=session["usuario"])
    return redirect("/")

@app.route("/scramble")
def scramble():
    if "usuario" in session:
        return render_template("scramble.html", usuario=session["usuario"])
    return redirect("/")

# CERRAR SESION

@app.route("/logout")
def logout():
    session.clear()
    flash("Sesión cerrada correctamente", "success")
    return redirect("/")

# MAIN

if __name__ == "__main__":
    app.run(debug=True)
