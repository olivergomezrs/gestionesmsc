pip install folium geopy streamlit-folium

import streamlit as st
import sqlite3
import hashlib
from datetime import datetime
import folium
from streamlit_folium import folium_static
from geopy.geocoders import Nominatim

# Configuración de la base de datos
conn = sqlite3.connect('gestiones.db')
cursor = conn.cursor()

# Crear tablas si no existen
cursor.execute('''CREATE TABLE IF NOT EXISTS usuarios
                  (id INTEGER PRIMARY KEY AUTOINCREMENT,
                   username TEXT UNIQUE NOT NULL,
                   password TEXT NOT NULL)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS secretarias
                  (id INTEGER PRIMARY KEY AUTOINCREMENT,
                   nombre TEXT UNIQUE NOT NULL)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS tipos_gestion
                  (id INTEGER PRIMARY KEY AUTOINCREMENT,
                   nombre TEXT NOT NULL,
                   secretaria_id INTEGER,
                   FOREIGN KEY (secretaria_id) REFERENCES secretarias(id))''')

cursor.execute('''CREATE TABLE IF NOT EXISTS gestiones
                  (id INTEGER PRIMARY KEY AUTOINCREMENT,
                   titulo TEXT,
                   descripcion TEXT,
                   estado TEXT,
                   usuario_id INTEGER,
                   fecha_ingreso TEXT,
                   domicilio TEXT,
                   latitud REAL,
                   longitud REAL,
                   secretaria_id INTEGER,
                   tipo_gestion_id INTEGER,
                   FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
                   FOREIGN KEY (secretaria_id) REFERENCES secretarias(id),
                   FOREIGN KEY (tipo_gestion_id) REFERENCES tipos_gestion(id))''')

# Prellenar la tabla con datos si está vacía
cursor.execute("SELECT COUNT(*) FROM secretarias")
if cursor.fetchone()[0] == 0:
    cursor.execute("INSERT INTO secretarias (nombre) VALUES ('Secretaría de Educación')")
    cursor.execute("INSERT INTO secretarias (nombre) VALUES ('Secretaría de Salud')")
    cursor.execute("INSERT INTO tipos_gestion (nombre, secretaria_id) VALUES ('Gestión Escolar', 1)")
    cursor.execute("INSERT INTO tipos_gestion (nombre, secretaria_id) VALUES ('Capacitación Docente', 1)")
    cursor.execute("INSERT INTO tipos_gestion (nombre, secretaria_id) VALUES ('Atención Médica', 2)")
    cursor.execute("INSERT INTO tipos_gestion (nombre, secretaria_id) VALUES ('Vacunación', 2)")
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

# Función para obtener coordenadas a partir de una dirección
def obtener_coordenadas(direccion):
    geolocator = Nominatim(user_agent="gestiones_app")
    try:
        location = geolocator.geocode(direccion)
        if location:
            return location.latitude, location.longitude
        else:
            return None, None
    except:
        return None, None

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

    # Seleccionar Secretaría
    cursor.execute("SELECT id, nombre FROM secretarias")
    secretarias = cursor.fetchall()
    secretaria_opciones = {nombre: id for id, nombre in secretarias}
    secretaria_seleccionada = st.selectbox("Seleccionar Secretaría", list(secretaria_opciones.keys()))

    # Mostrar gestiones asociadas a la Secretaría seleccionada
    tipo_gestion_id = None
    if secretaria_seleccionada:
        secretaria_id = secretaria_opciones[secretaria_seleccionada]
        cursor.execute("SELECT id, nombre FROM tipos_gestion WHERE secretaria_id = ?", (secretaria_id,))
        tipos_gestion = cursor.fetchall()
        tipos_gestion_opciones = {nombre: id for id, nombre in tipos_gestion}
        gestion_seleccionada = st.selectbox("Seleccionar Tipo de Gestión", list(tipos_gestion_opciones.keys()))
        if gestion_seleccionada:
            tipo_gestion_id = tipos_gestion_opciones[gestion_seleccionada]

    domicilio = st.text_input("Domicilio")

    if domicilio:
        lat, lon = obtener_coordenadas(domicilio)
        if lat and lon:
            m = folium.Map(location=[lat, lon], zoom_start=15)
            folium.Marker([lat, lon]).add_to(m)
            folium_static(m)
        else:
            st.warning("No se pudo obtener la ubicación para el domicilio proporcionado.")

    if st.button("Guardar Gestión"):
        if titulo and descripcion and domicilio and tipo_gestion_id:
            fecha_actual = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
            lat, lon = obtener_coordenadas(domicilio)
            cursor.execute('''INSERT INTO gestiones 
                              (titulo, descripcion, estado, usuario_id, fecha_ingreso, domicilio, latitud, longitud, secretaria_id, tipo_gestion_id) 
                              VALUES (?, ?, ?, (SELECT id FROM usuarios WHERE username = ?), ?, ?, ?, ?, ?, ?)''', 
                           (titulo, descripcion, estado, st.session_state.username, fecha_actual, domicilio, lat, lon, secretaria_id, tipo_gestion_id))
            conn.commit()
            st.success("Gestión guardada exitosamente!")
        else:
            st.error("Por favor, complete todos los campos.")

    # Mostrar las gestiones existentes
    st.header("Gestiones Existentes")
    cursor.execute('''SELECT g.id, g.titulo, g.descripcion, g.estado,
                             g.fecha_ingreso, g.domicilio,
                             s.nombre AS secretaria,
                             tg.nombre AS tipo_gestion,
                             g.latitud, g.longitud 
                      FROM gestiones g 
                      JOIN usuarios u ON g.usuario_id = u.id 
                      JOIN tipos_gestion tg ON tg.id = g.tipo_gestion_id 
                      JOIN secretarias s ON s.id = tg.secretaria_id 
                      WHERE u.username = ? ORDER BY g.fecha_ingreso DESC''', 
                   (st.session_state.username,))
    gestiones = cursor.fetchall()

    for gestion in gestiones:
        st.subheader(f"Gestión ID: {gestion[0]}")
        st.write(f"**Título:** {gestion[1]}")
        st.write(f"**Descripción:** {gestion[2]}")
        st.write(f"**Estado:** {gestion[3]}")
        st.write(f"**Fecha de ingreso:** {gestion[4]}")
        st.write(f"**Domicilio:** {gestion[5]}")
        st.write(f"**Secretaría:** {gestion[6]}")
        st.write(f"**Tipo de Gestión:** {gestion[7]}")
        
        # Mostrar mapa para cada gestión
        if gestion[8] and gestion[9]:
            m = folium.Map(location=[gestion[8], gestion[9]], zoom_start=15)
            folium.Marker([gestion[8], gestion[9]]).add_to(m)
            folium_static(m)

    if st.button("Cerrar Sesión"):
        st.session_state.logged_in = False
        st.rerun()

# Cerrar conexión
conn.close()
