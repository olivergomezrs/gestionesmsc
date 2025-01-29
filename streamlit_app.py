import streamlit as st
import sqlite3
import hashlib

# Configuración de la base de datos
conn = sqlite3.connect('gestiones.db')
cursor = conn.cursor()

# Crear tablas si no existen
cursor.execute('''CREATE TABLE IF NOT EXISTS usuarios
                  (id INTEGER PRIMARY KEY AUTOINCREMENT,
                   username TEXT UNIQUE NOT NULL,
                   password TEXT NOT NULL)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS gestiones
                  (id INTEGER PRIMARY KEY AUTOINCREMENT,
                   titulo TEXT NOT NULL,
                   descripcion TEXT NOT NULL,
                   estado TEXT NOT NULL,
                   usuario_id INTEGER,
                   FOREIGN KEY (usuario_id) REFERENCES usuarios(id))''')
conn.commit()

# Función para hashear contraseñas
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Función para verificar credenciales
def verificar_credenciales(username, password):
    cursor.execute("SELECT * FROM usuarios WHERE username = ? AND password = ?", (username, hash_password(password)))
    return cursor.fetchone() is not None

# Función para registrar nuevo usuario
def registrar_usuario(username, password):
    try:
        cursor.execute("INSERT INTO usuarios (username, password) VALUES (?, ?)", (username, hash_password(password)))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False

# Inicializar estado de sesión
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

# Interfaz de login/registro
if not st.session_state.logged_in:
    st.title("Portal de Gestiones Ciudadanas")
    tab1, tab2 = st.tabs(["Iniciar Sesión", "Registrarse"])
    
    with tab1:
        username = st.text_input("Usuario")
        password = st.text_input("Contraseña", type="password")
        if st.button("Iniciar Sesión"):
            if verificar_credenciales(username, password):
                st.session_state.logged_in = True
                st.session_state.username = username
                st.rerun()
            else:
                st.error("Credenciales incorrectas")
    
    with tab2:
        new_username = st.text_input("Nuevo Usuario")
        new_password = st.text_input("Nueva Contraseña", type="password")
        if st.button("Registrarse"):
            if registrar_usuario(new_username, new_password):
                st.success("Usuario registrado con éxito")
            else:
                st.error("El nombre de usuario ya existe")

# Interfaz principal después del login
if st.session_state.logged_in:
    st.title(f"Bienvenido, {st.session_state.username}")
    
    # Formulario para ingresar una nueva gestión
    st.header("Ingresar Nueva Gestión")
    titulo = st.text_input("Título de la Gestión")
    descripcion = st.text_area("Descripción de la Gestión")
    estado = st.selectbox("Estado de la Gestión", ["Pendiente", "En Proceso", "Completada"])

    if st.button("Guardar Gestión"):
        if titulo and descripcion:
            cursor.execute("INSERT INTO gestiones (titulo, descripcion, estado, usuario_id) VALUES (?, ?, ?, (SELECT id FROM usuarios WHERE username = ?))", 
                           (titulo, descripcion, estado, st.session_state.username))
            conn.commit()
            st.success("Gestión guardada exitosamente!")
        else:
            st.error("Por favor, complete todos los campos.")

    # Mostrar las gestiones existentes
    st.header("Gestiones Existentes")
    cursor.execute("SELECT g.id, g.titulo, g.descripcion, g.estado FROM gestiones g JOIN usuarios u ON g.usuario_id = u.id WHERE u.username = ?", (st.session_state.username,))
    gestiones = cursor.fetchall()

    for gestion in gestiones:
        st.subheader(f"Gestión ID: {gestion[0]}")
        st.write(f"**Título:** {gestion[1]}")
        st.write(f"**Descripción:** {gestion[2]}")
        st.write(f"**Estado:** {gestion[3]}")

    if st.button("Cerrar Sesión"):
        st.session_state.logged_in = False
        st.rerun()

# Cerrar conexión
conn.close()
