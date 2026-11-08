import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
from datetime import datetime

# ---------------------- CONFIGURACIÓN DE LA PÁGINA ----------------------
st.set_page_config(
    page_title="Sistema de Gestión de Pagos",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------- BASE DE DATOS ----------------------
def init_db():
    conn = sqlite3.connect('sistema_pagos.db')
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS usuarios
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  usuario TEXT UNIQUE NOT NULL,
                  contrasena TEXT NOT NULL,
                  rol TEXT NOT NULL)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS fechas_corte
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  dia INTEGER UNIQUE NOT NULL)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS clientes
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  nombre TEXT NOT NULL,
                  direccion TEXT,
                  telefono TEXT,
                  fecha_corte_id INTEGER,
                  estado TEXT DEFAULT 'Activo',
                  FOREIGN KEY (fecha_corte_id) REFERENCES fechas_corte(id))''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS pagos
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  cliente_id INTEGER NOT NULL,
                  monto REAL NOT NULL,
                  fecha_pago TEXT NOT NULL,
                  periodo TEXT NOT NULL,
                  FOREIGN KEY (cliente_id) REFERENCES clientes(id))''')
    
    c.execute("SELECT * FROM usuarios WHERE usuario = 'admin'")
    if not c.fetchone():
        c.execute("INSERT INTO usuarios (usuario, contrasena, rol) VALUES (?, ?, ?)",
                  ('admin', 'admin123', 'Administrador'))
    
    conn.commit()
    conn.close()

def ejecutar_consulta(query, parametros=(), fetch=False):
    conn = sqlite3.connect('sistema_pagos.db')
    c = conn.cursor()
    c.execute(query, parametros)
    resultado = c.fetchall() if fetch else None
    conn.commit()
    conn.close()
    return resultado

init_db()

# ---------------------- SESIÓN Y LOGIN ----------------------
if 'sesion' not in st.session_state:
    st.session_state.sesion = None
if 'usuario' not in st.session_state:
    st.session_state.usuario = None
if 'rol' not in st.session_state:
    st.session_state.rol = None

def login():
    st.title("Inicio de Sesión")
    st.subheader("Sistema de Gestión de Pagos de Internet")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        usuario = st.text_input("Usuario")
        contrasena = st.text_input("Contraseña", type="password")
        
        if st.button("Ingresar", type="primary", use_container_width=True):
            res = ejecutar_consulta("SELECT rol FROM usuarios WHERE usuario = ? AND contrasena = ?",
                                   (usuario, contrasena), fetch=True)
            if res:
                st.session_state.sesion = True
                st.session_state.usuario = usuario
                st.session_state.rol = res[0][0]
                st.success(f"Bienvenido, {usuario}!")
                st.rerun()
            else:
                st.error("Usuario o contraseña incorrectos")
    
    st.info("Credencial por defecto: Usuario: admin | Contraseña: admin123")
    st.stop()

if not st.session_state.sesion:
    login()

es_admin = st.session_state.rol == "Administrador"

# ---------------------- MENÚ LATERAL ----------------------
with st.sidebar:
    st.title("Sistema de Pagos")
    st.markdown(f"Usuario: {st.session_state.usuario}")
    st.markdown(f"Rol: {st.session_state.rol}")
    st.divider()
    
    menu = st.radio("Navegación", [
        "Dashboard",
        "Clientes",
        "Finanzas",
        "Gestión de Usuarios"
    ])
    
    st.divider()
    if st.button("Cerrar Sesión"):
        for key in st.session_state.keys():
            del st.session_state[key]
        st.rerun()

# ---------------------- FUNCIONES AUXILIARES ----------------------
def obtener_fechas_corte():
    return ejecutar_consulta("SELECT id, dia FROM fechas_corte ORDER BY dia", fetch=True)

def obtener_clientes(fecha_corte_id=None):
    if fecha_corte_id:
        return ejecutar_consulta("SELECT c.id, c.nombre, c.direccion, c.telefono, c.estado, f.dia FROM clientes c LEFT JOIN fechas_corte f ON c.fecha_corte_id = f.id WHERE c.fecha_corte_id = ? ORDER BY c.nombre", (fecha_corte_id,), fetch=True)
    return ejecutar_consulta("SELECT c.id, c.nombre, c.direccion, c.telefono, c.estado, f.dia FROM clientes c LEFT JOIN fechas_corte f ON c.fecha_corte_id = f.id ORDER BY c.nombre", fetch=True)

# ==================================================
# PÁGINA: DASHBOARD
# ==================================================
if menu == "Dashboard":
    st.title("Panel Principal")
    st.subheader("Resumen del Sistema")
    
    total_clientes = len(ejecutar_consulta("SELECT id FROM clientes", fetch=True))
    activos = len(ejecutar_consulta("SELECT id FROM clientes WHERE estado = 'Activo'", fetch=True))
    suspendidos = len(ejecutar_consulta("SELECT id FROM clientes WHERE estado = 'Suspendido'", fetch=True))
    
    pagos = ejecutar_consulta("SELECT monto FROM pagos WHERE strftime('%Y-%m', fecha_pago) = ?",
                              (datetime.now().strftime('%Y-%m'),), fetch=True)
    ingreso_mes = sum(p[0] for p in pagos) if pagos else 0
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Clientes", total_clientes)
    col2.metric("Clientes Activos", activos)
    col3.metric("Clientes Suspendidos", suspendidos)
    col4.metric("Ingreso del Mes", f"${ingreso_mes:,.2f}")
    
    st.divider()
    st.subheader("Resumen Rápido")
    st.info("Navega por el menú lateral para ver listas de clientes, registrar pagos y ver reportes financieros con gráficas.")
    
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("### Últimos Clientes Agregados")
        ultimos = ejecutar_consulta("SELECT nombre, estado FROM clientes ORDER BY id DESC LIMIT 5", fetch=True)
        if ultimos:
            for nom, est in ultimos:
                st.write(f"- {nom} - {'Activo' if est == 'Activo' else 'Suspendido'}")
        else:
            st.write("Sin registros aún")
    
    with col_b:
        st.markdown("### Últimos Pagos Registrados")
        ultimos_pagos = ejecutar_consulta("SELECT c.nombre, p.monto, p.fecha_pago FROM pagos p JOIN clientes c ON p.cliente_id = c.id ORDER BY p.id DESC LIMIT 5", fetch=True)
        if ultimos_pagos:
            for nom, mon, fec in ultimos_pagos:
                st.write(f"- {nom}: ${mon:.2f} ({fec})")
        else:
            st.write("Sin registros aún")

# ==================================================
# PÁGINA: CLIENTES
# ==================================================
elif menu == "Clientes":
    st.title("Gestión de Clientes")
    
    st.subheader("Fechas de Corte")
    fechas = obtener_fechas_corte()
    if fechas:
        st.write("Fechas configuradas: " + ", ".join([f"Día {f[1]}" for f in fechas]))
    
    if es_admin:
        with st.expander("Agregar Nueva Fecha de Corte"):
            dia_nuevo = st.number_input("Día del mes", min_value=1, max_value=31, step=1)
            if st.button("Guardar Fecha"):
                try:
                    ejecutar_consulta("INSERT INTO fechas_corte (dia) VALUES (?)", (dia_nuevo,))
                    st.success(f"Fecha del día {dia_nuevo} agregada")
                    st.rerun()
                except:
                    st.error("Ese día ya está registrado")
        
        if fechas:
            with st.expander("Eliminar Fecha de Corte"):
                opciones = {f"Día {d}": i for i, d in fechas}
                sel = st.selectbox("Selecciona fecha a eliminar", list(opciones.keys()))
                if st.button("Eliminar Fecha", type="secondary"):
                    ejecutar_consulta("DELETE FROM fechas_corte WHERE id = ?", (opciones[sel],))
                    st.warning("Fecha eliminada")
                    st.rerun()
    
    st.divider()
    
    st.subheader("Lista de Clientes")
    filt_opciones = ["Todas las fechas"] + [f"Día {d}" for _, d in fechas] if fechas else ["Sin fechas"]
    filtro = st.selectbox("Filtrar por fecha de corte", filt_opciones)
    
    clientes = []
    if filtro != "Todas las fechas" and fechas:
        dia_sel = int(filtro.replace("Día ", ""))
        fc_id = [i for i, d in fechas if d == dia_sel][0]
        clientes = obtener_clientes(fc_id)
    else:
        clientes = obtener_clientes()
    
    if clientes:
        df_clientes = pd.DataFrame(clientes, columns=["ID", "Nombre", "Dirección", "Teléfono", "Estado", "Fecha Corte"])
        st.dataframe(df_clientes, use_container_width=True, hide_index=True)
    else:
        st.info("No hay clientes registrados aún")
    
    if es_admin and fechas:
        st.divider()
        with st.expander("Agregar Nuevo Cliente", expanded=False):
            nom = st.text_input("Nombre Completo")
            dirr = st.text_input("Dirección")
            tel = st.text_input("Teléfono")
            fc_sel = st.selectbox("Fecha de Corte", [f"Día {d}" for _, d in fechas])
            fc_id_sel = [i for i, d in fechas if f"Día {d}" == fc_sel][0]
            estado = st.selectbox("Estado", ["Activo", "Suspendido"])
            
            if st.button("Guardar Cliente", type="primary"):
                if nom:
                    ejecutar_consulta("INSERT INTO clientes (nombre, direccion, telefono, fecha_corte_id, estado) VALUES (?, ?, ?, ?, ?)", (nom, dirr, tel, fc_id_sel, estado))
                    st.success(f"Cliente '{nom}' agregado correctamente")
                    st.rerun()
                else:
                    st.warning("El nombre es obligatorio")
    
    if es_admin and clientes:
        st.divider()
        st.subheader("Acciones")
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("Cambiar Estado del Cliente")
            cli_opc = {f"{c[1]} - {'Activo' if c[4]=='Activo' else 'Suspendido'}": c[0] for c in clientes}
            cli_sel = st.selectbox("Selecciona cliente", list(cli_opc.keys()))
            nuevo_est = "Suspendido" if "Activo" in cli_sel else "Activo"
            if st.button(f"Marcar como {nuevo_est}"):
                ejecutar_consulta("UPDATE clientes SET estado = ? WHERE id = ?", (nuevo_est, cli_opc[cli_sel]))
                st.success("Estado actualizado")
                st.rerun()
        
        with col2:
            st.markdown("Registrar Pago")
            cli_pago = {c[1]: c[0] for c in clientes}
            c_sel = st.selectbox("Cliente", list(cli_pago.keys()))
            monto = st.number_input("Monto ($)", min_value=0.0, step=10.0, format="%.2f")
            periodo = st.text_input("Periodo (ej: Noviembre 2026)")
            fecha_hoy = datetime.now().strftime("%Y-%m-%d")
            st.text(f"Fecha de pago: {fecha_hoy}")
            if st.button("Guardar Pago", type="primary"):
                if monto > 0 and periodo:
                    ejecutar_consulta("INSERT INTO pagos (cliente_id, monto, fecha_pago, periodo) VALUES (?, ?, ?, ?)", (cli_pago[c_sel], monto, fecha_hoy, periodo))
                    st.success("Pago registrado")
                    st.rerun()
                else:
                    st.warning("Completa monto y periodo")

# ==================================================
# PÁGINA: FINANZAS
# ==================================================
elif menu == "Finanzas":
    st.title("Finanzas y Reportes")
    
    periodos = ejecutar_consulta("SELECT DISTINCT periodo FROM pagos ORDER BY periodo DESC", fetch=True)
    periodos = [p[0] for p in periodos] if periodos else []
    
    if not periodos:
        st.info("No hay pagos registrados aún. Registra pagos en la sección de Clientes para ver reportes.")
        st.stop()
    
    st.subheader("Ingresos por Periodo")
    
    datos_ingresos = []
    for p in periodos:
        total = ejecutar_consulta("SELECT SUM(monto) FROM pagos WHERE periodo = ?", (p,), fetch=True)[0][0]
        cantidad = ejecutar_consulta("SELECT COUNT(*) FROM pagos WHERE periodo = ?", (p,), fetch=True)[0][0]
        datos_ingresos.append({"Periodo": p, "Ingreso Total": total, "Pagos Recibidos": cantidad})
    
    df_ingresos = pd.DataFrame(datos_ingresos)
    st.dataframe(df_ingresos, use_container_width=True, hide_index=True)
    
    total_general = df_ingresos["Ingreso Total"].sum()
    st.subheader(f"Total Acumulado: ${total_general:,.2f}")
    
    st.divider()
    st.subheader("Gráficas Comparativas")
    
    col_a, col_b = st.columns(2)
    with col_a:
        fig1 = px.bar(df_ingresos, x="Periodo", y="Ingreso Total",
                      title="Ingresos por Periodo ($)",
                      color="Periodo", text_auto=True)
        st.plotly_chart(fig1, use_container_width=True)
    
    with col_b:
        fig2 = px.pie(df_ingresos, values="Ingreso Total", names="Periodo",
                      title="Distribución de Ingresos")
        st.plotly_chart(fig2, use_container_width=True)
    
    st.subheader("Comparativa Detallada")
    fig3 = px.line(df_ingresos, x="Periodo", y="Ingreso Total",
                   markers=True, title="Tendencia de Ingresos",
                   text="Ingreso Total")
    fig3.update_traces(textposition="top center")
    st.plotly_chart(fig3, use_container_width=True)
    
    st.divider()
    st.subheader("Historial Completo de Pagos")
    pagos_completos = ejecutar_consulta("SELECT c.nombre, p.monto, p.fecha_pago, p.periodo FROM pagos p JOIN clientes c ON p.cliente_id = c.id ORDER BY p.fecha_pago DESC", fetch=True)
    
    if pagos_completos:
        df_pagos = pd.DataFrame(pagos_completos, columns=["Cliente", "Monto", "Fecha de Pago", "Periodo"])
        st.dataframe(df_pagos, use_container_width=True, hide_index=True)
    else:
        st.info("No hay pagos registrados")

# ==================================================
# GESTIÓN DE USUARIOS
# ==================================================
elif menu == "Gestión de Usuarios":
    st.title("Gestión de Usuarios")
    
    if not es_admin:
        st.warning("Solo los administradores pueden ver esta sección")
        st.stop()
    
    st.subheader("Usuarios del Sistema")
    usuarios = ejecutar_consulta("SELECT id, usuario, rol FROM usuarios ORDER BY usuario", fetch=True)
    if usuarios:
        df_usuarios = pd.DataFrame(usuarios, columns=["ID", "Usuario", "Rol"])
        st.dataframe(df_usuarios, use_container_width=True, hide_index=True)
    
    with st.expander("Agregar Nuevo Usuario"):
    	nombre = st.text_input("Nombre")
    	usuario = st.text_input("Usuario")
    	contrasena = st.text_input("Contraseña", type="password")
    	rol = st.selectbox("Rol", ["Usuario", "Administrador"])
    	if st.button("Guardar Usuario"):
        		# tu código aquí
        		st.success("Usuario agregado correctamente")