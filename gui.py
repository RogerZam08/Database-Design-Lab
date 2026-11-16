import streamlit as st
import requests
import pandas as pd

# URL base de tu API de Flask
API_URL = "http://127.0.0.1:5000/api/inventario"

st.set_page_config(page_title="Inventario de Laboratorio", layout="wide")
st.title("📦 Sistema de Inventario - Laboratorio de Hardware")

# Menú lateral para navegar
menu = ["Ver Inventario", "Agregar Componente"]
choice = st.sidebar.selectbox("Navegación", menu)

if choice == "Ver Inventario":
    st.subheader("Lista de Componentes en Stock")
    
    try:
        # Hacemos la petición GET a la API
        response = requests.get(API_URL)
        if response.status_code == 200:
            data = response.json()
            if data:
                # Usamos Pandas para que la tabla se vea estética y ordenada
                df = pd.DataFrame(data)
                df = df[['element_id', 'component_name', 'category', 'quantity']]
                df.columns = ['ID', 'Componente', 'Categoría', 'Cantidad (Stock)']
                st.dataframe(df, use_container_width=True)
            else:
                st.info("El inventario está vacío. Agrega componentes desde el menú.")
        else:
            st.error("Error al conectar con la API.")
    except Exception as e:
        st.error(f"No se pudo conectar a la API. ¿Está Flask corriendo? Error: {e}")

elif choice == "Agregar Componente":
    st.subheader("Registrar Nuevo Componente")
    
    # Formulario para mandar datos por POST
    with st.form("add_form"):
        col1, col2 = st.columns(2)
        with col1:
            element_id = st.text_input("Código del Elemento (ej. E03)")
            component_name = st.text_input("Nombre del Componente")
        with col2:
            category = st.selectbox("Categoría Técnica", ["ICs", "Passives", "Power Supplies", "Development Boards", "Other"])
            quantity = st.number_input("Cantidad Inicial en Stock", min_value=0, step=1)
        
        submit = st.form_submit_button("Guardar en Base de Datos")

        if submit:
            if element_id and component_name:
                payload = {
                    "element_id": element_id,
                    "component_name": component_name,
                    "category": category,
                    "quantity": quantity
                }
                try:
                    # Hacemos la petición POST a la API
                    res = requests.post(API_URL, json=payload)
                    if res.status_code == 201:
                        st.success(f"¡Componente '{component_name}' guardado exitosamente!")
                    else:
                        error_msg = res.json().get('error', 'Error desconocido')
                        st.error(f"No se pudo guardar: {error_msg}")
                except Exception as e:
                    st.error(f"Error de conexión con la API: {e}")
            else:
                st.warning("Por favor, llena los campos de Código y Nombre.")
