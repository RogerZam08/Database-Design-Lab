# Laboratory Hardware Inventory & Loan System

Transactional system for managing electronic component inventory, technical datasheets, academic projects, and loan requests with administrator approval.

## Tech Stack
- **Database:** MySQL 8.0 (`InnoDB`) with triggers, `CHECK` constraints, and foreign key indexes (`schema_mysql.sql`).
- **Backend API:** Python, Flask, and Flask-SQLAlchemy (`app.py`).
- **Frontend GUI:** Streamlit (`gui.py`).
- **Containerization:** Docker Compose (`docker-compose.yml`).

## Quick Start (Docker + Local Python)

1. **Start MySQL 8 in Docker** (automatically initializes `laboratory_db` from `schema_mysql.sql`):
   ```bash
   docker compose up -d
