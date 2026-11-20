# ⚡ Laboratory Hardware Inventory & Loan System

Transactional system for managing electronic component inventory, technical datasheets, academic projects, and loan requests with administrator approval.

---

## 🛠️ Tech Stack

| Layer | Technology | Key File |
| :--- | :--- | :--- |
| **Database** | MySQL 8.0 (`InnoDB`) with triggers, `CHECK` constraints, and FK indexes | `schema_mysql.sql` |
| **Backend API** | Python 3, Flask, and Flask-SQLAlchemy | `app.py` |
| **Frontend GUI** | Streamlit | `gui.py` |
| **Containerization** | Docker Compose | `docker-compose.yml` |

---

## 🚀 How to Start Everything & Open the Web App

You need **two terminals** open inside the project folder (`PROYECTO_LAB`).

### Step 1: Start the MySQL Database (Docker)
In **Terminal 1**, start the MySQL 8 container (automatically creates the target database and loads `schema_mysql.sql` on first run):
```bash
docker compose up -d
```

Verify that the container is active:
```bash
docker ps
```

### Step 2: Activate Virtual Environment & Install Dependencies
In **Terminal 1**, create and activate your virtual environment (`venv`), then install the required packages:
```bash
python3 -m venv venv
source venv/bin/activate.fish   # On bash/zsh: source venv/bin/activate
pip install -r requirements.txt
```

### Step 3: Start the Backend API (Terminal 1)
With `venv` active in **Terminal 1**, configure your database connection via environment variable (`DATABASE_URL`) if needed and start Flask on port `5000`:
```bash
# Optional: set your own connection string instead of hardcoding credentials
# export DATABASE_URL="mysql+pymysql://<db_user>:<your_db_password>@127.0.0.1:3306/<db_name>"
python app.py
```
> Keep this terminal open. The API listens at `[http://127.0.0.1:5000/api](http://127.0.0.1:5000/api)` (main routes: `/inventario`, `/usuarios`, `/proyectos`, `/solicitudes`).

### Step 4: Start the Web Interface / GUI (Terminal 2)
Open a **second terminal**, navigate to the project folder, activate `venv`, and run Streamlit:
```bash
cd /path/to/PROYECTO_LAB
source venv/bin/activate.fish   # On bash/zsh: source venv/bin/activate
streamlit run gui.py
```

### Step 5: Open the Web Page in Your Browser
Once Streamlit starts, open either URL in your browser (Streamlit usually opens it automatically):
* **Local URL:** `http://localhost:8501` (or `[http://127.0.0.1:8501](http://127.0.0.1:8501)`)
* **Network / LAN URL:** Check the `Network URL` printed in Terminal 2 (e.g., `[http://192.168.](http://192.168.)x.x:8501`) to open it from another device on the same network.

---

## 🧪 Quick End-to-End Test in the Web App

1. **Usuarios y Proyectos:** Create at least one `student`, one `administrator`, and one academic project.
2. **Agregar Componente:** Register a component (with optional datasheet fields); its available stock is initialized automatically in `inventario_actual`.
3. **Nueva Solicitud:** Submit a loan request (`pending` state).
4. **Panel Administrador:** **Approve** the request (deducting real-time stock) and later register **partial or full returns** (replenishing stock and closing the loan automatically when all units are returned).

---

## 🔐 Database Configuration (Without Hardcoding Secrets)

| Parameter | Value / Placeholder |
| :--- | :--- |
| **Host / Port** | `127.0.0.1:3306` |
| **Database** | `<db_name>` (e.g., `laboratory_db`) |
| **User** | `<db_user>` |
| **Password** | Set locally via environment variables or `.env` (never commit real passwords) |

---

## 🛑 Stopping Everything Safely

1. Press `Ctrl + C` in **Terminal 2** (Streamlit) and **Terminal 1** (Flask).
2. Stop the MySQL container without losing persisted data:
   ```bash
   docker compose stop
   ```

> **Note:** Avoid running `docker compose down -v` unless you intentionally want to wipe the persisted database volume.
