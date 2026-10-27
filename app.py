import os
import sqlite3
from flask import Flask, render_template, request, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-only-change-me')
DB_NAME = 'foro_colombia.db'

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.executescript('''
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                departamento TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS publicaciones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id INTEGER NOT NULL,
                titulo TEXT NOT NULL,
                contenido TEXT NOT NULL,
                creado_en DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
            );
            CREATE TABLE IF NOT EXISTS comentarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                publicacion_id INTEGER NOT NULL,
                usuario_id INTEGER NOT NULL,
                contenido TEXT NOT NULL,
                creado_en DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (publicacion_id) REFERENCES publicaciones(id),
                FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
            );
            CREATE TABLE IF NOT EXISTS reacciones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                publicacion_id INTEGER NOT NULL,
                usuario_id INTEGER NOT NULL,
                tipo_voto INTEGER CHECK(tipo_voto IN (1, -1)),
                UNIQUE(publicacion_id, usuario_id),
                FOREIGN KEY (publicacion_id) REFERENCES publicaciones(id),
                FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
            );
        ''')

init_db()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/registro', methods=['POST'])
def registro():
    data = request.get_json()
    nombre = data.get('nombre')
    email = data.get('email')
    password = data.get('password')
    departamento = data.get('departamento')

    pwd_hash = generate_password_hash(password)
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO usuarios (nombre, email, password_hash, departamento) VALUES (?, ?, ?, ?)',
                (nombre, email, pwd_hash, departamento)
            )
            session['user_id'] = cursor.lastrowid
            session['user_name'] = nombre
        return jsonify({'status': 'ok', 'mensaje': 'Usuario registrado exitosamente'})
    except sqlite3.IntegrityError:
        return jsonify({'status': 'error', 'mensaje': 'El correo ya está registrado'}), 400

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    with get_db() as conn:
        user = conn.execute('SELECT * FROM usuarios WHERE email = ?', (email,)).fetchone()
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['user_name'] = user['nombre']
            return jsonify({'status': 'ok', 'mensaje': 'Sesión iniciada correctamente'})
    return jsonify({'status': 'error', 'mensaje': 'Credenciales inválidas'}), 401

@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'status': 'ok'})

@app.route('/api/publicaciones', methods=['GET', 'POST'])
def publicaciones():
    if request.method == 'POST':
        if 'user_id' not in session:
            return jsonify({'status': 'error', 'mensaje': 'Debes iniciar sesión'}), 401
        data = request.get_json()
        titulo = data.get('titulo')
        contenido = data.get('contenido')
        with get_db() as conn:
            conn.execute(
                'INSERT INTO publicaciones (usuario_id, titulo, contenido) VALUES (?, ?, ?)',
                (session['user_id'], titulo, contenido)
            )
        return jsonify({'status': 'ok'})

    with get_db() as conn:
        posts = conn.execute('''
            SELECT p.*, u.nombre as autor, u.departamento,
                   COALESCE(SUM(CASE WHEN r.tipo_voto = 1 THEN 1 ELSE 0 END), 0) as likes,
                   COALESCE(SUM(CASE WHEN r.tipo_voto = -1 THEN 1 ELSE 0 END), 0) as dislikes
            FROM publicaciones p
            JOIN usuarios u ON p.usuario_id = u.id
            LEFT JOIN reacciones r ON p.id = r.publicacion_id
            GROUP BY p.id
            ORDER BY p.creado_en DESC
        ''').fetchall()
        
        resultado = []
        for post in posts:
            comments = conn.execute('''
                SELECT c.*, u.nombre as autor FROM comentarios c
                JOIN usuarios u ON c.usuario_id = u.id
                WHERE c.publicacion_id = ? ORDER BY c.creado_en ASC
            ''', (post['id'],)).fetchall()
            
            p_dict = dict(post)
            p_dict['comentarios'] = [dict(c) for c in comments]
            resultado.append(p_dict)

    return jsonify({'posts': resultado, 'usuario_actual': session.get('user_name'), 'user_id': session.get('user_id')})

@app.route('/api/reaccion', methods=['POST'])
def reaccion():
    if 'user_id' not in session:
        return jsonify({'status': 'error', 'mensaje': 'Inicia sesión para votar'}), 401
    data = request.get_json()
    post_id = data.get('post_id')
    tipo_voto = data.get('tipo_voto')

    with get_db() as conn:
        conn.execute('''
            INSERT INTO reacciones (publicacion_id, usuario_id, tipo_voto)
            VALUES (?, ?, ?)
            ON CONFLICT(publicacion_id, usuario_id) DO UPDATE SET tipo_voto = excluded.tipo_voto
        ''', (post_id, session['user_id'], tipo_voto))
    return jsonify({'status': 'ok'})

@app.route('/api/comentar', methods=['POST'])
def comentar():
    if 'user_id' not in session:
        return jsonify({'status': 'error', 'mensaje': 'Inicia sesión para comentar'}), 401
    data = request.get_json()
    post_id = data.get('post_id')
    contenido = data.get('contenido')

    with get_db() as conn:
        conn.execute(
            'INSERT INTO comentarios (publicacion_id, usuario_id, contenido) VALUES (?, ?, ?)',
            (post_id, session['user_id'], contenido)
        )
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    app.run(debug=True, port=5000)