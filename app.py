import os
from datetime import date, datetime
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError, OperationalError

app = Flask(__name__)

# Conexión a MySQL (permite sobrescribir con variable de entorno DATABASE_URL si se desea)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
    'DATABASE_URL',
    'mysql+pymysql://lab_user:lab_password@127.0.0.1:3306/laboratory_db'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ==========================================
# UTILIDAD PARA EXTRAER ERRORES DE MYSQL
# ==========================================
def extract_db_error(err):
    """Extrae el mensaje limpio enviado por triggers (SIGNAL 45000) o constraints."""
    if hasattr(err, 'orig') and err.orig and len(err.orig.args) > 1:
        return err.orig.args[1]
    return str(err)

def clean_optional(value):
    """Convierte strings vacíos en None para evitar choques en columnas UNIQUE."""
    if value is None:
        return None
    val = str(value).strip()
    return val if val else None

# ==========================================
# MODELOS (Mapeo de las 7 tablas en MySQL)
# ==========================================
class Usuario(db.Model):
    __tablename__ = 'usuarios'
    user_id = db.Column(db.String(10), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    rol = db.Column(db.String(20), nullable=False)

    def to_dict(self):
        return {'user_id': self.user_id, 'name': self.name, 'rol': self.rol}

class Proyecto(db.Model):
    __tablename__ = 'proyectos'
    project_id = db.Column(db.String(10), primary_key=True)
    project_name = db.Column(db.String(100), nullable=False)
    state = db.Column(db.String(20), nullable=False, default='in_development')
    user_id = db.Column(db.String(10), db.ForeignKey('usuarios.user_id'), nullable=False)

    def to_dict(self):
        return {
            'project_id': self.project_id,
            'project_name': self.project_name,
            'state': self.state,
            'user_id': self.user_id
        }

class InventarioGlobal(db.Model):
    __tablename__ = 'inventario_global'
    element_id = db.Column(db.String(10), primary_key=True)
    component_name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    total_quantity = db.Column(db.Integer, nullable=False)

    # Relaciones 1:1
    stock_actual = db.relationship('InventarioActual', backref='global_item', uselist=False, cascade='all, delete-orphan')
    datasheet = db.relationship('DetalleComponente', backref='global_item', uselist=False, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'element_id': self.element_id,
            'component_name': self.component_name,
            'category': self.category,
            'total_quantity': self.total_quantity,
            'available_quantity': self.stock_actual.available_quantity if self.stock_actual else 0,
            'last_updated': self.stock_actual.last_updated.isoformat() if self.stock_actual and self.stock_actual.last_updated else None,
            'datasheet': self.datasheet.to_dict() if self.datasheet else None
        }

class InventarioActual(db.Model):
    __tablename__ = 'inventario_actual'
    element_id = db.Column(db.String(10), db.ForeignKey('inventario_global.element_id'), primary_key=True)
    available_quantity = db.Column(db.Integer, nullable=False)
    last_updated = db.Column(db.DateTime)

class DetalleComponente(db.Model):
    __tablename__ = 'detalle_componente'
    element_id = db.Column(db.String(10), db.ForeignKey('inventario_global.element_id'), primary_key=True)
    manufacturer = db.Column(db.String(80))
    part_number = db.Column(db.String(50), unique=True)
    package_type = db.Column(db.String(30))
    operating_voltage = db.Column(db.String(30))
    technical_specs = db.Column(db.Text)
    datasheet_url = db.Column(db.String(255))

    def to_dict(self):
        return {
            'manufacturer': self.manufacturer,
            'part_number': self.part_number,
            'package_type': self.package_type,
            'operating_voltage': self.operating_voltage,
            'technical_specs': self.technical_specs,
            'datasheet_url': self.datasheet_url
        }

class RegistroSolicitud(db.Model):
    __tablename__ = 'registro_solicitudes'
    solicitud_id = db.Column(db.String(10), primary_key=True)
    project_id = db.Column(db.String(10), db.ForeignKey('proyectos.project_id'), nullable=False)
    approved_by = db.Column(db.String(10), db.ForeignKey('usuarios.user_id'), nullable=True)
    emission_date = db.Column(db.Date, nullable=False)
    due_date = db.Column(db.Date, nullable=False)
    closed_date = db.Column(db.Date, nullable=True)
    state = db.Column(db.String(20), nullable=False, default='pending')
    is_fully_returned = db.Column(db.Boolean, nullable=False, default=False)

    detalles = db.relationship('DetallePrestamo', backref='solicitud', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'solicitud_id': self.solicitud_id,
            'project_id': self.project_id,
            'approved_by': self.approved_by,
            'emission_date': self.emission_date.isoformat() if self.emission_date else None,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'closed_date': self.closed_date.isoformat() if self.closed_date else None,
            'state': self.state,
            'is_fully_returned': bool(self.is_fully_returned),
            'items': [d.to_dict() for d in self.detalles]
        }

class DetallePrestamo(db.Model):
    __tablename__ = 'detalle_prestamo'
    solicitud_id = db.Column(db.String(10), db.ForeignKey('registro_solicitudes.solicitud_id'), primary_key=True)
    element_id = db.Column(db.String(10), db.ForeignKey('inventario_global.element_id'), primary_key=True)
    quantity = db.Column(db.Integer, nullable=False)
    returned_quantity = db.Column(db.Integer, nullable=False, default=0)

    def to_dict(self):
        return {
            'solicitud_id': self.solicitud_id,
            'element_id': self.element_id,
            'quantity': self.quantity,
            'returned_quantity': self.returned_quantity
        }

# ==========================================
# ENDPOINTS: INVENTARIO (GLOBAL + ACTUAL + DATASHEET)
# ==========================================
@app.route('/api/inventario', methods=['GET'])
def get_inventory():
    items = InventarioGlobal.query.all()
    return jsonify([item.to_dict() for item in items]), 200

@app.route('/api/inventario/<element_id>', methods=['GET'])
def get_item(element_id):
    item = db.session.get(InventarioGlobal, element_id)
    if not item:
        return jsonify({'error': 'Component not found'}), 404
    return jsonify(item.to_dict()), 200

@app.route('/api/inventario', methods=['POST'])
def add_item():
    data = request.get_json()
    try:
        nuevo_global = InventarioGlobal(
            element_id=data['element_id'],
            component_name=data['component_name'],
            category=data['category'],
            total_quantity=data['total_quantity']
        )
        db.session.add(nuevo_global)
        # Flush ejecuta el INSERT y dispara trg_inv_global_after_insert (crea inventario_actual)
        db.session.flush()

        # Si el cliente envió ficha técnica, la guardamos en detalle_componente
        ds = data.get('datasheet')
        if ds and any(clean_optional(v) for v in ds.values()):
            detalle = DetalleComponente(
                element_id=data['element_id'],
                manufacturer=clean_optional(ds.get('manufacturer')),
                part_number=clean_optional(ds.get('part_number')),
                package_type=clean_optional(ds.get('package_type')),
                operating_voltage=clean_optional(ds.get('operating_voltage')),
                technical_specs=clean_optional(ds.get('technical_specs')),
                datasheet_url=clean_optional(ds.get('datasheet_url'))
            )
            db.session.add(detalle)

        db.session.commit()
        db.session.refresh(nuevo_global)  # Recarga inventario_actual creado por el trigger
        return jsonify({'message': 'Component created successfully', 'item': nuevo_global.to_dict()}), 201
    except (IntegrityError, OperationalError) as e:
        db.session.rollback()
        return jsonify({'error': extract_db_error(e)}), 400

@app.route('/api/inventario/<element_id>', methods=['PUT'])
def update_item(element_id):
    item = db.session.get(InventarioGlobal, element_id)
    if not item:
        return jsonify({'error': 'Component not found'}), 404

    data = request.get_json()
    if 'component_name' in data:
        item.component_name = data['component_name']
    if 'category' in data:
        item.category = data['category']
    if 'total_quantity' in data:
        item.total_quantity = data['total_quantity']
    if 'available_quantity' in data and item.stock_actual:
        item.stock_actual.available_quantity = data['available_quantity']

    if 'datasheet' in data and isinstance(data['datasheet'], dict):
        ds = data['datasheet']
        if not item.datasheet:
            item.datasheet = DetalleComponente(element_id=element_id)
        for field in ['manufacturer', 'part_number', 'package_type', 'operating_voltage', 'technical_specs', 'datasheet_url']:
            if field in ds:
                setattr(item.datasheet, field, clean_optional(ds[field]))

    try:
        db.session.commit()
        return jsonify({'message': 'Component updated successfully', 'item': item.to_dict()}), 200
    except (IntegrityError, OperationalError) as e:
        db.session.rollback()
        return jsonify({'error': extract_db_error(e)}), 400

@app.route('/api/inventario/<element_id>', methods=['DELETE'])
def delete_item(element_id):
    item = db.session.get(InventarioGlobal, element_id)
    if not item:
        return jsonify({'error': 'Component not found'}), 404
    try:
        db.session.delete(item)
        db.session.commit()
        return jsonify({'message': 'Component deleted successfully'}), 200
    except (IntegrityError, OperationalError) as e:
        db.session.rollback()
        return jsonify({'error': extract_db_error(e)}), 400

# ==========================================
# ENDPOINTS: USUARIOS Y PROYECTOS
# ==========================================
@app.route('/api/usuarios', methods=['GET'])
def get_users():
    rol = request.args.get('rol')
    query = Usuario.query
    if rol:
        query = query.filter_by(rol=rol)
    return jsonify([u.to_dict() for u in query.all()]), 200

@app.route('/api/usuarios', methods=['POST'])
def create_user():
    data = request.get_json()
    try:
        user = Usuario(user_id=data['user_id'], name=data['name'], rol=data['rol'])
        db.session.add(user)
        db.session.commit()
        return jsonify({'message': 'User created', 'user': user.to_dict()}), 201
    except (IntegrityError, OperationalError) as e:
        db.session.rollback()
        return jsonify({'error': extract_db_error(e)}), 400

@app.route('/api/proyectos', methods=['GET'])
def get_projects():
    return jsonify([p.to_dict() for p in Proyecto.query.all()]), 200

@app.route('/api/proyectos', methods=['POST'])
def create_project():
    data = request.get_json()
    try:
        proj = Proyecto(
            project_id=data['project_id'],
            project_name=data['project_name'],
            state=data.get('state', 'in_development'),
            user_id=data['user_id']
        )
        db.session.add(proj)
        db.session.commit()
        return jsonify({'message': 'Project created', 'project': proj.to_dict()}), 201
    except (IntegrityError, OperationalError) as e:
        db.session.rollback()
        return jsonify({'error': extract_db_error(e)}), 400

# ==========================================
# ENDPOINTS: SOLICITUDES, APROBACIÓN Y DEVOLUCIONES
# ==========================================
@app.route('/api/solicitudes', methods=['GET'])
def get_solicitudes():
    state = request.args.get('state')
    query = RegistroSolicitud.query
    if state:
        query = query.filter_by(state=state)
    solicitudes = query.order_by(RegistroSolicitud.emission_date.desc()).all()
    return jsonify([s.to_dict() for s in solicitudes]), 200

@app.route('/api/solicitudes', methods=['POST'])
def create_solicitud():
    """
    Crea una solicitud en estado 'pending' con sus ítems.
    Espera JSON:
    {
      "solicitud_id": "S01",
      "project_id": "P01",
      "due_date": "2026-12-01",
      "items": [{"element_id": "E01", "quantity": 2}]
    }
    """
    data = request.get_json()
    try:
        emission = datetime.strptime(data['emission_date'], '%Y-%m-%d').date() if data.get('emission_date') else date.today()
        due = datetime.strptime(data['due_date'], '%Y-%m-%d').date()

        solicitud = RegistroSolicitud(
            solicitud_id=data['solicitud_id'],
            project_id=data['project_id'],
            emission_date=emission,
            due_date=due,
            state='pending',
            is_fully_returned=False
        )
        db.session.add(solicitud)
        db.session.flush()  # Inserta la cabecera antes de los detalles

        for item in data.get('items', []):
            detalle = DetallePrestamo(
                solicitud_id=solicitud.solicitud_id,
                element_id=item['element_id'],
                quantity=int(item['quantity']),
                returned_quantity=0
            )
            db.session.add(detalle)

        db.session.commit()
        return jsonify({'message': 'Loan request created (pending approval)', 'solicitud': solicitud.to_dict()}), 201
    except (IntegrityError, OperationalError, ValueError, KeyError) as e:
        db.session.rollback()
        return jsonify({'error': extract_db_error(e)}), 400

@app.route('/api/solicitudes/<solicitud_id>/aprobar', methods=['PUT'])
def approve_solicitud(solicitud_id):
    """Cambia estado de pending -> approved. MySQL valida rol admin y descuenta stock."""
    sol = db.session.get(RegistroSolicitud, solicitud_id)
    if not sol:
        return jsonify({'error': 'Request not found'}), 404

    data = request.get_json()
    sol.approved_by = data.get('approved_by')
    sol.state = 'approved'

    try:
        db.session.commit()
        return jsonify({'message': 'Loan request approved and stock deducted', 'solicitud': sol.to_dict()}), 200
    except (IntegrityError, OperationalError) as e:
        db.session.rollback()
        return jsonify({'error': extract_db_error(e)}), 400

@app.route('/api/solicitudes/<solicitud_id>/rechazar', methods=['PUT'])
def reject_solicitud(solicitud_id):
    sol = db.session.get(RegistroSolicitud, solicitud_id)
    if not sol:
        return jsonify({'error': 'Request not found'}), 404

    data = request.get_json() or {}
    sol.approved_by = data.get('approved_by')
    sol.state = 'rejected'

    try:
        db.session.commit()
        return jsonify({'message': 'Loan request rejected', 'solicitud': sol.to_dict()}), 200
    except (IntegrityError, OperationalError) as e:
        db.session.rollback()
        return jsonify({'error': extract_db_error(e)}), 400

@app.route('/api/solicitudes/<solicitud_id>/devolver', methods=['PUT'])
def return_component(solicitud_id):
    """
    Registra devolución parcial o total de un ítem.
    MySQL suma el stock de vuelta y cierra la solicitud si ya devolvió todo.
    Espera JSON: {"element_id": "E01", "returned_quantity": 2}
    """
    data = request.get_json()
    element_id = data.get('element_id')
    detalle = db.session.get(DetallePrestamo, (solicitud_id, element_id))
    if not detalle:
        return jsonify({'error': 'Loan detail not found'}), 404

    detalle.returned_quantity = int(data['returned_quantity'])

    try:
        db.session.commit()
        sol = db.session.get(RegistroSolicitud, solicitud_id)
        db.session.refresh(sol)  # Recarga el estado actualizado por el trigger
        return jsonify({'message': 'Return registered successfully', 'solicitud': sol.to_dict()}), 200
    except (IntegrityError, OperationalError) as e:
        db.session.rollback()
        return jsonify({'error': extract_db_error(e)}), 400

# ==========================================
# INICIO DEL SERVIDOR
# ==========================================
if __name__ == '__main__':
    app.run(debug=True, port=5000)