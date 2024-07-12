from flask import Flask, request, jsonify
from flask_pymongo import PyMongo
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config["MONGO_URI"] = "mongodb+srv://flask-access:qwertyuiop@gms.6lp3mja.mongodb.net/client?retryWrites=true&w=majority"
app.secret_key = 'mysecretkey'

mongo = PyMongo(app)

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    if not data:
        return jsonify({'message': 'No input data provided'}), 400
    
    name = data.get('name')
    user_id = data.get('id')
    password = data.get('password')
    
    if not name or not user_id or not password:
        return jsonify({'message': 'Name, ID, and password are required'}), 400
    
    existing_user = mongo.db.users.find_one({'id': user_id})
    
    if existing_user:
        return jsonify({'message': 'User already exists'}), 409
    
    hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
    mongo.db.users.insert_one({
        'name': name,
        'id': user_id,
        'hashword': hashed_password,
        'confirmed': False,
        'confkey': ''  # You can generate a confirmation key if needed
    })
    
    return jsonify({'message': 'User registered successfully'}), 201

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    user_id = data.get('id')
    password = data.get('password')
    
    if not user_id or not password:
        return jsonify({'message': 'ID and password are required'}), 400
    
    user = mongo.db.users.find_one({'id': user_id})
    
    if not user or not check_password_hash(user['hashword'], password):
        return jsonify({'message': 'Invalid ID or password'}), 401
    
    return jsonify({'message': 'Login successful'}), 200

@app.route('/update', methods=['PUT'])
def update_user():
    data = request.get_json()
    user_id = data.get('id')
    new_data = data.get('new_data')
    
    if not user_id or not new_data:
        return jsonify({'message': 'ID and new data are required'}), 400
    
    user = mongo.db.users.find_one({'id': user_id})
    
    if not user:
        return jsonify({'message': 'User not found'}), 404
    
    mongo.db.users.update_one({'id': user_id}, {'$set': new_data})
    
    return jsonify({'message': 'User updated successfully'}), 200

@app.route('/delete', methods=['DELETE'])
def delete_user():
    data = request.get_json()
    user_id = data.get('id')
    
    if not user_id:
        return jsonify({'message': 'ID required'}), 400
    
    user = mongo.db.users.find_one({'id': user_id})
    
    if not user:
        return jsonify({'message': 'User not found'}), 404
    
    mongo.db.users.delete_one({'id': user_id})
    
    return jsonify({'message': 'User deleted successfully'}), 200

@app.route('/reset_password', methods=['POST'])
def reset_password():
    data = request.get_json()
    user_id = data.get('id')
    new_password = data.get('new_password')
    
    if not user_id or not new_password:
        return jsonify({'message': 'ID and new password are required'}), 400
    
    user = mongo.db.users.find_one({'id': user_id})
    
    if not user:
        return jsonify({'message': 'User not found'}), 404
    
    hashed_password = generate_password_hash(new_password, method='pbkdf2:sha256')
    mongo.db.users.update_one({'id': user_id}, {'$set': {'hashword': hashed_password}})
    
    return jsonify({'message': 'Password reset successfully'}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)

