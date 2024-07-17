from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import ssl, smtplib, hashlib, uuid
from flask import Flask, request, jsonify, render_template
from flask_pymongo import PyMongo
from datetime import datetime
import json



app = Flask(__name__)
app.config["MONGO_URI"] = "mongodb+srv://flask-access:qwertyuiop@gms.6lp3mja.mongodb.net/client?retryWrites=true&w=majority"
app.secret_key = 'mysecretkey'

mongo = PyMongo(app)
BASE_URL = "http://127.0.0.1:5001"


def get_hash(clear:str):
    return hashlib.sha224(clear.encode("utf-8")).hexdigest()

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

@app.route('/')
def home():
    project_info = {
            "project_name": "SIGMA | General Maintenance Software | API",
        }
    return project_info

@app.route('/client/register', methods=['POST'])
def client_register():
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
    
    hashed_password = get_hash(password)
    confirm_key = str(uuid.uuid4()).split("-")[0].upper()

    confirmation_link = f"{BASE_URL}/client/confirm/{confirm_key}"
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

@app.route('/client/confirm/<confkey>', methods=['GET'])
def client_confirm_email(confkey):
    user = mongo.db.users.find_one({'confkey': confkey})
    
    if not user:
        return jsonify({'message': 'Invalid confirmation key'}), 400
    
    mongo.db.users.update_one({'confkey': confkey}, {'$set': {'confirmed': True, 'confkey': ''}})
    
    return jsonify({'message': 'Email confirmed successfully. You can now log in.'}), 200

@app.route('/client/login', methods=['POST'])
def client_login():
    data = request.get_json()
    user_id = data.get('id')
    password = data.get('password')
    
    if not user_id or not password:
        return jsonify({'message': 'ID and password are required'}), 400
    
    user = mongo.db.users.find_one({'id': user_id})
    
    if not user or get_hash(password) != user['hashword']:
        return jsonify({'message': 'Invalid ID or password'}), 401
    
    if not user['confirmed']:
        return jsonify({'message': 'Email not confirmed. Please check your email.'}), 403
    
    return jsonify({'message': 'Login successful'}), 200

@app.route('/client/update', methods=['PUT'])
def client_update_user():
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

@app.route('/client/delete', methods=['DELETE'])
def client_delete_user():
    data = request.get_json()
    user_id = data.get('id')
    
    if not user_id:
        return jsonify({'message': 'ID required'}), 400
    
    user = mongo.db.users.find_one({'id': user_id})
    
    if not user:
        return jsonify({'message': 'User not found'}), 404
    
    mongo.db.users.delete_one({'id': user_id})
    
    return jsonify({'message': 'User deleted successfully'}), 200

@app.route('/client/reset_password', methods=['POST'])
def client_reset_password():
    data = request.get_json()
    user_id = data.get('id')
    old_password = data.get('old_password')
    new_password = data.get('new_password')
    
    if not user_id or not old_password or not new_password:
        return jsonify({'message': 'ID, old password, and new password are required'}), 400
    
    user = mongo.db.users.find_one({'id': user_id})
    
    if not user:
        return jsonify({'message': 'User not found'}), 404
    
    if get_hash(old_password) != user['hashword']:
        return jsonify({'message': 'Old password is incorrect'}), 401
    
    hashed_password = get_hash(new_password)
    mongo.db.users.update_one({'id': user_id}, {'$set': {'hashword': hashed_password}})
    
    return jsonify({'message': 'Password reset successfully'}), 200

@app.route('/client/forgot_password', methods=['POST'])
def client_forgot_password():
    data = request.get_json()
    user_id = data.get('id')
    
    if not user_id:
        return jsonify({'message': 'ID required'}), 400
    
    user = mongo.db.users.find_one({'id': user_id})
    
    if not user:
        return jsonify({'message': 'User not found'}), 404
    
    reset_key = str(uuid.uuid4()).split("-")[0].upper()
    reset_link = f"{BASE_URL}/client/reset/{reset_key}"
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

@app.route('/client/reset/<reset_key>', methods=['GET'])
def client_reset_password_page(reset_key):
    user = mongo.db.users.find_one({'reset_key': reset_key})
    
    if not user:
        return jsonify({'message': 'Invalid or expired reset key'}), 400
    
    return render_template('reset_password.html', reset_key=reset_key)

