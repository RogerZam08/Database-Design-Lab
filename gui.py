import streamlit as st
import requests
import pandas as pd
from datetime import date, timedelta

API_BASE = "http://127.0.0.1:5000/api"

st.set_page_config(
    page_title="LabStock | Inventario de Hardware",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# ESTILOS CSS PERSONALIZADOS
# ==========================================
st.markdown("""
<style>
    /* Banner principal con degradado tech */
    .hero-banner {
        background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 55%, #0284c7 100%);
        padding: 1.6rem 2rem;
        border-radius: 14px;
        color: #ffffff;
        margin-bottom: 1.5rem;
        box-shadow: 0 8px 24px rgba(2, 132, 199, 0.22);
        border: 1px solid rgba(56, 189, 248, 0.25);
    }
    .hero-banner h1 {
        margin: 0;
        font-size: 1.9rem;
        font-weight: 700;
        letter-spacing: -0.5px;
    }
    .hero-banner p {
        margin: 0.35rem 0 0 0;
        color: #bae6fd;
        font-size: 0.95rem;
    }

    /* Tarjetas de métricas */
    div[data-testid="stMetric"] {
        background: rgba(30, 41, 59, 0.55);
        border: 1px solid rgba(148, 163, 184, 0.2);
        padding: 1rem 1.2rem;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    }

    /* Badges de estado */
    .badge {
        display: inline-block;
        padding: 0.2rem 0.65rem;
        border-radius: 999px;
        font-size: 0.78rem;
        font-weight: 600;
        text-transform: uppercase;
    }
    .badge-pending { background: #fef3c7; color: #92400e; }
    .badge-approved { background: #dbeafe; color: #1e40af; }
    .badge-partial_return { background: #e0e7ff; color: #3730a3; }
    .badge-returned { background: #dcfce7; color: #166534; }
    .badge-rejected { background: #fee2e2; color: #991b1b; }
    .badge-overdue { background: #fecaca; color: #7f1d1d; }

    /* Tarjeta de datasheet */
    .datasheet-card {
        background: rgba(15, 23, 42, 0.6);
        border-left: 4px solid #38bdf8;
        padding: 1.2rem 1.5rem;
        border-radius: 10px;
        margin-top: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# UTILIDADES DE CONEXIÓN
# ==========================================
def api_get(endpoint):
    try:
        res = requests.get(f"{API_BASE}{endpoint}", timeout=5)
        if res.status_code == 200:
            return res.json(), None
        return None, f"HTTP {res.status_code}: {res.text[:250]}"
    except requests.exceptions.ConnectionError:
        return None, "No se pudo conectar con Flask (puerto 5000). Ejecuta `python app.py`."
    except Exception as e:
        return None, str(e)

# ==========================================
# SIDEBAR (NAVEGACIÓN + ESTADO EN VIVO)
# ==========================================
with st.sidebar:
    st.markdown("## ⚡ LabStock")
    st.caption("Gestión de Inventario y Préstamos")
    st.divider()

    # Verificar conexión en vivo
    inv_check, inv_err = api_get("/inventario")
    if inv_err is None:
        st.success("🟢 API & MySQL conectados")
    else:
        st.error("🔴 Error de conexión")

    menu = st.radio(
        "Módulos del Sistema",
        [
            "📊 Inventario y Datasheets",
            "➕ Agregar Componente",
            "👥 Usuarios y Proyectos",
            "📝 Nueva Solicitud",
            "🛡️ Panel Administrador"
        ]
    )
    st.divider()
    st.caption("Backend: Flask + SQLAlchemy\nMotor: MySQL 8 (InnoDB)")

# Banner superior global
st.markdown("""
<div class="hero-banner">
    <h1>⚡ Sistema de Inventario — Laboratorio de Hardware</h1>
    <p>Control transaccional de patrimonio global, stock disponible, fichas técnicas y flujo de préstamos con aprobación.</p>
</div>
""", unsafe_allow_html=True)

# ==========================================
# 1. INVENTARIO Y DATASHEETS
# ==========================================
if menu == "📊 Inventario y Datasheets":
    if inv_err:
        st.error(f"Error al consultar `/api/inventario` → {inv_err}")
        st.info("💡 Revisa la terminal de `app.py` para ver el error exacto de MySQL (contenedor apagado, tablas no creadas o credenciales).")
        st.stop()

    sol_data, _ = api_get("/solicitudes")
    pendientes_count = len([s for s in (sol_data or []) if s['state'] == 'pending'])

    # KPIs superiores
    total_tipos = len(inv_check)
    total_global = sum(i['total_quantity'] for i in inv_check)
    total_disp = sum(i['available_quantity'] for i in inv_check)
    total_prestados = total_global - total_disp

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Componentes Registrados", total_tipos)
    k2.metric("Patrimonio Global (Unidades)", total_global)
    k3.metric("Disponibles en Percha", total_disp, delta=f"-{total_prestados} prestados" if total_prestados > 0 else "100% libre")
    k4.metric("Solicitudes Pendientes", pendientes_count)

    st.markdown("### 📦 Catálogo: Inventario Global vs. Stock Actual")
    if inv_check:
        # Filtro de búsqueda rápida
        col_f1, col_f2 = st.columns([2, 1])
        search_q = col_f1.text_input("🔍 Buscar por nombre o código", placeholder="Ej: EEPROM, 555, E01...")
        cats = ["Todas"] + sorted(list({i['category'] for i in inv_check}))
        cat_filter = col_f2.selectbox("Filtrar por categoría", cats)

        filtrados = [
            i for i in inv_check
            if (search_q.lower() in i['component_name'].lower() or search_q.lower() in i['element_id'].lower())
            and (cat_filter == "Todas" or i['category'] == cat_filter)
        ]

        if filtrados:
            df = pd.DataFrame([
                {
                    'ID': d['element_id'],
                    'Componente': d['component_name'],
                    'Categoría': d['category'],
                    'Global (Total)': d['total_quantity'],
                    'Actual (Disp.)': d['available_quantity'],
                    'Disponibilidad': (d['available_quantity'] / d['total_quantity'] * 100) if d['total_quantity'] > 0 else 0,
                    'Datasheet': (d['datasheet'].get('datasheet_url') if d.get('datasheet') else None)
                }
                for d in filtrados
            ])
            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Disponibilidad": st.column_config.ProgressColumn(
                        "Disponibilidad (%)",
                        format="%.0f%%",
                        min_value=0,
                        max_value=100,
                    ),
                    "Datasheet": st.column_config.LinkColumn("Datasheet PDF", display_text="Abrir PDF")
                }
            )

            st.divider()
            st.markdown("### 📄 Inspector de Ficha Técnica (Datasheet)")
            opciones = {f"{d['element_id']} — {d['component_name']}": d for d in filtrados}
            seleccion = st.selectbox("Selecciona un componente para ver su ficha:", list(opciones.keys()))
            item_sel = opciones[seleccion]
            ds = item_sel.get('datasheet')

            if ds:
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Fabricante", ds.get('manufacturer') or "N/A")
                c2.metric("Part Number", ds.get('part_number') or "N/A")
                c3.metric("Encapsulado", ds.get('package_type') or "N/A")
                c4.metric("Voltaje Operativo", ds.get('operating_voltage') or "N/A")

                specs = ds.get('technical_specs') or "Sin especificaciones adicionales."
                url_html = f'<br><br>🔗 <a href="{ds["datasheet_url"]}" target="_blank" style="color:#38bdf8;">Ver Datasheet Oficial</a>' if ds.get('datasheet_url') else ""
                st.markdown(f"""
                <div class="datasheet-card">
                    <strong>Especificaciones Técnicas:</strong><br>{specs}{url_html}
                </div>
                """, unsafe_allow_html=True)
            else:
                st.info("Este componente no tiene ficha técnica registrada todavía.")
        else:
            st.warning("No hay componentes que coincidan con tu filtro.")
    else:
        st.info("El inventario está vacío. Ve a **➕ Agregar Componente** para registrar el primero.")

# ==========================================
# 2. AGREGAR COMPONENTE + DATASHEET
# ==========================================
elif menu == "➕ Agregar Componente":
    st.markdown("### ➕ Registrar Componente en Inventario Global")
    st.caption("Al guardar aquí, un Trigger en MySQL sincroniza automáticamente el stock inicial en `inventario_actual`.")

    with st.form("add_component_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            element_id = st.text_input("Código del Elemento *", placeholder="Ej: E01")
            component_name = st.text_input("Nombre del Componente *", placeholder="Ej: Memoria EEPROM 16K")
        with c2:
            category = st.selectbox("Categoría Técnica *", ["ICs", "Passives", "Power Supplies", "Development Boards", "Sensors", "Other"])
            total_quantity = st.number_input("Cantidad Total (Patrimonio) *", min_value=0, step=1, value=5)

        with st.expander("📄 Agregar Ficha Técnica / Datasheet (Opcional)", expanded=True):
            c3, c4 = st.columns(2)
            with c3:
                manufacturer = st.text_input("Fabricante", placeholder="Ej: Microchip / Atmel")
                part_number = st.text_input("Número de Parte (Único)", placeholder="Ej: AT28C16-15PU")
                package_type = st.text_input("Encapsulado", placeholder="Ej: DIP-24")
            with c4:
                operating_voltage = st.text_input("Voltaje de Operación", placeholder="Ej: 4.5V - 5.5V")
                datasheet_url = st.text_input("URL del Datasheet", placeholder="https://...")
            technical_specs = st.text_area("Especificaciones / Notas", placeholder="Ej: 2K x 8 Parallel EEPROM, 150ns access time...")

        submitted = st.form_submit_button("💾 Guardar Componente", type="primary", use_container_width=True)
        if submitted:
            if element_id.strip() and component_name.strip():
                payload = {
                    "element_id": element_id.strip(),
                    "component_name": component_name.strip(),
                    "category": category,
                    "total_quantity": total_quantity,
                    "datasheet": {
                        "manufacturer": manufacturer,
                        "part_number": part_number,
                        "package_type": package_type,
                        "operating_voltage": operating_voltage,
                        "technical_specs": technical_specs,
                        "datasheet_url": datasheet_url
                    }
                }
                try:
                    res = requests.post(f"{API_BASE}/inventario", json=payload)
                    if res.status_code == 201:
                        st.success(f"✅ '{component_name}' registrado correctamente.")
                    else:
                        st.error(f"❌ {res.json().get('error', res.text)}")
                except Exception as e:
                    st.error(f"Error de conexión: {e}")
            else:
                st.warning("Completa al menos el Código y el Nombre del componente.")

# ==========================================
# 3. USUARIOS Y PROYECTOS (SIN TOCAR SQL)
# ==========================================
elif menu == "👥 Usuarios y Proyectos":
    st.markdown("### 👥 Gestión de Usuarios y Proyectos")
    tab_u, tab_p = st.tabs(["👤 Usuarios (Estudiantes / Admins)", "🧪 Proyectos Académicos"])

    with tab_u:
        col_form, col_list = st.columns([1, 1.4])
        with col_form:
            with st.form("user_form", clear_on_submit=True):
                st.markdown("**Registrar Usuario**")
                u_id = st.text_input("ID de Usuario *", placeholder="Ej: U01")
                u_name = st.text_input("Nombre Completo *", placeholder="Ej: Roger Zambrano")
                u_rol = st.selectbox("Rol *", ["student", "administrator"])
                if st.form_submit_button("Guardar Usuario", type="primary", use_container_width=True):
                    if u_id.strip() and u_name.strip():
                        r = requests.post(f"{API_BASE}/usuarios", json={"user_id": u_id.strip(), "name": u_name.strip(), "rol": u_rol})
                        if r.status_code == 201:
                            st.success("✅ Usuario creado.")
                            st.rerun()
                        else:
                            st.error(f"❌ {r.json().get('error', r.text)}")
                    else:
                        st.warning("Llena todos los campos.")
        with col_list:
            users, u_err = api_get("/usuarios")
            if u_err:
                st.error(u_err)
            elif users:
                st.dataframe(pd.DataFrame(users), use_container_width=True, hide_index=True)
            else:
                st.info("No hay usuarios registrados aún.")

    with tab_p:
        users, _ = api_get("/usuarios")
        col_form, col_list = st.columns([1, 1.4])
        with col_form:
            with st.form("proj_form", clear_on_submit=True):
                st.markdown("**Registrar Proyecto**")
                p_id = st.text_input("ID de Proyecto *", placeholder="Ej: P01")
                p_name = st.text_input("Nombre del Proyecto *", placeholder="Ej: ALU 8-bits")
                p_state = st.selectbox("Estado", ["in_development", "finished"])
                if users:
                    u_map = {f"{u['user_id']} — {u['name']} ({u['rol']})": u['user_id'] for u in users}
                    u_sel = st.selectbox("Responsable *", list(u_map.keys()))
                else:
                    u_sel = None
                    st.warning("Crea primero un usuario en la pestaña anterior.")

                if st.form_submit_button("Guardar Proyecto", type="primary", use_container_width=True):
                    if p_id.strip() and p_name.strip() and u_sel:
                        r = requests.post(f"{API_BASE}/proyectos", json={
                            "project_id": p_id.strip(),
                            "project_name": p_name.strip(),
                            "state": p_state,
                            "user_id": u_map[u_sel]
                        })
                        if r.status_code == 201:
                            st.success("✅ Proyecto creado.")
                            st.rerun()
                        else:
                            st.error(f"❌ {r.json().get('error', r.text)}")
                    else:
                        st.warning("Completa todos los campos.")
        with col_list:
            projs, p_err = api_get("/proyectos")
            if p_err:
                st.error(p_err)
            elif projs:
                st.dataframe(pd.DataFrame(projs), use_container_width=True, hide_index=True)
            else:
                st.info("No hay proyectos registrados aún.")

# ==========================================
# 4. NUEVA SOLICITUD (ESTUDIANTE)
# ==========================================
elif menu == "📝 Nueva Solicitud":
    st.markdown("### 📝 Crear Solicitud de Préstamo")
    st.caption("La solicitud queda en estado `pending`. El stock disponible no se descuenta hasta que un administrador la apruebe.")

    proyectos, p_err = api_get("/proyectos")
    inventario, i_err = api_get("/inventario")

    if p_err or i_err:
        st.error(p_err or i_err)
    elif not proyectos or not inventario:
        st.warning("Necesitas al menos 1 proyecto y 1 componente registrados. Créalos en los módulos anteriores.")
    else:
        with st.form("loan_form"):
            c1, c2 = st.columns(2)
            with c1:
                solicitud_id = st.text_input("ID de Solicitud *", placeholder="Ej: S01")
                proj_map = {f"{p['project_id']} — {p['project_name']}": p['project_id'] for p in proyectos}
                proj_sel = st.selectbox("Proyecto *", list(proj_map.keys()))
            with c2:
                due_date = st.date_input("Fecha límite de devolución *", value=date.today() + timedelta(days=7))
                inv_map = {f"{i['element_id']} — {i['component_name']} (Disp: {i['available_quantity']})": i['element_id'] for i in inventario}
                comp_sel = st.selectbox("Componente solicitado *", list(inv_map.keys()))
                qty = st.number_input("Cantidad *", min_value=1, step=1)

            if st.form_submit_button("📤 Enviar Solicitud", type="primary", use_container_width=True):
                if solicitud_id.strip():
                    payload = {
                        "solicitud_id": solicitud_id.strip(),
                        "project_id": proj_map[proj_sel],
                        "due_date": due_date.isoformat(),
                        "items": [{"element_id": inv_map[comp_sel], "quantity": qty}]
                    }
                    r = requests.post(f"{API_BASE}/solicitudes", json=payload)
                    if r.status_code == 201:
                        st.success("✅ Solicitud enviada. Esperando aprobación del administrador.")
                    else:
                        st.error(f"❌ Rechazada por MySQL: {r.json().get('error', r.text)}")
                else:
                    st.warning("Ingresa un ID de solicitud.")

# ==========================================
# 5. PANEL ADMINISTRADOR (APROBACIONES Y DEVOLUCIONES)
# ==========================================
elif menu == "🛡️ Panel Administrador":
    st.markdown("### 🛡️ Control de Aprobaciones, Devoluciones e Historial")
    admins, a_err = api_get("/usuarios?rol=administrator")
    solicitudes, s_err = api_get("/solicitudes")

    if a_err or s_err:
        st.error(a_err or s_err)
        st.stop()

    tab1, tab2, tab3 = st.tabs(["⏳ Pendientes", "🔄 Devoluciones", "📊 Historial Completo"])

    with tab1:
        pendientes = [s for s in solicitudes if s['state'] == 'pending']
        if not pendientes:
            st.info("No hay solicitudes pendientes por aprobar.")
        elif not admins:
            st.warning("Registra al menos un usuario con rol `administrator` en **👥 Usuarios y Proyectos**.")
        else:
            admin_map = {f"{a['user_id']} — {a['name']}": a['user_id'] for a in admins}
            admin_id = admin_map[st.selectbox("Actuar como Administrador:", list(admin_map.keys()))]

            for sol in pendientes:
                with st.expander(f"📄 Solicitud {sol['solicitud_id']} | Proyecto: {sol['project_id']} | Vence: {sol['due_date']}", expanded=True):
                    st.dataframe(pd.DataFrame(sol['items']), use_container_width=True, hide_index=True)
                    b1, b2 = st.columns(2)
                    if b1.button("✅ Aprobar y Descontar Stock", key=f"app_{sol['solicitud_id']}", type="primary", use_container_width=True):
                        r = requests.put(f"{API_BASE}/solicitudes/{sol['solicitud_id']}/aprobar", json={"approved_by": admin_id})
                        if r.status_code == 200:
                            st.success("Aprobada y stock descontado.")
                            st.rerun()
                        else:
                            st.error(r.json().get('error', r.text))
                    if b2.button("❌ Rechazar", key=f"rej_{sol['solicitud_id']}", use_container_width=True):
                        r = requests.put(f"{API_BASE}/solicitudes/{sol['solicitud_id']}/rechazar", json={"approved_by": admin_id})
                        if r.status_code == 200:
                            st.warning("Solicitud rechazada.")
                            st.rerun()
                        else:
                            st.error(r.json().get('error', r.text))

    with tab2:
        activas = [s for s in solicitudes if s['state'] in ('approved', 'partial_return', 'overdue')]
        if not activas:
            st.info("No hay préstamos activos pendientes de devolución.")
        else:
            for sol in activas:
                st.markdown(
                    f"**Solicitud `{sol['solicitud_id']}`** (Proyecto `{sol['project_id']}`) "
                    f"<span class='badge badge-{sol['state']}'>{sol['state']}</span>",
                    unsafe_allow_html=True
                )
                for item in sol['items']:
                    c1, c2, c3 = st.columns([2.2, 1.8, 1])
                    c1.write(f"Componente `{item['element_id']}` — Prestados: **{item['quantity']}** | Devueltos: **{item['returned_quantity']}**")
                    nuevo_ret = c2.number_input(
                        "Total devuelto acumulado",
                        min_value=item['returned_quantity'],
                        max_value=item['quantity'],
                        value=item['returned_quantity'],
                        step=1,
                        key=f"ret_{sol['solicitud_id']}_{item['element_id']}",
                        label_visibility="collapsed"
                    )
                    if c3.button("Registrar", key=f"btn_{sol['solicitud_id']}_{item['element_id']}", type="primary", use_container_width=True):
                        r = requests.put(
                            f"{API_BASE}/solicitudes/{sol['solicitud_id']}/devolver",
                            json={"element_id": item['element_id'], "returned_quantity": nuevo_ret}
                        )
                        if r.status_code == 200:
                            st.success("Devolución registrada.")
                            st.rerun()
                        else:
                            st.error(r.json().get('error', r.text))
                st.divider()

    with tab3:
        if solicitudes:
            df_hist = pd.DataFrame([
                {
                    'ID': s['solicitud_id'],
                    'Proyecto': s['project_id'],
                    'Aprobado Por': s['approved_by'] or '—',
                    'Emisión': s['emission_date'],
                    'Vencimiento': s['due_date'],
                    'Cierre': s['closed_date'] or '—',
                    'Estado': s['state'],
                    '¿Devolvió Todo?': '✅ Sí' if s['is_fully_returned'] else '⏳ No'
                }
                for s in solicitudes
            ])
            c1, c2 = st.columns(2)
            c1.metric("Total de Préstamos", len(df_hist))
            c2.metric("Completamente Devueltos", sum(1 for s in solicitudes if s['is_fully_returned']))
            st.dataframe(df_hist, use_container_width=True, hide_index=True)
        else:
            st.info("Aún no existen solicitudes en el historial.")