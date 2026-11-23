USE laboratory_db;

-- ============================================================
-- 0. PREPARACION DE DATOS BASE (Ejecutar primero)
-- ============================================================
DELETE FROM detalle_prestamo WHERE solicitud_id IN ('S01', 'S02', 'S03', 'S04');
DELETE FROM registro_solicitudes WHERE solicitud_id IN ('S01', 'S02', 'S03', 'S04');
DELETE FROM proyectos WHERE project_id IN ('P01', 'P99');
DELETE FROM detalle_componente WHERE element_id IN ('E01', 'E02');
DELETE FROM inventario_actual WHERE element_id IN ('E01', 'E02');
DELETE FROM inventario_global WHERE element_id IN ('E01', 'E02');
DELETE FROM usuarios WHERE user_id IN ('U01', 'U02');

INSERT INTO usuarios (user_id, name, rol) VALUES
('U01', 'Roger Zambrano', 'student'),
('U02', 'Admin Laboratorio', 'administrator');

SELECT * FROM usuarios WHERE user_id IN ('U01', 'U02');


-- ============================================================
-- TC-01 (FR-01): Registro de proyecto e integridad referencial
-- ============================================================
-- Paso 1 (DEBE FUNCIONAR):
INSERT INTO proyectos (project_id, project_name, state, user_id)
VALUES ('P01', 'ALU 8-bit', 'in_development', 'U01');

-- Paso 2 (DEBE FALLAR - Foreign Key, usuario U99 no existe):
INSERT INTO proyectos (project_id, project_name, state, user_id)
VALUES ('P99', 'Proyecto Invalido', 'in_development', 'U99');

-- Verificar:
SELECT * FROM proyectos WHERE project_id = 'P01';


-- ============================================================
-- TC-02 (FR-02): Bloquear prestamo si supera el stock disponible
-- ============================================================
-- Precondiciones: E01 con total=10, disponible=5 y solicitud S01 pendiente
INSERT INTO inventario_global (element_id, component_name, category, total_quantity)
VALUES ('E01', 'EEPROM 28C256', 'ICs', 10);

UPDATE inventario_actual SET available_quantity = 5 WHERE element_id = 'E01';

INSERT INTO registro_solicitudes (solicitud_id, project_id, emission_date, due_date, state, is_fully_returned)
VALUES ('S01', 'P01', '2026-11-23', '2026-11-30', 'pending', FALSE);

-- Paso 1 (DEBE FALLAR - Trigger SQLSTATE 45000, pide 10 y solo hay 5):
INSERT INTO detalle_prestamo (solicitud_id, element_id, quantity)
VALUES ('S01', 'E01', 10);

-- Verificar que no se inserto nada:
SELECT * FROM detalle_prestamo WHERE solicitud_id = 'S01';


-- ============================================================
-- TC-03 (FR-03): Devoluciones parciales y cierre automatico
-- ============================================================
-- Precondiciones: Restaurar stock a 10, pedir 4 en S01 y aprobar
UPDATE inventario_actual SET available_quantity = 10 WHERE element_id = 'E01';

INSERT INTO detalle_prestamo (solicitud_id, element_id, quantity)
VALUES ('S01', 'E01', 4);

UPDATE registro_solicitudes
SET state = 'approved', approved_by = 'U02'
WHERE solicitud_id = 'S01';

-- Paso 1: Devolucion parcial (2 de 4)
UPDATE detalle_prestamo
SET returned_quantity = 2
WHERE solicitud_id = 'S01' AND element_id = 'E01';

-- Ver estado (debe estar en partial_return, is_fully_returned = 0):
SELECT solicitud_id, state, is_fully_returned, closed_date
FROM registro_solicitudes WHERE solicitud_id = 'S01';

-- Paso 2: Devolucion total (4 de 4)
UPDATE detalle_prestamo
SET returned_quantity = 4
WHERE solicitud_id = 'S01' AND element_id = 'E01';

-- Ver estado (debe pasar a returned, is_fully_returned = 1):
SELECT solicitud_id, state, is_fully_returned, closed_date
FROM registro_solicitudes WHERE solicitud_id = 'S01';


-- ============================================================
-- TC-04 (FR-04): Reposicion automatica de stock al devolver
-- ============================================================
-- Precondiciones: Dejar E01 en 9, aprobar prestamo S02 de 4 -> stock queda en 5
UPDATE inventario_actual SET available_quantity = 9 WHERE element_id = 'E01';

INSERT INTO registro_solicitudes (solicitud_id, project_id, emission_date, due_date, state, is_fully_returned)
VALUES ('S02', 'P01', '2026-11-23', '2026-11-30', 'pending', FALSE);

INSERT INTO detalle_prestamo (solicitud_id, element_id, quantity)
VALUES ('S02', 'E01', 4);

UPDATE registro_solicitudes
SET state = 'approved', approved_by = 'U02'
WHERE solicitud_id = 'S02';

-- Verificar stock antes de devolver (debe ser 5):
SELECT element_id, available_quantity FROM inventario_actual WHERE element_id = 'E01';

-- Paso 1: Devolver 3 unidades
UPDATE detalle_prestamo
SET returned_quantity = 3
WHERE solicitud_id = 'S02' AND element_id = 'E01';

