# Transactional System for Hardware Inventory Management

Este proyecto implementa el diseño, la base de datos, una API REST (Flask) y una interfaz gráfica (Streamlit) para el control de inventario de hardware.

## Archivos Principales
* `schema.sql`: Script DDL con la estructura, triggers y constraints.
* `test_cases_manual.sql`: Consultas para validar los Test Cases del documento.
* `app.py`: Backend (API REST CRUD en Flask).
* `gui.py`: Frontend (Interfaz gráfica en Streamlit).
* `Database_Design.pdf`: Especificación formal del diseño de BD.

## Instrucciones de Ejecución

1. Crear y activar el entorno virtual:
   ```bash
   python -m venv venv
   source venv/bin/activate