@app.route('/client/update_password', methods=['POST'])
def client_update_password():
    reset_key = request.form.get('reset_key')
    new_password = request.form.get('new_password')
    
    if not reset_key or not new_password:
        return jsonify({'message': 'Reset key and new password are required'}), 400
    
    user = mongo.db.users.find_one({'reset_key': reset_key})
    
    if not user:
        return jsonify({'message': 'Invalid or expired reset key'}), 400
    
    hashed_password = get_hash(new_password)
    mongo.db.users.update_one({'reset_key': reset_key}, {'$set': {'hashword': hashed_password, 'reset_key': ''}})
    
    return jsonify({'message': 'Password updated successfully'}), 200







#########################################################################################################################################



def workEfficiency():
    '''
    workEffeciency is a function which takes no parameters, analyzes the database and
    returns the workEffeciency as a float in percentage when called.
    '''
    
    totSuggestion=0
    totComplaint=0
    closedComplaint=0
    closedSuggestion=0
    entries = mongo.db.dataset.find()
    for issueEntry in entries:
        if (datetime.strptime(issueEntry["issue"]["issueLastUpdateDate"],"%d/%m/%y")-datetime.now()).days<=30:
            if issueEntry["issue"]["issueType"].lower()=="suggestion":
                totSuggestion+=1
                if issueEntry["status"].upper()=="CLOSE":
                    closedSuggestion+=1

            else:
                totComplaint+=1
                if issueEntry["status"].upper()=="CLOSE":
                    closedComplaint+=1
    workEff=0.6*((closedComplaint/totComplaint)*100)+0.4*((closedSuggestion/totSuggestion)*100)

    monthly = [0,0,0,0,0,0,0,0,0,0,0,0]
    monthly_resolved = [0,0,0,0,0,0,0,0,0,0,0,0]
    for issueEntry in entries:
        date = int(datetime.strptime(issueEntry["issue"]["issueLastUpdateDate"],"%d/%m/%y").strftime("%m"))
        monthly[date-1] += 1
    for issueEntry in entries:
        date = int(datetime.strptime(issueEntry["issue"]["issueLastUpdateDate"],"%d/%m/%y").strftime("%m"))
        if issueEntry["status"].upper()=="CLOSE":
            monthly_resolved[date-1] += 1
    return {"COMP":closedComplaint,"SUGG":(totComplaint-closedComplaint),"EFFE":round(workEff,2),"TOTA":totComplaint,"GRAP":monthly,"GRAP_RES":monthly_resolved}



def newUser(details:dict):

    mongo.db.personnel.insert_one({
                    "name" : details["name"],
                    "id" : details["id"],
                    "hashword" : details["hashword"],
                    "confirmed" : True,
                    "approved" : True,
                    "mod": 0
                 })
    

def priority(task:dict):
    '''
    priority is a function which takes the task as a dictionary, analyzes the task and returns
    a priority integer when called.
    '''

    if task["issue"]["issueType"] == "ISSUE":
        priority = 1
    elif task["issue"]["issueType"] == "SUGGESTION":
        priority = 2
    else:
        priority = 1
    return priority



def closeIssue(issueId:str,personId:str):
    '''
    closeIssue is a function which takes in 2 parameters, issueId and personId,
    and utilizes these parameters to search for an issue by issueId, mark the
    issue as close, and add "closed by personId" to the logs.
    '''

    rightNow=datetime.now()

    issueEntry = mongo.db.dataset.find_one({"issueNo":issueId})

    log = issueEntry.get("log")
    log.append({  
    "date":rightNow.strftime("%d-%m-%y %H:%M"),
    "action":"closed",
    "by": personId
    })
    issue = issueEntry.get("issue")
    issue["issueLastUpdateDate"]=rightNow.strftime("%d/%m/%y")
    issue["issueLastUpdateTime"]=rightNow.strftime("%I:%M %p")
    mongo.db.dataset.update_one({"_id":issueEntry.get("_id")}, {"$set" :
                                        {"log":log,
                                         "status":"CLOSE",
                                         "issue":issue}})
    

def openIssue(issueId:str,personId:str):
    '''
    openIssue is a function which takes in 2 parameters, issueId and personId,
    and utilizes these parameters to search for an issue by issueId, mark the
    issue as open, and add "opened by personId" to the logs.
    '''
    
    rightNow=datetime.now()

    issueEntry = mongo.db.dataset.find_one({"issueNo":issueId})

    log = issueEntry.get("log")
    log.append({  
    "date":rightNow.strftime("%d-%m-%y %H:%M"),
    "action":"opened",
    "by": personId
    })
    issue = issueEntry.get("issue")
    issue["issueLastUpdateDate"]=rightNow.strftime("%d/%m/%y")
    issue["issueLastUpdateTime"]=rightNow.strftime("%I:%M %p")
    mongo.db.dataset.update_one({"_id":issueEntry.get("_id")}, {"$set" :
                                        {"log":log,
                                         "status":"OPEN",
                                         "issue":issue}})
    

