-- Activar verificación estricta de llaves foráneas en SQLite
PRAGMA foreign_keys = ON;

-- Limpiar tablas por si acaso (para correr el script desde cero)
DELETE FROM detalle_prestamo;
DELETE FROM solicitudes;
DELETE FROM proyectos;
DELETE FROM inventario;
DELETE FROM usuarios;

-- Insertar los datos base (Precondiciones de TC-01 y TC-02)
INSERT INTO usuarios (user_id, name, rol) VALUES ('U01', 'Roger Zambrano', 'student');
INSERT INTO inventario (element_id, component_name, category, quantity) VALUES ('E01', 'EEPROM', 'ICs', 5);

-- ==========================================================
-- PRECONDICIONES: Insertamos los datos base
-- ==========================================================
INSERT INTO usuarios (user_id, name, rol) VALUES ('U01', 'Roger Zambrano', 'student');
INSERT INTO inventario (element_id, component_name, category, quantity) VALUES ('E01', 'EEPROM', 'ICs', 5);

-- ==========================================================
-- TC-01: Registro de proyecto y llave foránea (FR-01)
-- ==========================================================
-- 1. Éxito:
INSERT INTO proyectos (project_id, project_name, state, user_id) VALUES ('P01', 'ALU 8-bits', 'in_development', 'U01');
-- 2. Debe fallar (descomenta para probar el error de FOREIGN KEY constraint failed):
-- INSERT INTO proyectos VALUES ('P02', 'Error', 'in_development', 'U99');


-- ==========================================================
-- TC-02: Evitar préstamo si excede el stock (FR-02)
-- ==========================================================
INSERT INTO solicitudes (solicitud_id, emission_date, state, project_id) VALUES ('S01', '2026-11-16', 'pending', 'P01');

-- Debe fallar (Pide 10, pero solo hay 5). El TRIGGER abortará la operación:
-- INSERT INTO detalle_prestamo (solicitud_id, element_id, quantity) VALUES ('S01', 'E01', 10);


-- ==========================================================
-- TC-03 y TC-04: Préstamo exitoso, descuentos y devoluciones
-- ==========================================================
-- Hacemos un préstamo válido de 4 unidades (el stock global bajará de 5 a 1):
INSERT INTO detalle_prestamo (solicitud_id, element_id, quantity, returned_quantity) VALUES ('S01', 'E01', 4, 0);

-- Verificamos el stock tras el préstamo (Debe imprimir 1):
SELECT 'Stock tras prestar 4:' AS Info, quantity FROM inventario WHERE element_id = 'E01';

-- TC-03 (Paso 1): Devolución parcial (Devuelve 2, el stock global sube a 3)
UPDATE detalle_prestamo SET returned_quantity = 2 WHERE solicitud_id = 'S01' AND element_id = 'E01';
SELECT 'Stock tras devolver 2:' AS Info, quantity FROM inventario WHERE element_id = 'E01';

-- TC-03 (Paso 2) / TC-04: Devolución total (Devuelve los 4, el stock regresa a 5)
UPDATE detalle_prestamo SET returned_quantity = 4 WHERE solicitud_id = 'S01' AND element_id = 'E01';
SELECT 'Stock tras devolver todo:' AS Info, quantity FROM inventario WHERE element_id = 'E01';


-- ==========================================================
-- TC-05: Restricción de stock no negativo (NFR-01)
-- ==========================================================
-- Debe fallar con CHECK constraint failed:
-- UPDATE inventario SET quantity = -1 WHERE element_id = 'E01';


-- ==========================================================
-- TC-07: Error por devolver más de lo prestado (NFR-03)
-- ==========================================================
-- Debe fallar (solo prestó 4, no puede devolver 10):
-- UPDATE detalle_prestamo SET returned_quantity = 10 WHERE solicitud_id = 'S01' AND element_id = 'E01';


-- ==========================================================
-- TC-06: Verificación de Índices (NFR-02)
-- ==========================================================
-- Imprime la lista de índices activos para demostrar que existen:
PRAGMA index_list('proyectos');
PRAGMA index_list('solicitudes');