-- Paso 2: Verificar stock despues de devolver (debe subir de 5 a 8):
SELECT element_id, available_quantity FROM inventario_actual WHERE element_id = 'E01';


-- ============================================================
-- TC-05 (NFR-01): Stock no negativo y limite de inventario global
-- ============================================================
-- Paso 1 (DEBE FALLAR - CHECK available_quantity >= 0):
UPDATE inventario_actual SET available_quantity = -1 WHERE element_id = 'E01';

-- Paso 2 (DEBE FALLAR - Trigger impide superar total_quantity = 10):
UPDATE inventario_actual SET available_quantity = 12 WHERE element_id = 'E01';

-- Verificar que el stock sigue intacto en 8:
SELECT g.element_id, g.total_quantity, a.available_quantity
FROM inventario_global g
JOIN inventario_actual a ON g.element_id = a.element_id
WHERE g.element_id = 'E01';


-- ============================================================
-- TC-06 (NFR-02): Verificar indices en llaves foraneas
-- ============================================================
SHOW INDEX FROM proyectos;
SHOW INDEX FROM registro_solicitudes;


-- ============================================================
-- TC-07 (NFR-03): Rollback atomico ante devolucion invalida
-- ============================================================
-- Precondicion: Nuevo prestamo S03 aprobado por 4 unidades (returned = 0)
INSERT INTO registro_solicitudes (solicitud_id, project_id, emission_date, due_date, state, is_fully_returned)
VALUES ('S03', 'P01', '2026-11-23', '2026-11-30', 'pending', FALSE);

INSERT INTO detalle_prestamo (solicitud_id, element_id, quantity)
VALUES ('S03', 'E01', 4);

UPDATE registro_solicitudes
SET state = 'approved', approved_by = 'U02'
WHERE solicitud_id = 'S03';

SELECT element_id, available_quantity FROM inventario_actual WHERE element_id = 'E01';

-- Paso 1 (DEBE FALLAR - CHECK returned_quantity <= quantity):
UPDATE detalle_prestamo
SET returned_quantity = 10
WHERE solicitud_id = 'S03' AND element_id = 'E01';

-- Verificar que el stock NO cambio:
SELECT element_id, available_quantity FROM inventario_actual WHERE element_id = 'E01';


-- ============================================================
-- TC-08 (FR-05): Validacion de rol admin y descuento al aprobar
-- ============================================================
-- Precondicion: Solicitud S04 pendiente pidiendo 2 unidades de E01
INSERT INTO registro_solicitudes (solicitud_id, project_id, emission_date, due_date, state, is_fully_returned)
VALUES ('S04', 'P01', '2026-11-23', '2026-11-30', 'pending', FALSE);

INSERT INTO detalle_prestamo (solicitud_id, element_id, quantity)
VALUES ('S04', 'E01', 2);

-- Stock antes de aprobar:
SELECT element_id, available_quantity FROM inventario_actual WHERE element_id = 'E01';

-- Paso 1 (DEBE FALLAR - U01 es student, no administrator):
UPDATE registro_solicitudes
SET state = 'approved', approved_by = 'U01'
WHERE solicitud_id = 'S04';

-- Paso 2 (DEBE FUNCIONAR - U02 es administrator y descuenta 2 unidades):
UPDATE registro_solicitudes
SET state = 'approved', approved_by = 'U02'
WHERE solicitud_id = 'S04';

-- Verificar stock despues de aprobar (debe haber bajado en 2):
SELECT element_id, available_quantity FROM inventario_actual WHERE element_id = 'E01';


-- ============================================================
-- TC-09 (FR-05): Sincronizacion automatica y part_number unico
-- ============================================================
-- Paso 1: Insertar E02 con total = 8 y verificar creacion automatica en inventario_actual
INSERT INTO inventario_global (element_id, component_name, category, total_quantity)
VALUES ('E02', 'Timer 555', 'ICs', 8);

SELECT * FROM inventario_actual WHERE element_id = 'E02';

-- Paso 2: Insertar datasheet en E01 y luego repetir part_number en E02
INSERT INTO detalle_componente (element_id, manufacturer, part_number, package_type, operating_voltage)
VALUES ('E01', 'Texas Instruments', 'NE555P', 'DIP-8', '4.5V-16V');

-- Esta linea DEBE FALLAR (restriccion UNIQUE en part_number):
INSERT INTO detalle_componente (element_id, manufacturer, part_number, package_type, operating_voltage)
VALUES ('E02', 'Texas Instruments', 'NE555P', 'DIP-8', '4.5V-16V');


-- ============================================================
-- LIMPIEZA OPCIONAL (Ejecutar solo al terminar las pruebas)
-- ============================================================
-- DELETE FROM detalle_prestamo WHERE solicitud_id IN ('S01', 'S02', 'S03', 'S04');
-- DELETE FROM registro_solicitudes WHERE solicitud_id IN ('S01', 'S02', 'S03', 'S04');
-- DELETE FROM proyectos WHERE project_id IN ('P01', 'P99');
-- DELETE FROM detalle_componente WHERE element_id IN ('E01', 'E02');
-- DELETE FROM inventario_actual WHERE element_id IN ('E01', 'E02');
-- DELETE FROM inventario_global WHERE element_id IN ('E01', 'E02');
-- DELETE FROM usuarios WHERE user_id IN ('U01', 'U02');