def addComment(issueId:str,comment:dict):
    '''
    addComment is a function which takes in 2 parameters, issueId and comment,
    and utilizes these parameters to search for an issue by issueId, mark the
    issue as close, and add "closed by personId" to the logs.
    '''
    rightNow=datetime.now()

    issueEntry = mongo.db.dataset.find_one({"issueNo":issueId})

    comments = issueEntry.get("comments")
    comments.append({ 
            "date":rightNow.strftime("%d-%m-%y %H:%M"),
            "content":comment["content"],
            "by":comment["by"]
            })
    issue = issueEntry.get("issue")
    issue["issueLastUpdateDate"]=rightNow.strftime("%d/%m/%y")
    issue["issueLastUpdateTime"]=rightNow.strftime("%I:%M %p")
    mongo.db.dataset.update_one({"_id":issueEntry.get("_id")}, {"$set" :
                                        {"comments":comments,
                                         "issue":issue}})



@app.route('/manager/register',methods=['POST'])
def manager_register():
    data = request.get_json()
    if not data:
        return jsonify({'message': 'No input data provided'}), 400
    
    name = data.get('name')
    user_id = data.get('id')
    password = data.get('password')
    
    if not name or not user_id or not password:
        return jsonify({'message': 'Name, ID, and password are required'}), 400
    
    existing_user = mongo.db.personnel.find_one({'id': user_id})
    
    if existing_user:
        return jsonify({'message': 'User already exists'}), 409
    
    hashed_password = get_hash(password)
    confirm_key = str(uuid.uuid4()).split("-")[0].upper()

    confirmation_link = f"{BASE_URL}/manager/confirm/{confirm_key}"
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

    mongo.db.personnel.insert_one({
        'name': name,
        'id': user_id,
        'hashword': hashed_password,
        'confirmed': False,
        'approved': False,
        'mod': 0,
        'confkey': confirm_key
    })
    
    return jsonify({'message': 'Please check your e-mail to confirm your registration.'}), 201



# self email confirmation
@app.route('/manager/confirm/<confkey>', methods=['GET'])
def manager_confirm_email(confkey):
    users = list(mongo.db.personnel.find())
    user_to_confirm = None

    for user in users:
        if user.get("confkey") == confkey:
            user_to_confirm = user
            break
    
    if not user_to_confirm:
        return jsonify({'message': 'Invalid confirmation key'}), 400

    mod_key = str(uuid.uuid4()).split("-")[0].upper()
    mongo.db.personnel.update_one({"_id": user_to_confirm.get("_id")}, {
        "$set": {
            "confirmed": True,
            "approved": False,
            "mod": 0,
            "modkey": mod_key
        }
    })

    id = user_to_confirm["id"]
    name = user_to_confirm["name"]
    sendmail(
        {"type": "welcome"},
        f"{id}@psgtech.ac.in",
        "[PSG-GMS-SIGMA] E-Mail Confirmed. Welcome!",
        "Your E-Mail has been Confirmed!",
        f'''Dear {name},
        <br/>Welcome to "SIGMA" General Maintenance Software by PSG College of Technology! Your E-Mail has been Confirmed. Please await approval from a moderator, so you can start using the application!
        <br/>Thank You.'''
    )

    for user in users:
        if user["mod"] == 1:
            sendmail(
                {"type": "welcome"},
                f"{user['id']}@psgtech.ac.in",
                "[PSG-GMS-SIGMA] Approve New Registration",
                "Please Approve New Registration to the System",
                f'''Dear {user["name"]},
                <br/>{name} [{id}@psgtech.ac.in] has registered as a maintenance staff under the "SIGMA" General Maintenance Software by PSG College of Technology. Please, as a moderator, approve the user, so {name} can start using the application!
                <br/><br/>
                <a style="text-decoration:none;background-color: #2A4BAA;font-size: 20px;border: none;color: white;border-radius: 10px;padding-top: 10px;padding-bottom: 10px;padding-left: 30px;padding-right: 30px;" href="{BASE_URL}/manager/approve/{mod_key}">Approve User</a>
                <br/><br/>
                If the button does not work, please visit {BASE_URL}/manager/approve/{mod_key} and confirm.
                <br/><br/>
                If you do <b>NOT</b> know who this is, please <b>do NOT</b> confirm.
                <br/>Thank You.'''
            )

    return jsonify({
        'message': 'Welcome to "SIGMA" General Maintenance Software by PSG College of Technology! Your E-Mail has been Confirmed. Please await approval from a moderator, so you can start using the application!'
    }), 200

