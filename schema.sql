-- =========================================================================
-- Database Schema: Inventory Management and Electronic Component Loan System
-- Engine: SQLite
-- =========================================================================

-- Habilitar llaves foráneas en SQLite
PRAGMA foreign_keys = ON;

-- 1. Tabla: usuarios
CREATE TABLE usuarios (
    user_id VARCHAR(10) CONSTRAINT pk_usuarios PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    rol VARCHAR(20) NOT NULL CHECK (rol IN ('administrator', 'student'))
);

-- 2. Tabla: inventario (Catálogo de componentes)
CREATE TABLE inventario (
    element_id VARCHAR(10) CONSTRAINT pk_inventario PRIMARY KEY,
    component_name VARCHAR(100) NOT NULL,
    category VARCHAR(50) NOT NULL,
    -- Cumple NFR-01: Restricción de stock no negativo a nivel de esquema
    quantity INTEGER NOT NULL CONSTRAINT ck_inventario_stock_positivo CHECK (quantity >= 0)
);

-- 3. Tabla: proyectos (Relación 1:N con usuarios)
CREATE TABLE proyectos (
    project_id VARCHAR(10) CONSTRAINT pk_proyectos PRIMARY KEY,
    project_name VARCHAR(100) NOT NULL,
    state VARCHAR(20) NOT NULL CHECK (state IN ('in_development', 'finished')),
    user_id VARCHAR(10) NOT NULL,
    CONSTRAINT fk_proyectos_usuarios FOREIGN KEY (user_id) REFERENCES usuarios(user_id)
);

-- 4. Tabla: solicitudes (Cabecera transaccional)
CREATE TABLE solicitudes (
    solicitud_id VARCHAR(10) CONSTRAINT pk_solicitudes PRIMARY KEY,
    emission_date DATE NOT NULL,
    state VARCHAR(20) NOT NULL CHECK (state IN ('pending', 'approved', 'returned')),
    project_id VARCHAR(10) NOT NULL,
    CONSTRAINT fk_solicitudes_proyectos FOREIGN KEY (project_id) REFERENCES proyectos(project_id)
);

-- 5. Tabla: detalle_prestamo (Resolución N:M entre solicitudes e inventario)
CREATE TABLE detalle_prestamo (
    solicitud_id VARCHAR(10) NOT NULL,
    element_id VARCHAR(10) NOT NULL,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    -- Cumple FR-03 y NFR-03: Devoluciones parciales acotadas al total solicitado
    returned_quantity INTEGER NOT NULL DEFAULT 0 CHECK (returned_quantity >= 0 AND returned_quantity <= quantity),
    CONSTRAINT pk_detalle_prestamo PRIMARY KEY (solicitud_id, element_id),
    CONSTRAINT fk_detalle_solicitudes FOREIGN KEY (solicitud_id) REFERENCES solicitudes(solicitud_id),
    CONSTRAINT fk_detalle_inventario FOREIGN KEY (element_id) REFERENCES inventario(element_id)
);

-- =========================================================================
-- Índices para optimizar JOINs (Cumple NFR-02)
-- =========================================================================
CREATE INDEX idx_proyectos_user_id ON proyectos(user_id);
CREATE INDEX idx_solicitudes_project_id ON solicitudes(project_id);
CREATE INDEX idx_detalle_element_id ON detalle_prestamo(element_id);

-- =========================================================================
-- Triggers de Negocio (Cumple FR-02, FR-04 y NFR-03)
-- =========================================================================

-- Trigger 1: Valida stock disponible y descuenta globalmente al insertar detalle (FR-02)
CREATE TRIGGER trg_detalle_prestamo_before_insert
BEFORE INSERT ON detalle_prestamo
FOR EACH ROW
BEGIN
    SELECT CASE
        WHEN (SELECT quantity FROM inventario WHERE element_id = NEW.element_id) < NEW.quantity
        THEN RAISE(ABORT, 'Error: Insufficient stock in inventory for this component.')
    END;
    UPDATE inventario 
    SET quantity = quantity - NEW.quantity 
    WHERE element_id = NEW.element_id;
END;

-- Trigger 2: Reintegra automáticamente al inventario las piezas devueltas (FR-04)
CREATE TRIGGER trg_detalle_prestamo_after_return
AFTER UPDATE OF returned_quantity ON detalle_prestamo
FOR EACH ROW
BEGIN
    UPDATE inventario
    SET quantity = quantity + (NEW.returned_quantity - OLD.returned_quantity)
    WHERE element_id = NEW.element_id;
END;
