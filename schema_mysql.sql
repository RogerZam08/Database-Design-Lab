-- =========================================================================
-- Database Schema: Hardware Inventory & Electronic Component Loan System
-- Engine: MySQL 8.0+ (InnoDB)
-- =========================================================================

CREATE DATABASE IF NOT EXISTS laboratory_db
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE laboratory_db;

-- 1. Tabla: usuarios
CREATE TABLE usuarios (
    user_id VARCHAR(10) NOT NULL,
    name VARCHAR(100) NOT NULL,
    rol VARCHAR(20) NOT NULL,
    CONSTRAINT pk_usuarios PRIMARY KEY (user_id),
    CONSTRAINT ck_usuarios_rol CHECK (rol IN ('administrator', 'student'))
) ENGINE=InnoDB;

-- 2. Tabla: proyectos (Relación 1:N con usuarios)
CREATE TABLE proyectos (
    project_id VARCHAR(10) NOT NULL,
    project_name VARCHAR(100) NOT NULL,
    state VARCHAR(20) NOT NULL DEFAULT 'in_development',
    user_id VARCHAR(10) NOT NULL,
    CONSTRAINT pk_proyectos PRIMARY KEY (project_id),
    CONSTRAINT ck_proyectos_state CHECK (state IN ('in_development', 'finished')),
    CONSTRAINT fk_proyectos_usuarios FOREIGN KEY (user_id) REFERENCES usuarios(user_id)
) ENGINE=InnoDB;

-- 3. Tabla: inventario_global (Patrimonio total del laboratorio)
CREATE TABLE inventario_global (
    element_id VARCHAR(10) NOT NULL,
    component_name VARCHAR(100) NOT NULL,
    category VARCHAR(50) NOT NULL,
    total_quantity INT NOT NULL,
    CONSTRAINT pk_inventario_global PRIMARY KEY (element_id),
    CONSTRAINT ck_inventario_global_total CHECK (total_quantity >= 0)
) ENGINE=InnoDB;

