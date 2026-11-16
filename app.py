import os
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError

app = Flask(__name__)

# Forzar a que busque laboratory.db en la misma carpeta exacta donde está app.py
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'laboratory.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ==========================================
# MODELO (Mapeo de la tabla existente)
# ==========================================
class Inventario(db.Model):
    __tablename__ = 'inventario'
    element_id = db.Column(db.String(10), primary_key=True)
    component_name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)

    def to_dict(self):
        return {
            'element_id': self.element_id,
            'component_name': self.component_name,
            'category': self.category,
            'quantity': self.quantity
        }

# ==========================================
# RUTAS CRUD - ENDPOINTS DE LA API
# ==========================================

# 1. READ ALL (GET) - Listar todo el inventario
@app.route('/api/inventario', methods=['GET'])
def get_inventory():
    items = Inventario.query.all()
    return jsonify([item.to_dict() for item in items]), 200

# 2. READ ONE (GET) - Buscar un componente por ID
@app.route('/api/inventario/<element_id>', methods=['GET'])
def get_item(element_id):
    item = Inventario.query.get(element_id)
    if not item:
        return jsonify({'error': 'Component not found'}), 404
    return jsonify(item.to_dict()), 200

# 3. CREATE (POST) - Registrar un nuevo componente
@app.route('/api/inventario', methods=['POST'])
def add_item():
    data = request.get_json()
    
    nuevo_item = Inventario(
        element_id=data['element_id'],
        component_name=data['component_name'],
        category=data['category'],
        quantity=data['quantity']
    )
    
    try:
        db.session.add(nuevo_item)
        db.session.commit()
        return jsonify({'message': 'Component created successfully', 'item': nuevo_item.to_dict()}), 201
    except IntegrityError as e:
        db.session.rollback()
        # Esto atrapa tanto si el ID ya existe como si el quantity es negativo (tu CHECK constraint)
        return jsonify({'error': 'Integrity Error (e.g., Duplicate ID or negative quantity)'}), 400

# 4. UPDATE (PUT) - Actualizar stock u otro campo
@app.route('/api/inventario/<element_id>', methods=['PUT'])
def update_item(element_id):
    item = Inventario.query.get(element_id)
    if not item:
        return jsonify({'error': 'Component not found'}), 404

    data = request.get_json()
    
    if 'component_name' in data:
        item.component_name = data['component_name']
    if 'category' in data:
        item.category = data['category']
    if 'quantity' in data:
        item.quantity = data['quantity']
        
    try:
        db.session.commit()
        return jsonify({'message': 'Component updated successfully', 'item': item.to_dict()}), 200
    except IntegrityError:
        db.session.rollback()
        return jsonify({'error': 'Update failed due to constraint violation (e.g., negative stock)'}), 400

# 5. DELETE (DELETE) - Eliminar un componente
@app.route('/api/inventario/<element_id>', methods=['DELETE'])
def delete_item(element_id):
    item = Inventario.query.get(element_id)
    if not item:
        return jsonify({'error': 'Component not found'}), 404
        
    db.session.delete(item)
    db.session.commit()
    return jsonify({'message': 'Component deleted successfully'}), 200

# ==========================================
# INICIO DEL SERVIDOR
# ==========================================
if __name__ == '__main__':
    app.run(debug=True, port=5000)
