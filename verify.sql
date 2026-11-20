-- ============================================================================
-- SCRIPT DE PRUEBAS MANUALES - INVENTARIO DE LABORATORIO
-- Este archivo es de consulta. Copiar y ejecutar bloque por bloque.
-- ============================================================================


-- ============================================================================
-- 0. PRECONDICIONES (Ejecutar esto primero antes de cualquier prueba)
-- ============================================================================
-- Activa la verificación estricta de llaves foráneas en SQLite
PRAGMA foreign_keys = ON;

-- Limpia datos basura de pruebas anteriores (en orden para no romper dependencias)
DELETE FROM detalle_prestamo;
DELETE FROM solicitudes;
DELETE FROM proyectos;
DELETE FROM inventario;
DELETE FROM usuarios;

-- Inserta los datos base requeridos por los TC
INSERT INTO usuarios (user_id, name, rol) VALUES ('U01', 'Roger Zambrano', 'student');
INSERT INTO inventario (element_id, component_name, category, quantity) VALUES ('E01', 'EEPROM', 'ICs', 5);
-- ============================================================================



-- ============================================================================
-- TC-01 (FR-01): Registro de proyecto y llave foránea
-- ============================================================================
-- PASO 1: Inserción válida (Debe registrar el proyecto correctamente)
INSERT INTO proyectos (project_id, project_name, state, user_id) 
VALUES ('P01', 'ALU 8-bits', 'in_development', 'U01');

-- PASO 2: Inserción inválida 
-- DEBE FALLAR CON: "Runtime error: FOREIGN KEY constraint failed"
INSERT INTO proyectos (project_id, project_name, state, user_id) 
VALUES ('P02', 'Adder', 'in_development', 'U99');
-- ============================================================================



-- ============================================================================
-- TC-02 (FR-02): Bloquear préstamo si excede el stock (Trigger BEFORE INSERT)
-- ============================================================================
-- Precondición: Crear la cabecera de la solicitud
INSERT INTO solicitudes (solicitud_id, emission_date, state, project_id) 
VALUES ('S01', '2026-11-16', 'pending', 'P01');

-- PASO: Intentar pedir 10 unidades de E01 cuando el stock global es 5.
-- DEBE FALLAR CON: "Runtime error: Error: Insufficient stock in inventory..."
INSERT INTO detalle_prestamo (solicitud_id, element_id, quantity) 
VALUES ('S01', 'E01', 10);
-- ============================================================================



-- ============================================================================
-- TC-03 y TC-04 (FR-03 y FR-04): Préstamos parciales y Trigger AFTER UPDATE
-- ============================================================================
-- Precondición: Hacer un préstamo válido de 4 unidades. 
-- El Trigger BEFORE INSERT dejará el stock global en 1.
INSERT INTO detalle_prestamo (solicitud_id, element_id, quantity, returned_quantity) 
VALUES ('S01', 'E01', 4, 0);

-- Comprobar estado inicial del inventario (Debe mostrar 1)
SELECT quantity AS Stock_Actual_DebeSer_1 FROM inventario WHERE element_id = 'E01';

-- TC-03 (Paso 1): El estudiante devuelve 2 unidades (Devolución parcial)
UPDATE detalle_prestamo SET returned_quantity = 2 WHERE solicitud_id = 'S01' AND element_id = 'E01';

-- TC-04 (Verificación): El stock global sube automáticamente de 1 a 3
SELECT quantity AS Stock_Actual_DebeSer_3 FROM inventario WHERE element_id = 'E01';

-- TC-03 (Paso 2): El estudiante devuelve las 2 unidades restantes (Total devuelto = 4)
UPDATE detalle_prestamo SET returned_quantity = 4 WHERE solicitud_id = 'S01' AND element_id = 'E01';

-- TC-04 (Verificación): El stock global regresa automáticamente a 5
SELECT quantity AS Stock_Actual_DebeSer_5 FROM inventario WHERE element_id = 'E01';
-- ============================================================================



-- ============================================================================
-- TC-05 (NFR-01): Restricción de stock no negativo en Inventario (CHECK constraint)
-- ============================================================================
-- PASO: Intentar alterar el stock directamente a un número negativo
-- DEBE FALLAR CON: "Runtime error: CHECK constraint failed: ck_inventario_stock_positivo"
UPDATE inventario SET quantity = -1 WHERE element_id = 'E01';
-- ============================================================================



-- ============================================================================
-- TC-06 (NFR-02): Verificación de creación de índices
-- ============================================================================
-- PASO: Listar los índices internos de SQLite para estas tablas.
-- DEBE MOSTRAR: idx_proyectos_user_id e idx_solicitudes_project_id
PRAGMA index_list('proyectos');
PRAGMA index_list('solicitudes');
-- ============================================================================



-- ============================================================================
-- TC-07 (NFR-03): Consistencia transaccional, bloquear devoluciones fantasma
-- ============================================================================
-- Precondición: Regresamos el contador de devoluciones a 0 para la prueba
UPDATE detalle_prestamo SET returned_quantity = 0 WHERE solicitud_id = 'S01' AND element_id = 'E01';

-- PASO: Intentar devolver 10 unidades cuando solo se prestaron 4.
-- DEBE FALLAR CON: "Runtime error: CHECK constraint failed..." (Stock y préstamo quedan intactos)
UPDATE detalle_prestamo SET returned_quantity = 10 WHERE solicitud_id = 'S01' AND element_id = 'E01';
-- ============================================================================