# account approval from a moderator
@app.route('/manager/approve/<confkey>', methods=['GET'])
def manager_approve_email(confkey):
    users = list(mongo.db.personnel.find())
    user_to_approve = None

    for user in users:
        if user.get("modkey") == confkey:
            user_to_approve = user
            break
    
    if not user_to_approve:
        return jsonify({'message': 'Invalid confirmation key'}), 400

    mod_key = str(uuid.uuid4()).split("-")[0].upper()
    mongo.db.personnel.update_one({"_id": user_to_approve.get("_id")}, {
        "$set": {
            "confirmed": True,
            "approved": True,
            "mod": 0,
            "modkey": mod_key
        }
    })

    id = user_to_approve["id"]
    name = user_to_approve["name"]

    for user in users:
        if user["mod"] == 1:
            sendmail(
                {"type": "welcome"},
                f"{user['id']}@psgtech.ac.in",
                "[PSG-GMS-SIGMA] Approve New Registration",
                "Please Approve New Registration to the System",
                f'''Dear {user["name"]},
                <br/>{name} [{id}@psgtech.ac.in] has been approved as a maintenance staff under the "SIGMA" General Maintenance Software by PSG College of Technology. If you wish for {name} to be a moderator, please escalate user privileges by clicking this button:
                <br/><br/>
                <a style="text-decoration:none;background-color: #2A4BAA;font-size: 20px;border: none;color: white;border-radius: 10px;padding-top: 10px;padding-bottom: 10px;padding-left: 30px;padding-right: 30px;" href="{BASE_URL}/manager/escalate/{mod_key}">Escalate User</a>
                <br/><br/>
                If the button does not work, please visit {BASE_URL}/manager/escalate/{mod_key}.
                <br/><br/>
                If you do <b>NOT</b> know who this is, please <b>do NOT</b> confirm.
                <br/>Thank You.'''
            )

    sendmail(
        {"type": "welcome"},
        f"{id}@psgtech.ac.in",
        "[PSG-GMS-SIGMA] Log-In Account Approved. Welcome!",
        "Your Log-In Account has been Approved!",
        f'''Dear {name},
        <br/>Welcome to "SIGMA" General Maintenance Software by PSG College of Technology! Your Log-In Account has been Approved. Please download and open the application and Log-In as usual so you can start using the application!
        <br/>Thank You.'''
    )

    return jsonify({
        'message': f'''You have approved this user. If you wish to escalate this person's privileges and approve as a moderator, click the following button after approval from the previous step:
        <br/><br/>
        <a style="text-decoration:none;background-color: #2A4BAA;font-size: 20px;border: none;color: white;border-radius: 10px;padding-top: 10px;padding-bottom: 10px;padding-left: 30px;padding-right: 30px;" href="{BASE_URL}/manager/escalate/{mod_key}">Approve User</a>
        <br/><br/>
        If the button does not work, please visit {BASE_URL}/manager/escalate/{mod_key} and confirm.
        <br/><br/>'''
    }), 200

@app.route('/manager/escalate/<confkey>', methods=['GET'])
def manager_escalate_email(confkey):
    users = list(mongo.db.personnel.find())
    user_to_escalate = None

    for user in users:
        if user.get("modkey") == confkey:
            user_to_escalate = user
            break
    
    if not user_to_escalate:
        return jsonify({'message': 'Invalid confirmation key'}), 400

    mongo.db.personnel.update_one({"_id": user_to_escalate.get("_id")}, {
        "$set": {
            "confirmed": True,
            "approved": True,
            "mod": 1
        }
    })

    id = user_to_escalate["id"]
    name = user_to_escalate["name"]

    sendmail(
        {"type": "welcome"},
        f"{id}@psgtech.ac.in",
        "[PSG-GMS-SIGMA] Privileges Escalated to Moderator Status!",
        "Congrats! You have been Assigned to Moderator Status with Account Approval Privileges!",
        f'''Dear {name},
        <br/>Welcome to "SIGMA" General Maintenance Software by PSG College of Technology! You have been Assigned to Moderator Status with Account Approval Privileges! You will now be notified via e-mail whenever someone creates a new account, and be responsible for approval of new accounts!
        <br/>Thank You.'''
    )

    return jsonify({
        'message': "You have escalated this user's privileges to moderator status."
    }), 200


