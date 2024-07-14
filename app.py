from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import ssl, smtplib, hashlib, uuid
from flask import Flask, request, jsonify, render_template
from flask_pymongo import PyMongo
from werkzeug.security import generate_password_hash, check_password_hash



app = Flask(__name__)
app.config["MONGO_URI"] = "mongodb+srv://flask-access:qwertyuiop@gms.6lp3mja.mongodb.net/client?retryWrites=true&w=majority"
app.secret_key = 'mysecretkey'

mongo = PyMongo(app)
BASE_URL = "http://127.0.0.1:5001"

def sendmail(mail_met, receiver, subject, short_subject, text, html="NOT INPUT BY USER."):
    mailid = 'ct.gms@psgtech.ac.in'
    mailps = 'sigmaM4IN7'
    if html == "NOT INPUT BY USER.":
        html = render_template("email.html",
                               mail=receiver,
                               message=text,
                               subject=short_subject,
                               mail_met=mail_met)
    
    sender_email = mailid
    receiver_email = receiver
    password = mailps
    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = sender_email
    message["To"] = receiver_email
    part1 = MIMEText(text, 'plain')
    part2 = MIMEText(html, 'html')
    message.attach(part1)
    message.attach(part2)
    
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=context) as server:
        server.login(sender_email, password)
        server.sendmail(sender_email, receiver_email, message.as_string())

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
    confirm_key = str(uuid.uuid4()).split("-")[0].upper()

    confirmation_link = f"{BASE_URL}/confirm/{confirm_key}"
    sendmail(
        mail_met={"type": "welcome"},
        receiver=f"{user_id}@psgtech.ac.in",
        subject="[PSG-GMS-SIGMA] Welcome!",
        short_subject="Welcome!",
        text=f'''Dear {name},
        <br/>Welcome to "SIGMA" General Maintenance Software by PSG College of Technology! Please click the link below to confirm your e-mail and start using the software.
        <br/><br/>
        <a style="text-decoration:none;background-color: #2A4BAA;font-size: 20px;border: none;color: white;border-radius: 10px;padding-top: 10px;padding-bottom: 10px;padding-left: 30px;padding-right: 30px;" href="{confirmation_link}">Confirm E-Mail</a>
        <br/><br/>
        If the button does not work, please visit {confirmation_link} and confirm.
        <br/>Thank You.'''
    )

    mongo.db.users.insert_one({
        'name': name,
        'id': user_id,
        'hashword': hashed_password,
        'confirmed': False,
        'confkey': confirm_key
    })
    
    return jsonify({'message': 'Please check your e-mail to confirm your registration.'}), 201

@app.route('/confirm/<confkey>', methods=['GET'])
def confirm_email(confkey):
    user = mongo.db.users.find_one({'confkey': confkey})
    
    if not user:
        return jsonify({'message': 'Invalid confirmation key'}), 400
    
    mongo.db.users.update_one({'confkey': confkey}, {'$set': {'confirmed': True, 'confkey': ''}})
    
    return jsonify({'message': 'Email confirmed successfully. You can now log in.'}), 200

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
    
    if not user['confirmed']:
        return jsonify({'message': 'Email not confirmed. Please check your email.'}), 403
    
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
    old_password = data.get('old_password')
    new_password = data.get('new_password')
    
    if not user_id or not old_password or not new_password:
        return jsonify({'message': 'ID, old password, and new password are required'}), 400
    
    user = mongo.db.users.find_one({'id': user_id})
    
    if not user:
        return jsonify({'message': 'User not found'}), 404
    
    if not check_password_hash(user['hashword'], old_password):
        return jsonify({'message': 'Old password is incorrect'}), 401
    
    hashed_password = generate_password_hash(new_password, method='pbkdf2:sha256')
    mongo.db.users.update_one({'id': user_id}, {'$set': {'hashword': hashed_password}})
    
    return jsonify({'message': 'Password reset successfully'}), 200

@app.route('/forgot_password', methods=['POST'])
def forgot_password():
    data = request.get_json()
    user_id = data.get('id')
    
    if not user_id:
        return jsonify({'message': 'ID required'}), 400
    
    user = mongo.db.users.find_one({'id': user_id})
    
    if not user:
        return jsonify({'message': 'User not found'}), 404
    
    reset_key = str(uuid.uuid4()).split("-")[0].upper()
    reset_link = f"{BASE_URL}/reset/{reset_key}"
    sendmail(
        mail_met={"type": "reset_password"},
        receiver=f"{user_id}@psgtech.ac.in",
        subject="[PSG-GMS-SIGMA] Reset Your Password",
        short_subject="Reset Your Password",
        text=f'''Dear {user['name']},
        <br/>We received a request to reset your password. Please click the link below to reset your password.
        <br/><br/>
        <a style="text-decoration:none;background-color: #2A4BAA;font-size: 20px;border: none;color: white;border-radius: 10px;padding-top: 10px;padding-bottom: 10px;padding-left: 30px;padding-right: 30px;" href="{reset_link}">Reset Password</a>
        <br/><br/>
        If the button does not work, please visit {reset_link} and reset your password.
        <br/>Thank You.'''
    )
    
    mongo.db.users.update_one({'id': user_id}, {'$set': {'reset_key': reset_key}})
    
    return jsonify({'message': 'Please check your e-mail to reset your password.'}), 200

@app.route('/reset/<reset_key>', methods=['GET'])
def reset_password_page(reset_key):
    user = mongo.db.users.find_one({'reset_key': reset_key})
    
    if not user:
        return jsonify({'message': 'Invalid or expired reset key'}), 400
    
    return render_template('reset_password.html', reset_key=reset_key)

@app.route('/update_password', methods=['POST'])
def update_password():
    reset_key = request.form.get('reset_key')
    new_password = request.form.get('new_password')
    
    if not reset_key or not new_password:
        return jsonify({'message': 'Reset key and new password are required'}), 400
    
    user = mongo.db.users.find_one({'reset_key': reset_key})
    
    if not user:
        return jsonify({'message': 'Invalid or expired reset key'}), 400
    
    hashed_password = generate_password_hash(new_password, method='pbkdf2:sha256')
    mongo.db.users.update_one({'reset_key': reset_key}, {'$set': {'hashword': hashed_password, 'reset_key': ''}})
    
    return jsonify({'message': 'Password updated successfully'}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)


