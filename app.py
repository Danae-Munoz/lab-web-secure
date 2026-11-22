from flask import Flask, request, render_template_string, redirect, session, abort
from werkzeug.security import check_password_hash
import sqlite3
import secrets
import os

app = Flask(__name__)

# CORRECCIÓN: la sesión pasa a ser una cookie firmada por el servidor (no texto plano).
# La clave se toma del entorno; si no existe se genera una aleatoria al iniciar.
app.secret_key = os.environ.get('SECRET_KEY') or secrets.token_hex(32)
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,    # CORRECCIÓN: JavaScript no puede leer la cookie
    SESSION_COOKIE_SAMESITE='Lax',   # CORRECCIÓN: el navegador no la envía en POST de otros sitios (mitiga CSRF)
    SESSION_COOKIE_SECURE=os.environ.get('COOKIE_SECURE') == '1',  # activar con HTTPS
)


def db_query(query, params=()):
    """Función auxiliar para ejecutar queries (CORREGIDA: consultas parametrizadas)"""
    conn = sqlite3.connect('vulnerable.db')
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.cursor()
        # CORRECCIÓN SQLi: los valores viajan separados de la sentencia SQL
        cursor.execute(query, params)
        result = cursor.fetchall()
        conn.commit()
        return result
    finally:
        conn.close()


@app.after_request
def cabeceras_de_seguridad(resp):
    # CORRECCIÓN: cabeceras de seguridad HTTP
    resp.headers['Content-Security-Policy'] = "default-src 'self'; frame-ancestors 'none'; form-action 'self'"
    resp.headers['X-Frame-Options'] = 'DENY'
    resp.headers['X-Content-Type-Options'] = 'nosniff'
    resp.headers['Referrer-Policy'] = 'no-referrer'
    resp.headers['Cache-Control'] = 'no-store'
    return resp


# --- LOGIN (corregido: SQLi) ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = request.form.get('username', '')
        pw = request.form.get('password', '')

        # CORRECCIÓN SQLi: consulta parametrizada y contraseña comparada contra su hash
        usuarios = db_query("SELECT * FROM usuarios WHERE username = ?", (user,))

        if usuarios and check_password_hash(usuarios[0]['password'], pw):
            session.clear()
            session['user'] = usuarios[0]['username']
            session['csrf_token'] = secrets.token_hex(16)  # CORRECCIÓN CSRF: token por sesión
            return redirect('/dashboard')
        return "<h3>Acceso denegado</h3><a href='/login'>Volver</a>", 401

    return '''
        <h2>Login del Sistema Académico</h2>
        <form method="post">
            Usuario: <input type="text" name="username"><br>
            Password: <input type="password" name="password"><br>
            <input type="submit" value="Ingresar">
        </form>
    '''


# --- DASHBOARD (corregido: XSS y CSRF) ---
@app.route('/dashboard')
def dashboard():
    username = session.get('user')
    if not username:
        return redirect('/login')

    filas = db_query("SELECT * FROM usuarios WHERE username = ?", (username,))
    if not filas:
        session.clear()
        return redirect('/login')
    datos = filas[0]

    # CORRECCIÓN XSS: los datos se pasan como variables de la plantilla ({{ }}),
    # Jinja2 los escapa automáticamente. Ya no se incrustan con f-strings.
    html = """
    <h1>Panel de {{ username }}</h1>
    <p><b>Rol:</b> {{ rol }}</p>
    <p><b>Biografía:</b> {{ bio }}</p>
    <hr>
    <h3>Actualizar Biografía</h3>
    <form action="/update_bio" method="POST">
        <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
        <input type="text" name="nueva_bio" placeholder="Escribe algo...">
        <input type="submit" value="Guardar Cambios">
    </form>
    <br><a href="/logout">Cerrar Sesión</a>
    """
    return render_template_string(
        html,
        username=datos['username'],
        rol=datos['rol'],
        bio=datos['bio'],
        csrf_token=session['csrf_token'],
    )


@app.route('/update_bio', methods=['POST'])
def update_bio():
    username = session.get('user')
    if not username:
        return redirect('/login')

    # CORRECCIÓN CSRF: se exige el token generado al iniciar sesión
    token = request.form.get('csrf_token', '')
    if not secrets.compare_digest(token, session.get('csrf_token', '')):
        abort(403)

    nueva_bio = request.form.get('nueva_bio', '')
    db_query("UPDATE usuarios SET bio = ? WHERE username = ?", (nueva_bio, username))
    return redirect('/dashboard')


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')


@app.route('/')
def home():
    return redirect('/login')


if __name__ == '__main__':
    # CORRECCIÓN: debug desactivado (el modo debug expone un depurador interactivo)
    app.run(port=5000, debug=False)