@app.route('/manager/reset_password', methods=['POST'])
def manager_reset_password():
    data = request.get_json()
    user_id = data.get('id')
    old_password = data.get('old_password')
    new_password = data.get('new_password')
    
    if not user_id or not old_password or not new_password:
        return jsonify({'message': 'ID, old password, and new password are required'}), 400
    
    user = mongo.db.personnel.find_one({'id': user_id})
    
    if not user:
        return jsonify({'message': 'User not found'}), 404
    
    if get_hash(old_password) != user['hashword']:
        return jsonify({'message': 'Old password is incorrect'}), 401
    
    hashed_password = get_hash(new_password)
    mongo.db.personnel.update_one({'id': user_id}, {'$set': {'hashword': hashed_password}})
    
    return jsonify({'message': 'Password reset successfully'}), 200

@app.route('/manager/forgot_password', methods=['POST'])
def manager_forgot_password():
    data = request.get_json()
    user_id = data.get('id')
    
    if not user_id:
        return jsonify({'message': 'ID required'}), 400
    
    user = mongo.db.personnel.find_one({'id': user_id})
    
    if not user:
        return jsonify({'message': 'User not found'}), 404
    
    reset_key = str(uuid.uuid4()).split("-")[0].upper()
    reset_link = f"{BASE_URL}/manager/reset/{reset_key}"
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
    
    mongo.db.personnel.update_one({'id': user_id}, {'$set': {'reset_key': reset_key}})
    
    return jsonify({'message': 'Please check your e-mail to reset your password.'}), 200

@app.route('/manager/reset/<reset_key>', methods=['GET'])
def manager_reset_password_page(reset_key):
    user = mongo.db.personnel.find_one({'reset_key': reset_key})
    
    if not user:
        return jsonify({'message': 'Invalid or expired reset key'}), 400
    
    return render_template('mgr_reset_password.html', reset_key=reset_key)

@app.route('/manager/update_password', methods=['POST'])
def manager_update_password():
    reset_key = request.form.get('reset_key')
    new_password = request.form.get('new_password')
    
    if not reset_key or not new_password:
        return jsonify({'message': 'Reset key and new password are required'}), 400
    
    user = mongo.db.personnel.find_one({'reset_key': reset_key})
    
    if not user:
        return jsonify({'message': 'Invalid or expired reset key'}), 400
    
    hashed_password = get_hash(new_password)
    mongo.db.personnel.update_one({'reset_key': reset_key}, {'$set': {'hashword': hashed_password, 'reset_key': ''}})
    
    return jsonify({'message': 'Password updated successfully'}), 200


@app.route('/manager/login', methods=['POST'])
def manager_login():
    data = request.get_json()
    user_id = data.get('id')
    password = data.get('password')
    
    if not user_id or not password:
        return jsonify({'message': 'ID and password are required'}), 400
    
    user = mongo.db.personnel.find_one({'id': user_id})
    
    if not user or get_hash(password) != user['hashword']:
        return jsonify({'message': 'Invalid ID or password'}), 401
    
    if not user['confirmed']:
        return jsonify({'message': 'Email not confirmed. Please check your email.'}), 403
    
    # If login is successful, return the entire user data
    user['_id'] = str(user['_id'])  # Convert ObjectId to string for JSON serialization
    return jsonify({'message': 'Login successful', 'user': user}), 200


@app.route('/administrator/new-user', methods=['POST']) # adds new personnel member
def adm_new_user():
    data = request.get_json()

    if not data:
        return jsonify({'message': 'No JSON data received'}), 400

    new_user = {
        "name": data.get("name"),
        "id": data.get("id"),
        "hashword": "d63dc919e201d7bc4c825630d2cf25fdc93d4b2f0d46706d29038d01",  # default password is password
        "confirmed": True
    }

    newUser(new_user)
    return jsonify({'message': 'New user created successfully'}), 201


@app.route('/administrator/all-users')
def all_users_table():
    users = mongo.db.users.find()
    my_users = []
    userids = []
    
    for user in users:
        status = "CONFIRMED" if str(user["confirmed"]).lower() == "true" else "NOT CONFIRMED"
        my_users.append({
            "name": user.get("name"),
            "id": user.get("id"),
            "status": status
        })
        userids.append(user["id"])
    
    admin_users = []
    loaded_users = mongo.db.personnel.find()
    
    for admin_user in loaded_users:
        if admin_user["id"] not in userids:
            status = "CONFIRMED" if str(admin_user["confirmed"]).lower() == "true" else "NOT CONFIRMED"
            my_users.append({
                "name": admin_user.get("name"),
                "id": admin_user.get("id"),
                "status": status
            })
    
    return jsonify({"users": my_users, "title": "[PSG COLLEGE OF TECHNOLOGY | MAINTENANCE] ALL USERS"})