-- 4. Tabla: inventario_actual (Stock disponible en tiempo real - Relación 1:1)
CREATE TABLE inventario_actual (
    element_id VARCHAR(10) NOT NULL,
    available_quantity INT NOT NULL,
    last_updated DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT pk_inventario_actual PRIMARY KEY (element_id),
    CONSTRAINT ck_inventario_actual_stock CHECK (available_quantity >= 0),
    CONSTRAINT fk_inv_actual_global FOREIGN KEY (element_id)
        REFERENCES inventario_global(element_id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- 5. Tabla: detalle_componente (Ficha técnica / Datasheet - Relación 1:1)
CREATE TABLE detalle_componente (
    element_id VARCHAR(10) NOT NULL,
    manufacturer VARCHAR(80),
    part_number VARCHAR(50),
    package_type VARCHAR(30),
    operating_voltage VARCHAR(30),
    technical_specs TEXT,
    datasheet_url VARCHAR(255),
    CONSTRAINT pk_detalle_componente PRIMARY KEY (element_id),
    CONSTRAINT uq_detalle_part_number UNIQUE (part_number),
    CONSTRAINT fk_detalle_comp_global FOREIGN KEY (element_id)
        REFERENCES inventario_global(element_id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- 6. Tabla: registro_solicitudes (Historial y control de préstamos)
CREATE TABLE registro_solicitudes (
    solicitud_id VARCHAR(10) NOT NULL,
    project_id VARCHAR(10) NOT NULL,
    approved_by VARCHAR(10) NULL,
    emission_date DATE NOT NULL,
    due_date DATE NOT NULL,
    closed_date DATE NULL,
    state VARCHAR(20) NOT NULL DEFAULT 'pending',
    is_fully_returned BOOLEAN NOT NULL DEFAULT FALSE,
    CONSTRAINT pk_registro_solicitudes PRIMARY KEY (solicitud_id),
    CONSTRAINT ck_solicitudes_state CHECK (
        state IN ('pending', 'approved', 'partial_return', 'returned', 'rejected', 'overdue')
    ),
    CONSTRAINT ck_solicitudes_dates CHECK (due_date >= emission_date),
    CONSTRAINT fk_solicitudes_proyectos FOREIGN KEY (project_id) REFERENCES proyectos(project_id),
    CONSTRAINT fk_solicitudes_admin FOREIGN KEY (approved_by) REFERENCES usuarios(user_id)
) ENGINE=InnoDB;

-- 7. Tabla: detalle_prestamo (Resolución N:M entre solicitudes e inventario)
CREATE TABLE detalle_prestamo (
    solicitud_id VARCHAR(10) NOT NULL,
    element_id VARCHAR(10) NOT NULL,
    quantity INT NOT NULL,
    returned_quantity INT NOT NULL DEFAULT 0,
    CONSTRAINT pk_detalle_prestamo PRIMARY KEY (solicitud_id, element_id),
    CONSTRAINT ck_detalle_quantity CHECK (quantity > 0),
    CONSTRAINT ck_detalle_returned CHECK (returned_quantity >= 0 AND returned_quantity <= quantity),
    CONSTRAINT fk_detalle_solicitudes FOREIGN KEY (solicitud_id)
        REFERENCES registro_solicitudes(solicitud_id) ON DELETE CASCADE,
    CONSTRAINT fk_detalle_inventario FOREIGN KEY (element_id)
        REFERENCES inventario_global(element_id)
) ENGINE=InnoDB;

-- =========================================================================
-- Índices para optimizar JOINs y consultas de auditoría
-- =========================================================================
CREATE INDEX idx_proyectos_user_id ON proyectos(user_id);
CREATE INDEX idx_solicitudes_project_id ON registro_solicitudes(project_id);
CREATE INDEX idx_solicitudes_approved_by ON registro_solicitudes(approved_by);
CREATE INDEX idx_solicitudes_state ON registro_solicitudes(state);
CREATE INDEX idx_detalle_element_id ON detalle_prestamo(element_id);

-- =========================================================================
-- Triggers de Negocio (MySQL 8.0+)
-- =========================================================================
DELIMITER //

-- Trigger 1: Sincroniza automáticamente inventario_actual al registrar un componente global
CREATE TRIGGER trg_inv_global_after_insert
AFTER INSERT ON inventario_global
FOR EACH ROW
BEGIN
    INSERT INTO inventario_actual (element_id, available_quantity)
    VALUES (NEW.element_id, NEW.total_quantity);
END//

-- Trigger 2: Regla de oro -> available_quantity nunca puede superar total_quantity
CREATE TRIGGER trg_inv_actual_before_update
BEFORE UPDATE ON inventario_actual
FOR EACH ROW
BEGIN
    DECLARE v_total INT;
    SELECT total_quantity INTO v_total
    FROM inventario_global
    WHERE element_id = NEW.element_id;

    IF NEW.available_quantity > v_total THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Error: Available stock cannot exceed global laboratory inventory.';
    END IF;
END//

-- Trigger 3: Al agregar ítems a una solicitud, valida que esté pendiente y haya stock
-- (NO descuenta aún; el descuento ocurre al aprobar la solicitud)
CREATE TRIGGER trg_detalle_prestamo_before_insert
BEFORE INSERT ON detalle_prestamo
FOR EACH ROW
BEGIN
    DECLARE v_available INT;
    DECLARE v_state VARCHAR(20);

    SELECT state INTO v_state
    FROM registro_solicitudes
    WHERE solicitud_id = NEW.solicitud_id;

    IF v_state <> 'pending' THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Error: Items can only be added to pending loan requests.';
    END IF;

    SELECT available_quantity INTO v_available
    FROM inventario_actual
    WHERE element_id = NEW.element_id;

    IF v_available < NEW.quantity THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Error: Requested quantity exceeds available stock.';
    END IF;
END//

-- Trigger 4: Valida aprobación (debe aprobar un admin y haber stock suficiente)
CREATE TRIGGER trg_solicitudes_before_approve
BEFORE UPDATE ON registro_solicitudes
FOR EACH ROW
BEGIN
    DECLARE v_rol VARCHAR(20);
    DECLARE v_insufficient INT DEFAULT 0;

    IF OLD.state = 'pending' AND NEW.state = 'approved' THEN
        -- Verificar que haya un aprobador con rol administrator
        IF NEW.approved_by IS NULL THEN
            SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Error: An administrator ID (approved_by) is required to approve a request.';
        END IF;

        SELECT rol INTO v_rol FROM usuarios WHERE user_id = NEW.approved_by;
        IF v_rol <> 'administrator' THEN
            SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Error: Only users with administrator role can approve requests.';
        END IF;

        -- Verificar stock de todos los componentes de la solicitud
        SELECT COUNT(*) INTO v_insufficient
        FROM detalle_prestamo dp
        JOIN inventario_actual ia ON dp.element_id = ia.element_id
        WHERE dp.solicitud_id = NEW.solicitud_id
          AND dp.quantity > ia.available_quantity;

        IF v_insufficient > 0 THEN
            SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Error: Insufficient stock to approve one or more components in this request.';
        END IF;
    END IF;
END//

-- Trigger 5: Descuenta el stock real en inventario_actual al aprobarse la solicitud
CREATE TRIGGER trg_solicitudes_after_approve
AFTER UPDATE ON registro_solicitudes
FOR EACH ROW
BEGIN
    IF OLD.state = 'pending' AND NEW.state = 'approved' THEN
        UPDATE inventario_actual ia
        JOIN detalle_prestamo dp ON ia.element_id = dp.element_id
        SET ia.available_quantity = ia.available_quantity - dp.quantity
        WHERE dp.solicitud_id = NEW.solicitud_id;
    END IF;
END//

-- Trigger 6: Reintegra stock en devoluciones y cierra la solicitud si ya devolvió todo
CREATE TRIGGER trg_detalle_prestamo_after_return
AFTER UPDATE ON detalle_prestamo
FOR EACH ROW
BEGIN
    DECLARE v_pending_items INT DEFAULT 0;

    IF NEW.returned_quantity <> OLD.returned_quantity THEN
        -- Sumar la diferencia devuelta al inventario actual
        UPDATE inventario_actual
        SET available_quantity = available_quantity + (NEW.returned_quantity - OLD.returned_quantity)
        WHERE element_id = NEW.element_id;

        -- Verificar si todavía quedan ítems sin completar en esta solicitud
        SELECT COUNT(*) INTO v_pending_items
        FROM detalle_prestamo
        WHERE solicitud_id = NEW.solicitud_id
          AND returned_quantity < quantity;

        IF v_pending_items = 0 THEN
            UPDATE registro_solicitudes
            SET state = 'returned',
                is_fully_returned = TRUE,
                closed_date = CURDATE()
            WHERE solicitud_id = NEW.solicitud_id;
        ELSE
            UPDATE registro_solicitudes
            SET state = 'partial_return',
                is_fully_returned = FALSE,
                closed_date = NULL
            WHERE solicitud_id = NEW.solicitud_id;
        END IF;
    END IF;
END//

DELIMITER ;