@app.route('/tasks/resolved')
def resolved_table():
    issues = mongo.db.dataset.find()
    my_issues = []

    for i in issues:
        if i["status"] == "CLOSE":
            if i["issue"]["issueType"] == "ISSUE":
                issueDate = datetime.strptime(i["issue"]["issueLastUpdateDate"], "%d/%m/%y")
                ddays = (datetime.now() - issueDate).days
                i.update({"delay_days": ddays})
                i.update({"priority": priority(i)})
                my_issues.append({
                    "delay_days": ddays,
                    "priority": priority(i),
                    "issue": i["issue"]
                })
        elif i["issue"]["issueType"] == "FEEDBACK":
            issueDate = datetime.strptime(i["issue"]["issueLastUpdateDate"], "%d/%m/%y")
            ddays = (datetime.now() - issueDate).days
            i.update({"delay_days": ddays})
            i.update({"priority": priority(i)})
            my_issues.append({
                "delay_days": ddays,
                "priority": priority(i),
                "issue": i["issue"]
            })
    
    return jsonify({"issues": my_issues, "title": "[PSG COLLEGE OF TECHNOLOGY | MAINTENANCE] RESOLVED ISSUES"})


@app.route('/task/status/<code>')
def issue_status_description(code):
    issue = mongo.db.dataset.find_one({"issueNo": code})
    
    if issue:
        # Convert ObjectId to string for JSON serialization
        issue["_id"] = str(issue["_id"])
        
        # Example logic to handle anonymity based on request context (replace with your actual logic)
        if issue.get("anonymity") == "true" and request.args.get("mod") == "1":
            issue["anonymity"] = "false"
        
        return jsonify({"issue": issue})
    
    return jsonify({"message": "Issue not found"}), 404


@app.route('/tasks/todo')
def task_list_table():
    issues = mongo.db.dataset.find()
    my_issues = []
    
    for i in issues:
        if i["status"] == "OPEN" and i["issue"]["issueType"] == "ISSUE":
            issueDate = datetime.strptime(i["issue"]["issueLastUpdateDate"], "%d/%m/%y")
            ddays = (datetime.now() - issueDate).days
            i.update({"delay_days": ddays})
            i.update({"priority": priority(i)})
            # Remove the "_id" field to avoid JSON serialization issues
            i.pop("_id", None)
            my_issues.append(i)
    
    return jsonify({"tasks": my_issues})


@app.route('/task/close/<code>', methods=['POST'])
def issue_close(code):
    data = request.get_json()
    user_id = data.get('user_id')  # Assuming the client sends the user ID in the request

    if not user_id:
        return jsonify({'message': 'User ID is required'}), 400

    closeIssue(code, user_id)
    return jsonify({'message': 'Issue closed successfully'}), 200

@app.route('/task/open/<code>', methods=['POST'])
def issue_open(code):
    data = request.get_json()
    user_id = data.get('user_id')  # Assuming the client sends the user ID in the request

    if not user_id:
        return jsonify({'message': 'User ID is required'}), 400

    openIssue(code, user_id)
    return jsonify({'message': 'Issue opened successfully'}), 200


@app.route('/task/add-comment/<code>', methods=['POST'])
def issue_add_comment(code):
    data = request.get_json()
    user_id = data.get('user_id')  # Assuming the client sends the user ID in the request
    content = data.get('content')  # Assuming the client sends the comment content in the request

    if not user_id or not content:
        return jsonify({'message': 'User ID and comment content are required'}), 400

    addComment(code, {"content": content, "by": user_id})
    return jsonify({'message': 'Comment added successfully'}), 200

@app.route('/manager/account')
def account_page():
    data = request.get_json()
    user_id = data.get('id')
    user = mongo.db.personnel.find_one({'id': user_id})

    if not user_id:
        return jsonify({'message': 'ID is required'}), 400
    
    if not user:
        return jsonify({'message': 'Invalid ID'}), 401
    
    user['_id'] = str(user['_id'])  # Convert ObjectId to string for JSON serialization
    return jsonify({'user': user}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
    print(mongo.db.users.find().pretty())
