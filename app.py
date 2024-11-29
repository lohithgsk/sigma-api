from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import ssl, smtplib, hashlib, uuid
from flask import Flask, request, jsonify, render_template, render_template_string, Response
from flask_pymongo import PyMongo
import json
import random, string, requests, subprocess
from flask_cors import CORS, cross_origin
from flask_jwt_extended import (
    JWTManager,
    jwt_required,
    create_access_token,
    get_jwt_identity,
)
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os
import time
from pytz import timezone

load_dotenv()
########################################################################
import cv2
import numpy as np

import base64

from PIL import Image
from io import StringIO, BytesIO
import io


########################################################################

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle
from reportlab.lib.units import inch
import matplotlib
matplotlib.use('agg')
import matplotlib.pyplot as plt
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph
from reportlab.platypus import Table, TableStyle, Paragraph
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

########################################################################

def qr_decoder(image):
    # Initialize the QRCode detector
    detector = cv2.QRCodeDetector()

    # Detect and decode the QR code
    data, vertices_array, _ = detector.detectAndDecode(image)

    if vertices_array is not None and data:
        return data  # Return the decoded data as a string

    raise ValueError("No QR code found in the image.")

# Function to convert a Base64 string to an OpenCV-compatible image
def readb64(uri):
    encoded_data = uri.split(",")[1]
    nparr = np.frombuffer(base64.b64decode(encoded_data), np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    return img


#########################################################################


app = Flask(__name__)
app.config["MONGO_URI"] = os.getenv("MONGO_URI")
app.secret_key = os.getenv("SECRET_KEY")
app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY")
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(days=1)
jwt = JWTManager(app)
CORS(app)

mongo = PyMongo(app)
# BASE_URL = "https://api.gms.intellx.in"
BASE_URL = "http://127.0.0.1:5001"
# BASE_URL = "https://sigma-api.vercel.app"
# BASE_URL = "https://sigma-api-r7ao.onrender.com"


def get_hash(clear: str):
    return hashlib.sha224(clear.encode("utf-8")).hexdigest()


def sendmail(
    mail_met, receiver, subject, short_subject, text, html="NOT INPUT BY USER."
):
    mailid = os.getenv("EMAILID")
    mailps = os.getenv("EMAILPS")
    if html == "NOT INPUT BY USER.":
        html = render_template(
            "email.html",
            mail=receiver,
            message=text,
            subject=short_subject,
            mail_met=mail_met,
        )

    sender_email = mailid
    receiver_email = receiver
    password = mailps
    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = sender_email
    message["To"] = receiver_email
    part1 = MIMEText(text, "plain")
    part2 = MIMEText(html, "html")
    message.attach(part1)
    message.attach(part2)

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
        server.login(sender_email, password)
        server.sendmail(sender_email, receiver_email, message.as_string())


def createIssue(data: dict):
    """
    the createIssue function creates an Issue and appends it to the DataBase, and takes "data",
    a dictionary as input.
    {
        "name"        : str
        "id"          : str
        "issueType"   : str
        "issueContent": str
        "block"       : str
        "floor"       : str
        "actionItem"  : str
        "comments"    : [
                          {
                            "by"      : str
                            "content" : str
                          }
                        ]
        "survey"      : {
                            "key" : str (a set of keys and values)
                        }
        "anonymity"   : str (true/false)
    }
    """

    rightNow = datetime.now(timezone("Asia/Kolkata"))
    newEntry = {
        "issueNo": "".join(random.choices(string.ascii_uppercase + string.digits, k=5)),
        "time": rightNow.strftime("%I:%M %p"),
        "date": rightNow.strftime("%d/%m/%y"),
        "ISODateTime": rightNow.isoformat(),
        "raised_by": {"name": data["name"], "personId": data["id"]},
        "issue": {
            "issueLastUpdateTime": rightNow.strftime("%I:%M %p"),
            "issueLastUpdateDate": rightNow.strftime("%d/%m/%y"),
            "issueType": data["issueType"],
            "issueCat": data["issueCat"],
            "issueContent": data["issueContent"],
            "block": data["block"],
            "floor": data["floor"],
            "actionItem": data["actionItem"],
        },
        "comments": [
            {
                "date": rightNow.strftime("%d-%m-%y %I:%M %p"),
                "by": data["comments"][0]["by"],
                "content": data["comments"][0]["content"],
            }
        ],
        "status": "OPEN",
        "log": [
            {
                "date": rightNow.strftime("%d-%m-%y %H:%M"),
                "action": "opened",
                "by": data["id"],
            }
        ],
        "survey": data["survey"],
        "anonymity": data["anonymity"],
    }

    mongo.db.dataset.insert_one(newEntry)

    return newEntry["issueNo"]


def openIssue(issueId: str, personId: str):
    """
    openIssue is a function which takes in 2 parameters, issueId and personId,
    and utilizes these parameters to search for an issue by issueId, mark the
    issue as open, and add "opened by personId" to the logs.
    """

    rightNow = datetime.now(timezone("Asia/Kolkata"))

    issueEntry = mongo.db.dataset.find_one({"issueNo": issueId})

    log = issueEntry.get("log")
    log.append(
        {
            "date": rightNow.strftime("%d-%m-%y %H:%M"),
            "action": "opened",
            "by": personId,
        }
    )
    issue = issueEntry.get("issue")
    issue["issueLastUpdateDate"] = rightNow.strftime("%d/%m/%y")
    issue["issueLastUpdateTime"] = rightNow.strftime("%I:%M %p")
    mongo.db.dataset.update_one(
        {"_id": issueEntry.get("_id")},
        {"$set": {"log": log, "status": "OPEN", "issue": issue}},
    )


def closeIssue(issueId: str, personId: str):
    """
    closeIssue is a function which takes in 2 parameters, issueId and personId,
    and utilizes these parameters to search for an issue by issueId, mark the
    issue as close, and add "closed by personId" to the logs.
    """

    rightNow = datetime.now(timezone("Asia/Kolkata"))

    issueEntry = mongo.db.dataset.find_one({"issueNo": issueId})

    log = issueEntry.get("log")
    log.append(
        {
            "date": rightNow.strftime("%d-%m-%y %H:%M"),
            "action": "closed",
            "by": personId,
        }
    )
    issue = issueEntry.get("issue")
    issue["issueLastUpdateDate"] = rightNow.strftime("%d/%m/%y")
    issue["issueLastUpdateTime"] = rightNow.strftime("%I:%M %p")
    mongo.db.dataset.update_one(
        {"_id": issueEntry.get("_id")},
        {"$set": {"log": log, "status": "CLOSE", "issue": issue}},
    )


def addComment(issueId: str, comment: dict):
    """
    addComment is a function which takes in 2 parameters, issueId and comment,
    and utilizes these parameters to search for an issue by issueId, mark the
    issue as close, and add "closed by personId" to the logs.
    """

    rightNow = datetime.now()

    issueEntry = mongo.db.dataset.find_one({"issueNo": issueId})

    comments = issueEntry.get("comments")
    comments.append(
        {
            "date": rightNow.strftime("%d-%m-%y %H:%M"),
            "by": comment["by"],
            "content": [{"by": comment["by"], "content": comment["content"]}],
        }
    )
    issue = issueEntry.get("issue")
    issue["issueLastUpdateDate"] = rightNow.strftime("%d/%m/%y")
    issue["issueLastUpdateTime"] = rightNow.strftime("%I:%M %p")
    mongo.db.dataset.update_one(
        {"_id": issueEntry.get("_id")}, {"$set": {"comments": comments, "issue": issue}}
    )


@app.route("/")
def home():
    project_info = {
        "project_name": "SIGMA | General Maintenance Software | API",
        "contributors": {
            "Frontend": ["Navaneetha Krishnan", "Abinav", "Kavvya"],
            "Backend": ["Aaditya Rengarajan", "Lohith S", "Maanasa S"],
            "Advisors": ["Dr.Sundaram M", "Dr.Priya", "Dr.L.S.Jayashree"],
        },
    }
    return jsonify(project_info)


@app.route("/client/register", methods=["POST"])
def client_register():
    data = request.get_json()
    if not data:
        return jsonify({"message": "No input data provided"}), 400

    name = data.get("name")
    user_id = data.get("id").lower()
    password = data.get("password")

    if not name or not user_id or not password:
        return jsonify({"message": "Name, ID, and password are required"}), 400

    existing_user = mongo.db.users.find_one({"id": user_id})

    if existing_user:
        return jsonify({"message": "User already exists"}), 409

    hashed_password = get_hash(password)
    confirm_key = str(uuid.uuid4()).split("-")[0].upper()

    confirmation_link = f"{BASE_URL}/client/confirm/{confirm_key}"
    sendmail(
        mail_met={"type": "welcome"},
        receiver=f"{user_id}@psgtech.ac.in",
        subject="[PSG-GMS-SIGMA] Welcome!",
        short_subject="Welcome!",
        text=f"""Dear {name},
        <br/>Welcome to "SIGMA" General Maintenance Software by PSG College of Technology! Please click the link below to confirm your e-mail and start using the software.
        <br/><br/>
        <a style="text-decoration:none;background-color: #2A4BAA;font-size: 20px;border: none;color: white;border-radius: 10px;padding-top: 10px;padding-bottom: 10px;padding-left: 30px;padding-right: 30px;" href="{confirmation_link}">Confirm E-Mail</a>
        <br/><br/>
        If the button does not work, please visit {confirmation_link} and confirm.
        <br/>Thank You.""",
    )

    mongo.db.users.insert_one(
        {
            "name": name,
            "id": user_id,
            "hashword": hashed_password,
            "confirmed": False,
            "confkey": confirm_key,
        }
    )

    return (
        jsonify({"message": "Please check your e-mail to confirm your registration."}),
        201,
    )

@app.route("/client/confirm/<confkey>", methods=["GET"])
def client_confirm_email(confkey):
    user = mongo.db.users.find_one({"confkey": confkey})

    if not user:
        # Render template for invalid confirmation key
        return render_template(
            "response.html",
            message="The confirmation key you provided is invalid. Please check your email or contact support."
        ), 400

    # Update user as confirmed
    mongo.db.users.update_one(
        {"confkey": confkey}, {"$set": {"confirmed": True, "confkey": ""}}
    )

    # Render template for successful confirmation
    return render_template(
        "response.html",
        message="Email confirmed successfully! You can now log in to your account."
    ), 200


@app.route("/client/login", methods=["POST"])
def client_login():
    data = request.get_json()
    user_id = data.get("id").lower()
    password = data.get("password")

    if not user_id or not password:
        return jsonify({"message": "ID and password are required"}), 400

    user = mongo.db.users.find_one({"id": user_id})

    if not user or get_hash(password) != user["hashword"]:
        return jsonify({"message": "Invalid ID or password"}), 401

    if not user["confirmed"]:
        return (
            jsonify({"message": "Email not confirmed. Please check your email."}),
            403,
        )

    access_token = create_access_token(identity={"id": user_id, "name": user["name"]})
    user.pop("hashword", None)
    user.pop("_id", None)
    return (
        jsonify({"message": "Login successful", "token": access_token, "user": user}),
        200,
    )


@app.route("/client/update", methods=["PUT"])
def client_update_user():
    data = request.get_json()
    user_id = data.get("id").lower()
    new_data = data.get("new_data")

    if not user_id or not new_data:
        return jsonify({"message": "ID and new data are required"}), 400

    user = mongo.db.users.find_one({"id": user_id})

    if not user:
        return jsonify({"message": "User not found"}), 404

    mongo.db.users.update_one({"id": user_id}, {"$set": new_data})

    return jsonify({"message": "User updated successfully"}), 200


@app.route("/client/delete", methods=["DELETE"])
def client_delete_user():
    data = request.get_json()
    user_id = data.get("id").lower()

    if not user_id:
        return jsonify({"message": "ID required"}), 400

    user = mongo.db.users.find_one({"id": user_id})

    if not user:
        return jsonify({"message": "User not found"}), 404

    mongo.db.users.delete_one({"id": user_id})

    return jsonify({"message": "User deleted successfully"}), 200


@app.route("/client/reset_password", methods=["POST"])
def client_reset_password():
    data = request.get_json()
    user_id = data.get("id").lower()
    old_password = data.get("old_password")
    new_password = data.get("new_password")

    if not user_id or not old_password or not new_password:
        return (
            jsonify({"message": "ID, old password, and new password are required"}),
            400,
        )

    user = mongo.db.users.find_one({"id": user_id})

    if not user:
        return jsonify({"message": "User not found"}), 404

    if get_hash(old_password) != user["hashword"]:
        return jsonify({"message": "Old password is incorrect"}), 401

    hashed_password = get_hash(new_password)
    mongo.db.users.update_one({"id": user_id}, {"$set": {"hashword": hashed_password}})

    return jsonify({"message": "Password reset successfully"}), 200


@app.route("/client/forgot_password", methods=["POST"])
def client_forgot_password():
    data = request.get_json()
    user_id = data.get("id").lower()

    if not user_id:
        return jsonify({"message": "ID required"}), 400

    user = mongo.db.users.find_one({"id": user_id})

    if not user:
        return jsonify({"message": "User not found"}), 404

    reset_key = str(uuid.uuid4()).split("-")[0].upper()
    reset_link = f"{BASE_URL}/client/reset/{reset_key}"
    sendmail(
        mail_met={"type": "reset_password"},
        receiver=f"{user_id}@psgtech.ac.in",
        subject="[PSG-GMS-SIGMA] Reset Your Password",
        short_subject="Reset Your Password",
        text=f"""Dear {user['name']},
        <br/>We received a request to reset your password. Please click the link below to reset your password.
        <br/><br/>
        <a style="text-decoration:none;background-color: #2A4BAA;font-size: 20px;border: none;color: white;border-radius: 10px;padding-top: 10px;padding-bottom: 10px;padding-left: 30px;padding-right: 30px;" href="{reset_link}">Reset Password</a>
        <br/><br/>
        If the button does not work, please visit {reset_link} and reset your password.
        <br/>Thank You.""",
    )

    mongo.db.users.update_one({"id": user_id}, {"$set": {"reset_key": reset_key}})

    return jsonify({"message": "Please check your e-mail to reset your password."}), 200


@app.route("/client/forgot_password/reset", methods=["POST"])
def client_forgot_password_reset():
    data = request.get_json()
    reset_key = data.get("reset_key").upper()
    new_password = data.get("new_password")
    user = mongo.db.users.find_one({"reset_key": reset_key})

    if not user:
        return jsonify({"message": "Invalid or expired reset key"}), 400
    
    hashed_password = get_hash(new_password)
    mongo.db.users.update_one({"reset_key": reset_key}, {"$set": {"hashword": hashed_password}})

    return jsonify({"message": "Password reset successfully"}), 200
      

@app.route("/client/reset/<reset_key>", methods=["GET"])
def client_reset_password_page(reset_key):
    user = mongo.db.users.find_one({"reset_key": reset_key})

    if not user:
        return jsonify({"message": "Invalid or expired reset key"}), 400

    return render_template("reset_password.html", reset_key=reset_key)


@app.route("/client/update_password", methods=["POST"])
def client_update_password():
    reset_key = request.form.get("reset_key")
    new_password = request.form.get("new_password")

    if not reset_key or not new_password:
        return jsonify({"message": "Reset key and new password are required"}), 400

    user = mongo.db.users.find_one({"reset_key": reset_key})

    if not user:
        return jsonify({"message": "Invalid or expired reset key"}), 400

    hashed_password = get_hash(new_password)
    mongo.db.users.update_one(
        {"reset_key": reset_key},
        {"$set": {"hashword": hashed_password, "reset_key": ""}},
    )

    return jsonify({"message": "Password updated successfully"}), 200


@app.route("/client/issues/total", methods=["GET"])
def total_issues():
    total_issues_count = mongo.db.dataset.count_documents({})
    return jsonify({"total_issues": total_issues_count})


@app.route("/client/issues/total/open", methods=["GET"])
def open_issues():
    open_issues_count = mongo.db.dataset.count_documents({"status": "OPEN"})
    return jsonify({"open_issues": open_issues_count})


@app.route("/client/issues/total/closed", methods=["GET"])
def closed_issues():
    closed_issues_count = mongo.db.dataset.count_documents({"status": "CLOSE"})
    return jsonify({"closed_issues": closed_issues_count})


@app.route("/client/issue/status", methods=["POST"])
def issue_status():
    data = request.get_json()
    if not data:
        return (
            jsonify({"status": "error", "message": "Invalid or missing JSON data"}),
            400,
        )

    user_id = data.get("user_id")
    if not user_id:
        return (
            jsonify({"status": "error", "message": "Missing user_id in request data"}),
            400,
        )

    try:
        issues = mongo.db.dataset.find()
        my_issues = []
        for i in issues:
            if i["raised_by"]["personId"] == user_id:
                my_issues.append(
                    {
                        "category": i["issue"]["issueCat"],
                        "code": i["issueNo"],
                        "status": i["status"],
                        "date": i["date"],
                        "issueType": i["issue"]["issueType"],
                        "desc": (
                            f"{i['issue']['issueContent'][:75]}..."
                            if len(i["issue"]["issueContent"]) > 75
                            else i["issue"]["issueContent"]
                        ),
                    }
                )

        return jsonify({"status": "success", "data": my_issues}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/client/issue/status/<code>", methods=["POST"])
def client_issue_status_description(code):
    return issue_status_description(code)


@app.route("/client/issue/add-comment/<code>", methods=["GET", "POST"])
def client_issue_add_comment(code):
    return issue_add_comment(code)


@app.route("/client/issue/close/<code>")
def client_issue_close(code):
    return issue_close(code)


@app.route("/client/issue/open/<code>")
def client_issue_open(code):
    return issue_open(code)


@app.route("/client/account", methods=["POST"])
def client_account_page():
    data = request.get_json()
    user_id = data.get("id")
    user = mongo.db.users.find_one({"id": user_id})

    if not user_id:
        return jsonify({"message": "ID is required"}), 400

    if not user:
        return jsonify({"message": "Invalid ID"}), 401

    user.pop("hashword", None)
    user.pop("_id", None)  # Convert ObjectId to string for JSON serialization
    return jsonify({"user": user}), 200


@app.route("/client/issue/report/qr", methods=["POST"])
def report_issue_qr():
    data = request.get_json()

    user_id = data.get("id")
    if not user_id:
        return jsonify({"message": "User ID is required"}), 400

    file_data = data.get("file")
    if not file_data:
        return jsonify({"message": "File data is required"}), 400

    try:
        img = readb64(file_data)
        qr_result = qr_decoder(img)
        return jsonify({"qr_result": qr_result}), 200
    except Exception as e:
        return jsonify({"message": str(e)}), 500


@app.route("/client/issue/report", methods=["POST"])
def report_issue():
    data = request.get_json()

    if not data:
        return jsonify({"message": "Request data is required"}), 400

    # Get user details from request data
    user_id = data.get("id")
    user_name = data.get("name")

    if not user_id or not user_name:
        return jsonify({"message": "User ID and name are required"}), 400

    # Extract and format survey data
    survey = {}
    for key, value in data.items():
        if key.startswith("survey-"):
            name = key.replace("survey-", "").replace("-", " ")
            name = " ".join(word.capitalize() for word in name.split(" "))
            survey[name] = value

    issue_data = {
        "name": user_name,
        "id": user_id,
        "issueType": data.get("issueType"),
        "issueCat": data.get("issueCat").upper(),
        "issueContent": data.get("issueContent"),
        "block": data.get("block"),
        "floor": data.get("floor"),
        "actionItem": data.get("actionItem"),
        "comments": [{"by": user_id, "content": data["comments"]}],
        "survey": survey,
        "anonymity": "true" if data.get("anonymity") == "on" else "false",
    }

    issue_id = createIssue(issue_data)

    return (
        jsonify({"message": "Issue reported successfully", "issue_id": issue_id}),
        201,
    )

@app.route('/client/get_similar_issues', methods=['GET'])
def client_get_similar_issues():
    # Get parameters
    block = request.args.get('block')
    floor = request.args.get('floor')
    today_date = datetime.now(timezone("Asia/Kolkata")).strftime("%d/%m/%y")

    # Build query
    query = {"date": today_date}  # Match today's date
    if block:
        query["block"] = block  # Match block if provided
    if floor:
        query["floor"] = floor  # Match floor if provided

    # Fetch data from MongoDB using the query
    issues = list(mongo.db.dataset.find(query, {"_id": 0}))  # Exclude `_id` from results for simplicity

    return jsonify(issues)



#########################################################################################################################################


def workEfficiency():
    """
    workEffeciency is a function which takes no parameters, analyzes the database and
    returns the workEffeciency as a float in percentage when called.
    """

    totSuggestion = 0
    totComplaint = 0
    closedComplaint = 0
    closedSuggestion = 0
    entries = mongo.db.dataset.find()
    for issueEntry in entries:
        if (
            datetime.strptime(issueEntry["issue"]["issueLastUpdateDate"], "%d/%m/%y")
            - datetime.now()
        ).days <= 30:
            if issueEntry["issue"]["issueType"].lower() == "suggestion":
                totSuggestion += 1
                if issueEntry["status"].upper() == "CLOSE":
                    closedSuggestion += 1

            else:
                totComplaint += 1
                if issueEntry["status"].upper() == "CLOSE":
                    closedComplaint += 1
    workEff = 0.6 * ((closedComplaint / totComplaint) * 100) + 0.4 * (
        (closedSuggestion / totSuggestion) * 100
    )

    monthly = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    monthly_resolved = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    for issueEntry in entries:
        date = int(
            datetime.strptime(
                issueEntry["issue"]["issueLastUpdateDate"], "%d/%m/%y"
            ).strftime("%m")
        )
        monthly[date - 1] += 1
    for issueEntry in entries:
        date = int(
            datetime.strptime(
                issueEntry["issue"]["issueLastUpdateDate"], "%d/%m/%y"
            ).strftime("%m")
        )
        if issueEntry["status"].upper() == "CLOSE":
            monthly_resolved[date - 1] += 1
    return {
        "COMP": closedComplaint,
        "SUGG": (totComplaint - closedComplaint),
        "EFFE": round(workEff, 2),
        "TOTA": totComplaint,
        "GRAP": monthly,
        "GRAP_RES": monthly_resolved,
    }


def newUser(details: dict):

    mongo.db.personnel.insert_one(
        {
            "name": details["name"],
            "id": details["id"],
            "hashword": details["hashword"],
            "confirmed": True,
            "approved": True,
            "mod": 0,
        }
    )


def priority(task: dict):
    """
    priority is a function which takes the task as a dictionary, analyzes the task and returns
    a priority integer when called.
    """

    if task["issue"]["issueType"] == "ISSUE":
        priority = 1
    elif task["issue"]["issueType"] == "SUGGESTION":
        priority = 2
    else:
        priority = 1
    return priority


@app.route("/manager/register", methods=["POST"])
def manager_register():
    data = request.get_json()
    if not data:
        return jsonify({"message": "No input data provided"}), 400

    name = data.get("name")
    user_id = data.get("id").lower()
    password = data.get("password")

    if not name or not user_id or not password:
        return jsonify({"message": "Name, ID, and password are required"}), 400

    existing_user = mongo.db.personnel.find_one({"id": user_id})

    if existing_user:
        return jsonify({"message": "User already exists"}), 409

    hashed_password = get_hash(password)
    confirm_key = str(uuid.uuid4()).split("-")[0].upper()

    confirmation_link = f"{BASE_URL}/manager/confirm/{confirm_key}"
    sendmail(
        mail_met={"type": "welcome"},
        receiver=f"{user_id}@psgtech.ac.in",
        subject="[PSG-GMS-SIGMA] Welcome!",
        short_subject="Welcome!",
        text=f"""Dear {name},
        <br/>Welcome to "SIGMA" General Maintenance Software by PSG College of Technology! Please click the link below to confirm your e-mail and start using the software.
        <br/><br/>
        <a style="text-decoration:none;background-color: #2A4BAA;font-size: 20px;border: none;color: white;border-radius: 10px;padding-top: 10px;padding-bottom: 10px;padding-left: 30px;padding-right: 30px;" href="{confirmation_link}">Confirm E-Mail</a>
        <br/><br/>
        If the button does not work, please visit {confirmation_link} and confirm.
        <br/>Thank You.""",
    )

    mongo.db.personnel.insert_one(
        {
            "name": name,
            "id": user_id,
            "hashword": hashed_password,
            "confirmed": False,
            "approved": False,
            "mod": 0,
            "confkey": confirm_key,
        }
    )

    return (
        jsonify({"message": "Please check your e-mail to confirm your registration."}),
        201,
    )


# self email confirmation
@app.route("/manager/confirm/<confkey>", methods=["GET"])
def manager_confirm_email(confkey):
    users = list(mongo.db.personnel.find())
    user_to_confirm = None

    for user in users:
        if user.get("confkey") == confkey:
            user_to_confirm = user
            break

    if not user_to_confirm:
        return render_template(
            "response.html",
            message="Invalid confirmation key"
        ), 400

    
    if user_to_confirm.get("confirmed"):
        return render_template(
            "response.html",
            message="E-Mail is already confirmed"
        ), 200

    mod_key = str(uuid.uuid4()).split("-")[0].upper()
    mongo.db.personnel.update_one(
        {"_id": user_to_confirm.get("_id")},
        {"$set": {"confirmed": True, "approved": False, "mod": 0, "modkey": mod_key}},
    )

    id = user_to_confirm["id"]
    name = user_to_confirm["name"]
    sendmail(
        {"type": "welcome"},
        f"{id}@psgtech.ac.in",
        "[PSG-GMS-SIGMA] E-Mail Confirmed. Welcome!",
        "Your E-Mail has been Confirmed!",
        f"""Dear {name},
        <br/>Welcome to "SIGMA" General Maintenance Software by PSG College of Technology! Your E-Mail has been Confirmed. Please await approval from a moderator, so you can start using the application!
        <br/>Thank You.""",
    )

    for user in users:
        if user["mod"] == 1:
            sendmail(
                {"type": "welcome"},
                f"{user['id']}@psgtech.ac.in",
                "[PSG-GMS-SIGMA] Approve New Registration",
                "Please Approve New Registration to the System",
                f"""Dear {user["name"]},
                <br/>{name} [{id}@psgtech.ac.in] has registered as a maintenance staff under the "SIGMA" General Maintenance Software by PSG College of Technology. Please, as a moderator, approve the user, so {name} can start using the application!
                <br/><br/>
                <a style="text-decoration:none;background-color: #2A4BAA;font-size: 20px;border: none;color: white;border-radius: 10px;padding-top: 10px;padding-bottom: 10px;padding-left: 30px;padding-right: 30px;" href="{BASE_URL}/manager/approve/{confkey}">Approve User</a>
                <br/><br/>
                If the button does not work, please visit {BASE_URL}/manager/approve/{confkey} and confirm.
                <br/><br/>
                If you do <b>NOT</b> know who this is, please <b>do NOT</b> confirm.
                <br/>Thank You.""",
            )

    return render_template(
        "response.html",
        message="Welcome to \"SIGMA\" General Maintenance Software by PSG College of Technology! Your E-Mail has been Confirmed. Please await approval from a moderator, so you can start using the application!"
    ), 200


# account approval from a moderator
@app.route("/manager/approve/<confkey>", methods=["GET"])
def manager_approve_email(confkey):
    users = list(mongo.db.personnel.find())
    user_to_approve = None

    for user in users:
        if user.get("confkey") == confkey:
            user_to_approve = user
            break

    if not user_to_approve:    
        return render_template(
            "response.html",
            message="Invalid confirmation key"
        ), 400
    
    if user_to_approve.get("approved"):
        return render_template(
            "response.html",
            message="User is already approved"
        ), 200

    mod_key = str(uuid.uuid4()).split("-")[0].upper()
    mongo.db.personnel.update_one(
        {"_id": user_to_approve.get("_id")},
        {"$set": {"confirmed": True, "approved": True, "mod": 0, "modkey": mod_key}},
    )

    id = user_to_approve["id"]
    name = user_to_approve["name"]

    for user in users:
        if user["mod"] == 1:
            sendmail(
                {"type": "welcome"},
                f"{user['id']}@psgtech.ac.in",
                "[PSG-GMS-SIGMA] Approve New Registration",
                "Please Approve New Registration to the System",
                f"""Dear {user["name"]},
                <br/>{name} [{id}@psgtech.ac.in] has been approved as a maintenance staff under the "SIGMA" General Maintenance Software by PSG College of Technology. If you wish for {name} to be a moderator, please escalate user privileges by clicking this button:
                <br/><br/>
                <a style="text-decoration:none;background-color: #2A4BAA;font-size: 20px;border: none;color: white;border-radius: 10px;padding-top: 10px;padding-bottom: 10px;padding-left: 30px;padding-right: 30px;" href="{BASE_URL}/manager/escalate/{mod_key}">Escalate User</a>
                <br/><br/>
                If the button does not work, please visit {BASE_URL}/manager/escalate/{mod_key}.
                <br/><br/>
                If you do <b>NOT</b> know who this is, please <b>do NOT</b> confirm.
                <br/>Thank You.""",
            )

    sendmail(
        {"type": "welcome"},
        f"{id}@psgtech.ac.in",
        "[PSG-GMS-SIGMA] Log-In Account Approved. Welcome!",
        "Your Log-In Account has been Approved!",
        f"""Dear {name},
        <br/>Welcome to "SIGMA" General Maintenance Software by PSG College of Technology! Your Log-In Account has been Approved. Please download and open the application and Log-In as usual so you can start using the application!
        <br/>Thank You.""",
    )

    return render_template(
        "response.html",
        message="You have approved this user. If you wish to escalate this person's privileges and approve as a moderator, check email for further instructions."
    ), 200


@app.route("/manager/escalate/<modkey>", methods=["GET"])
def manager_escalate_email(modkey):
    users = list(mongo.db.personnel.find())
    user_to_escalate = None

    for user in users:
        if user.get("modkey") == modkey:
            user_to_escalate = user
            break

    if not user_to_escalate:    
        return render_template(
            "response.html",
            message="Invalid moderator key"
        ), 400

    # Check if the user is already a moderator
    if user_to_escalate.get("mod") == 1:    
        return render_template(
            "response.html",
            message="User is already a moderator"
        ), 200

    mongo.db.personnel.update_one(
        {"_id": user_to_escalate.get("_id")},
        {"$set": {"confirmed": True, "approved": True, "mod": 1}},
    )

    id = user_to_escalate["id"]
    name = user_to_escalate["name"]

    sendmail(
        {"type": "welcome"},
        f"{id}@psgtech.ac.in",
        "[PSG-GMS-SIGMA] Privileges Escalated to Moderator Status!",
        "Congrats! You have been Assigned to Moderator Status with Account Approval Privileges!",
        f"""Dear {name},
        <br/>Welcome to "SIGMA" General Maintenance Software by PSG College of Technology! You have been Assigned to Moderator Status with Account Approval Privileges! You will now be notified via e-mail whenever someone creates a new account, and be responsible for approval of new accounts!
        <br/>Thank You.""",
    )

    return render_template(
        "response.html",
        message="You have escalated this user's privileges to moderator status."
    ), 200

@app.route("/manager/delete", methods=["POST"])
def manager_delete():
    data = request.get_json()
    user_id = data.get("id").lower()

    if not user_id:
        return jsonify({"message": "ID required"}), 400

    user = mongo.db.personnel.find_one({"id": user_id})

    if not user:
        return jsonify({"message": "User not found"}), 404

    mongo.db.personnel.delete_one({"id": user_id})

    return jsonify({"message": "User deleted successfully"}), 200

@app.route("/manager/reject/<user_id>", methods=["DELETE"])
def reject_user(user_id):
    user = mongo.db.personnel.find_one({"id": user_id})

    if not user:
        return jsonify({"message": "User not found"}), 404

    # Remove user from the database
    mongo.db.personnel.delete_one({"id": user_id})

    # Send rejection email
    rejection_message = f"""Dear {user['name']},
    <br/>We regret to inform you that your registration has been rejected. You can reapply and approach a moderator for further assistance.
    <br/><br/>
    Thank You."""

    sendmail(
        mail_met={"type": "rejection"},
        receiver=f"{user_id}@psgtech.ac.in",
        subject="[PSG-GMS-SIGMA] Registration Rejected",
        short_subject="Registration Rejected",
        text=rejection_message,
    )

    return jsonify({"message": "User has been rejected and notified via email"}), 200


@app.route("/manager/reset_password", methods=["POST"])
def manager_reset_password():
    data = request.get_json()
    user_id = data.get("id")
    old_password = data.get("old_password")
    new_password = data.get("new_password")

    if not user_id or not old_password or not new_password:
        return (
            jsonify({"message": "ID, old password, and new password are required"}),
            400,
        )

    user = mongo.db.personnel.find_one({"id": user_id})

    if not user:
        return jsonify({"message": "User not found"}), 404

    if get_hash(old_password) != user["hashword"]:
        return jsonify({"message": "Old password is incorrect"}), 401

    hashed_password = get_hash(new_password)
    mongo.db.personnel.update_one(
        {"id": user_id}, {"$set": {"hashword": hashed_password}}
    )

    return jsonify({"message": "Password reset successfully"}), 200


@app.route("/manager/forgot_password", methods=["POST"])
def manager_forgot_password():
    """Function Helping Manager Reset Password"""
    data = request.get_json()
    user_id = data.get("id").lower()

    if not user_id:
        return jsonify({"message": "ID required"}), 400

    user = mongo.db.personnel.find_one({"id": user_id})

    if not user:
        return jsonify({"message": "User not found"}), 404

    reset_key = str(uuid.uuid4()).split("-")[0].upper()
    reset_link = f"{BASE_URL}/manager/reset/{reset_key}"
    sendmail(
        mail_met={"type": "reset_password"},
        receiver=f"{user_id}@psgtech.ac.in",
        subject="[PSG-GMS-SIGMA] Reset Your Password",
        short_subject="Reset Your Password",
        text=f"""Dear {user['name']},
        <br/>We received a request to reset your password. Please click the link below to reset your password.
        <br/><br/>
        <a style="text-decoration:none;background-color: #2A4BAA;font-size: 20px;border: none;color: white;border-radius: 10px;padding-top: 10px;padding-bottom: 10px;padding-left: 30px;padding-right: 30px;" href="{reset_link}">Reset Password</a>
        <br/><br/>
        If the button does not work, please visit {reset_link} and reset your password.
        <br/>Thank You.""",
    )

    mongo.db.personnel.update_one({"id": user_id}, {"$set": {"reset_key": reset_key}})

    return jsonify({"message": "Please check your e-mail to reset your password."}), 200

@app.route("/manager/forgot_password/reset", methods=["POST"])
def manager_forgot_password_reset():
    data = request.get_json()
    reset_key = data.get("reset_key").upper()
    new_password = data.get("new_password")
    user = mongo.db.personnel.find_one({"reset_key": reset_key})

    if not user:
        return jsonify({"message": "Invalid or expired reset key"}), 400
    
    hashed_password = get_hash(new_password)
    mongo.db.personnel.update_one({"reset_key": reset_key}, {"$set": {"hashword": hashed_password}})

    return jsonify({"message": "Password reset successfully"}), 200

@app.route("/manager/reset/<reset_key>", methods=["GET"])
def manager_reset_password_page(reset_key):
    user = mongo.db.personnel.find_one({"reset_key": reset_key})

    if not user:
        return jsonify({"message": "Invalid or expired reset key"}), 400

    return render_template("mgr_reset_password.html", reset_key=reset_key)


@app.route("/manager/update_password", methods=["POST"])
def manager_update_password():
    reset_key = request.form.get("reset_key")
    new_password = request.form.get("new_password")

    if not reset_key or not new_password:
        return jsonify({"message": "Reset key and new password are required"}), 400

    user = mongo.db.personnel.find_one({"reset_key": reset_key})

    if not user:
        return jsonify({"message": "Invalid or expired reset key"}), 400

    hashed_password = get_hash(new_password)
    mongo.db.personnel.update_one(
        {"reset_key": reset_key},
        {"$set": {"hashword": hashed_password, "reset_key": ""}},
    )

    return jsonify({"message": "Password updated successfully"}), 200


@app.route("/manager/login", methods=["POST"])
def manager_login():
    data = request.get_json()
    user_id = data.get("id").lower()
    password = data.get("password")

    if not user_id or not password:
        return jsonify({"message": "ID and password are required"}), 400

    user = mongo.db.personnel.find_one({"id": user_id})

    if not user or get_hash(password) != user["hashword"]:
        return jsonify({"message": "Invalid ID or password"}), 401

    if not user["confirmed"]:
        return (
            jsonify({"message": "Email not confirmed. Please check your email."}),
            403,
        )

    # If login is successful, return the entire user data
    access_token = create_access_token(identity={"id": user_id, "name": user["name"], "mod": user["mod"]})
    user.pop("hashword", None)
    user.pop("_id", None)
    return (
        jsonify({"message": "Login successful", "token": access_token, "user": user}),
        200,
    )


@app.route("/administrator/new-user", methods=["POST"])  # adds new personnel member
def adm_new_user():
    data = request.get_json()

    if not data:
        return jsonify({"message": "No JSON data received"}), 400

    new_user = {
        "name": data.get("name"),
        "id": data.get("id"),
        "hashword": get_hash(data.get("hashword")),  # default password is password
        "confirmed": True,
    }

    newUser(new_user)
    return jsonify({"message": "New user created successfully"}), 201


@app.route("/administrator/all-users")
def all_users_table():
    users = mongo.db.users.find()
    my_users = []
    userids = []

    for user in users:
        status = (
            "CONFIRMED" if str(user["confirmed"]).lower() == "true" else "NOT CONFIRMED"
        )
        my_users.append(
            {
                "name": user.get("name"),
                "id": user.get("id"),
                "status": status,
                "role": "USER",
            }
        )
        userids.append(user["id"])

    admin_users = []
    loaded_users = mongo.db.personnel.find()

    for admin_user in loaded_users:
        if admin_user["id"] not in userids:
            status = (
                "CONFIRMED"
                if str(admin_user["confirmed"]).lower() == "true"
                else "NOT CONFIRMED"
            )
            my_users.append(
                {
                    "name": admin_user.get("name"),
                    "id": admin_user.get("id"),
                    "status": status,
                    "role": "ADMIN",
                }
            )

    return jsonify(
        {
            "users": my_users,
            "title": "[PSG COLLEGE OF TECHNOLOGY | MAINTENANCE] ALL USERS",
        }
    )


@app.route("/manager/pending-approval", methods=["GET"])
def get_pending_approval_users():
    pending_users_cursor = mongo.db.personnel.find(
        {"confirmed": True, "approved": False}
    )
    pending_users = []
    for user in pending_users_cursor:
        pending_users.append(
            {
                "name": user["name"],
                "id": user["id"],
                "confirmed": user["confirmed"],
                "approved": user["approved"],
                "confkey": user["confkey"],
                "modkey": user["modkey"],
            }
        )

    pending_count = len(pending_users)

    return jsonify({"count": pending_count, "users": pending_users}), 200


@app.route("/tasks", methods=["GET"])
def get_all_issues():
    issues = mongo.db.dataset.find()
    serialized_issues = []
    for issue in issues:
        issue_dict = {key: value for key, value in issue.items() if key != "_id"}
        serialized_issues.append(issue_dict)
    return jsonify({"issues": serialized_issues})


@app.route("/tasks/count", methods=["GET"])
def count_issues():
    # Get the current date and calculate the date for 365 days and 30 days ago
    current_date = datetime.now()
    date_365_days_ago = current_date - timedelta(days=365)
    date_30_days_ago = current_date - timedelta(days=30)

    # Initialize counters
    count_365_days_open = 0
    count_365_days_closed = 0
    count_30_days_open = 0
    count_30_days_closed = 0

    # Fetch all issues from the database
    issues = mongo.db.dataset.find({"date": {"$exists": True}})

    # Iterate through the issues and count based on the date and status
    for issue in issues:
        issue_date_str = issue.get("date")
        issue_status = issue.get("status")

        try:
            # Convert the issue's date string to a datetime object
            issue_date = datetime.strptime(issue_date_str, "%d/%m/%y")

            # Check and count based on the date comparison and status
            if issue_date >= date_365_days_ago:
                if issue_status == "OPEN":
                    count_365_days_open += 1
                elif issue_status == "CLOSE":
                    count_365_days_closed += 1

            if issue_date >= date_30_days_ago:
                if issue_status == "OPEN":
                    count_30_days_open += 1
                elif issue_status == "CLOSE":
                    count_30_days_closed += 1

        except ValueError:
            # Handle cases where the date format might be incorrect
            print(f"Date format error in issue with ID: {issue.get('_id')}")

    return (
        jsonify(
            {
                "issues_last_365_days": {
                    "total": count_365_days_open + count_365_days_closed,
                    "open": count_365_days_open,
                    "closed": count_365_days_closed,
                },
                "issues_last_30_days": {
                    "total": count_30_days_open + count_30_days_closed,
                    "open": count_30_days_open,
                    "closed": count_30_days_closed,
                },
            }
        ),
        200,
    )


@app.route("/task/status/<code>")
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


@app.route("/tasks/todo")
def task_list_table():
    issues = mongo.db.dataset.find()
    my_issues = []

    for i in issues:
        if i["status"] == "OPEN" and i["issue"]["issueType"] == "Complaint":
            issueDate = datetime.strptime(i["issue"]["issueLastUpdateDate"], "%d/%m/%y")
            ddays = (datetime.now() - issueDate).days
            i.update({"delay_days": ddays})
            i.update({"priority": priority(i)})
            # Remove the "_id" field to avoid JSON serialization issues
            i.pop("_id", None)
            my_issues.append(i)

    return jsonify({"tasks": my_issues})


@app.route("/task/close/<code>", methods=["POST"])
def issue_close(code):
    data = request.get_json()
    user_id = data.get(
        "user_id"
    )  # Assuming the client sends the user ID in the request

    if not user_id:
        return jsonify({"message": "User ID is required"}), 400

    closeIssue(code, user_id)
    return jsonify({"message": "Issue closed successfully"}), 200


@app.route("/task/open/<code>", methods=["POST"])
def issue_open(code):
    data = request.get_json()
    user_id = data.get(
        "user_id"
    )  # Assuming the client sends the user ID in the request

    if not user_id:
        return jsonify({"message": "User ID is required"}), 400

    openIssue(code, user_id)
    return jsonify({"message": "Issue opened successfully"}), 200


@app.route("/task/add-comment/<code>", methods=["POST"])
def issue_add_comment(code):
    data = request.get_json()
    user_id = data.get(
        "user_id"
    )  # Assuming the client sends the user ID in the request
    content = data.get(
        "content"
    )  # Assuming the client sends the comment content in the request

    if not user_id or not content:
        return jsonify({"message": "User ID and comment content are required"}), 400

    addComment(code, {"content": content, "by": user_id})
    return jsonify({"message": "Comment added successfully"}), 200


@app.route("/task/export/<code>")
def issue_status_export(code):
    issue = mongo.db.dataset.find_one({"issueNo": code})

    if issue:
        # Convert ObjectId to string for JSON serialization
        issue["_id"] = str(issue["_id"])

        # Example logic to handle anonymity based on request context (replace with your actual logic)
        if issue.get("anonymity") == "true" and request.args.get("mod") == "1":
            issue["anonymity"] = "false"

        return render_template("issue_report.html", issue=issue)

        # return jsonify({"issue": issue})

    return jsonify({"message": "Issue not found"}), 404


@app.route("/manager/account", methods=["POST"])
def account_page():
    data = request.get_json()
    user_id = data.get("id")
    user = mongo.db.personnel.find_one({"id": user_id})

    if not user_id:
        return jsonify({"message": "ID is required"}), 400

    if not user:
        return jsonify({"message": "Invalid ID"}), 401

    user["_id"] = str(user["_id"])  # Convert ObjectId to string for JSON serialization
    return jsonify({"user": user}), 200



#################################################################################################################


PAGE_WIDTH, PAGE_HEIGHT = A4
MARGIN = 50



# Draw page border
def draw_border(pdf):
    pdf.setStrokeColor(colors.black)
    pdf.rect(MARGIN, MARGIN, PAGE_WIDTH - 2 * MARGIN, PAGE_HEIGHT - 2 * MARGIN)

# Add Sigma header
def add_sigma_header(pdf):
    sigma_url = "static/head.jpg"  # Path to the Sigma header image
    sigma_img = Image.open(sigma_url)
    
    # Calculate image dimensions and positions
    img_width = PAGE_WIDTH - 2 * MARGIN
    img_height = 75
    img_x = MARGIN
    img_y = PAGE_HEIGHT - MARGIN - img_height

    # Draw black border (slightly larger than the image)
    border_thickness = 2
    pdf.setStrokeColor(colors.black)
    pdf.setLineWidth(border_thickness)
    pdf.rect(img_x - border_thickness / 2, img_y - border_thickness / 2, img_width + border_thickness, img_height + border_thickness)

    # Draw the image
    pdf.drawInlineImage(sigma_img, img_x, img_y, width=img_width, height=img_height)

def add_charts(pdf, from_date, to_date):
    
    issues = list(
        mongo.db.dataset.find(
            {"ISODateTime": {
                    "$gte": from_date.isoformat(),  # Convert `from_date` to ISO 8601 format
                    "$lte": to_date.isoformat(),   # Convert `to_date` to ISO 8601 format
                }}))

    # Initialize counters
    categories = {}
    open_issues_count = 0
    closed_issues_count = 0

    for issue in issues:
        category = issue["issue"].get("issueCat", "Unknown")
        status = issue.get("status", "Unknown")

        # Count open and closed issues
        if status == "OPEN":
            open_issues_count += 1
        elif status == "CLOSE":
            closed_issues_count += 1

        # Count issues by category
        if category not in categories:
            categories[category] = {"open": 0, "closed": 0}
        if status == "OPEN":
            categories[category]["open"] += 1
        elif status == "CLOSE":
            categories[category]["closed"] += 1

    # Prepare data for charts
    category_names = list(categories.keys())
    open_issues = [categories[cat]["open"] for cat in category_names]
    closed_issues = [categories[cat]["closed"] for cat in category_names]

    # --- Bar Chart ---
    fig, ax = plt.subplots(figsize=(5, 2))
    bar_width = 0.4
    x = range(len(category_names))

    ax.bar(x, open_issues, width=bar_width, label="Open Issues", color="orange")
    ax.bar([p + bar_width for p in x], closed_issues, width=bar_width, label="Closed Issues", color="blue")

    ax.set_xticks([p + bar_width / 2 for p in x])
    ax.set_xticklabels(category_names, rotation=45, ha="right")
    ax.set_title("Issues by Category")
    ax.set_ylabel("# of Issues")
    ax.legend()

    # Save bar chart to BytesIO buffer
    bar_chart_buffer = BytesIO()
    plt.savefig(bar_chart_buffer, format="PNG", bbox_inches="tight")
    plt.close(fig)
    bar_chart_buffer.seek(0)

    # Embed bar chart in the PDF
    bar_chart_image = Image.open(bar_chart_buffer)
    pdf.drawInlineImage(bar_chart_image, (PAGE_WIDTH / 2) - 200, PAGE_HEIGHT - 500, width=400, height=200)

    # Add pie charts
    add_pie_charts(pdf, categories, open_issues_count, closed_issues_count)


def add_pie_charts(pdf, categories, open_issues_count, closed_issues_count):
    # --- Pie Chart 1: Categories Distribution ---
    labels1 = list(categories.keys())
    sizes1 = [sum(cat_data.values()) for cat_data in categories.values()]
    colors1 = plt.cm.tab20.colors[:len(labels1)]

    fig1, ax1 = plt.subplots()
    ax1.pie(
        sizes1,
        labels=labels1,
        autopct="%1.1f%%" if sum(sizes1) > 0 else None,
        startangle=90,
        colors=colors1,
    )
    ax1.set_title("Complaint Categories Distribution")

    # Save first pie chart to buffer
    pie1_buffer = BytesIO()
    plt.savefig(pie1_buffer, format="PNG", bbox_inches="tight")
    pie1_buffer.seek(0)
    plt.close(fig1)
    pie1_image = Image.open(pie1_buffer)

    # Embed first pie chart in the PDF
    pdf.drawInlineImage(pie1_image, MARGIN + 50, PAGE_HEIGHT - 730, width=200, height=200)

    # --- Pie Chart 2: Open vs Closed Issues ---
    labels2 = ["Open Issues", "Closed Issues"]
    sizes2 = [open_issues_count, closed_issues_count]
    colors2 = ["orange", "blue"]

    fig2, ax2 = plt.subplots()
    ax2.pie(
        sizes2,
        labels=labels2,
        autopct="%1.1f%%" if sum(sizes2) > 0 else None,
        startangle=90,
        colors=colors2,
    )
    ax2.set_title("Open vs Closed Issues")

    # Save second pie chart to buffer
    pie2_buffer = BytesIO()
    plt.savefig(pie2_buffer, format="PNG", bbox_inches="tight")
    pie2_buffer.seek(0)
    plt.close(fig2)
    pie2_image = Image.open(pie2_buffer)

    # Embed second pie chart in the PDF
    pdf.drawInlineImage(pie2_image, MARGIN + 250, PAGE_HEIGHT - 730, width=200, height=200)


def add_table(pdf, table_data, start_y, width=((PAGE_WIDTH - 2 * MARGIN) / 2) - PAGE_WIDTH/3.5):
    table = Table(table_data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    table.wrapOn(pdf, width, PAGE_HEIGHT - start_y)
    table.drawOn(pdf, width, start_y)

PAGE_WIDTH, PAGE_HEIGHT = A4
MARGIN = 30  # Margin around the page

def add_table_d(pdf, table_data, start_y, page_width=PAGE_WIDTH - 2 * MARGIN, page_height=PAGE_HEIGHT):
    # Define column widths dynamically
    col_widths = [page_width / len(table_data[0])] * len(table_data[0])

    # Style for wrapped text
    styles = getSampleStyleSheet()
    cell_style = styles['BodyText']
    cell_style.wordWrap = 'CJK'  # Enable word wrapping

    # Wrap text in cells using Paragraph
    wrapped_data = []
    for row in table_data:
        wrapped_row = [Paragraph(str(cell), cell_style) for cell in row]
        wrapped_data.append(wrapped_row)

    # Create the table
    table = Table(wrapped_data, colWidths=col_widths)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))

    # Calculate available height for the table
    available_height = start_y - MARGIN
    table_height = table.wrap(page_width, available_height)[1]

    # Handle table overflow to the next page if needed
    if table_height > available_height:
        rows_per_page = int(available_height // 27)  # Approximate rows per page
        header = [wrapped_data[0]]  # Keep the header row separate
        data_rows = wrapped_data[1:]

        while data_rows:
            page_data = header + data_rows[:rows_per_page]
            table = Table(page_data, colWidths=col_widths)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            table.wrap(page_width, available_height)
            table.drawOn(pdf, MARGIN, start_y - table.wrap(page_width, available_height)[1])

            # Move to the next page if rows are remaining
            data_rows = data_rows[rows_per_page:]
            if data_rows:
                pdf.showPage()
                draw_border(pdf)  # Ensure border is redrawn
                start_y = page_height - MARGIN
    else:
        table.wrap(page_width, available_height)
        table.drawOn(pdf, MARGIN, start_y - table_height)


# Add footer with page number
def add_footer(pdf, page_no):
    pdf.setFont("Helvetica", 10)
    pdf.drawString(PAGE_WIDTH / 2 - 20, MARGIN / 2, f"Page {page_no}")

# Add blank page at the end
def add_blank_page(pdf):
    draw_border(pdf)
    # pdf.setFont("Helvetica-Italic", 14)
    pdf.drawString(PAGE_WIDTH / 2 - 100, PAGE_HEIGHT / 2, "This page is intentionally left blank.")
    pdf.setFont("Helvetica", 12)
    pdf.drawString(PAGE_WIDTH / 2 - 35, MARGIN / 2, "End of Report")



@app.route('/manager/generate-pdf', methods=['GET'])
def generate_pdf():
    from_date_str = request.args.get('from', None)
    to_date_str = request.args.get('to', None)
    print(from_date_str)

    if not from_date_str or not to_date_str:
        return jsonify({"error": "Both 'from' and 'to' date parameters are required."}), 400

    try:
        # Convert input date strings to datetime objects
        from_date = datetime.strptime(from_date_str, "%d-%m-%Y")
        to_date = datetime.strptime(to_date_str, "%d-%m-%Y")
    except ValueError:
        return jsonify({"error": "Invalid date format. Use 'DD-MM-YYYY'."}), 400

    # Adjust `to_date` to include the entire day
    to_date = to_date + timedelta(days=1) - timedelta(seconds=1)

    # Fetch data from the MongoDB collection within the date range
    issues = list(
        mongo.db.dataset.find(
            {"ISODateTime": {
                    "$gte": from_date.isoformat(),  # Convert `from_date` to ISO 8601 format
                    "$lte": to_date.isoformat(),   # Convert `to_date` to ISO 8601 format
                }}))
    
    # Check if the issues list is empty
    if not issues:
        return jsonify({"error": "No available issues in the given range."}), 404

    # Initialize counters and accumulators
    total_days = 0
    closed_issues_count = 0
    open_issues_count = 0
    total_close_time = 0
    complaint_categories = {}

    for issue in issues:
        try:
            # Extract issue details
            status = issue.get("status")
            category = issue["issue"].get("issueCat", "Unknown")
            logs = issue.get("log", [])

            # Count open and closed issues
            if status == "CLOSE":
                closed_issues_count += 1
            elif status == "OPEN":
                open_issues_count += 1

            # Calculate the most common category
            complaint_categories[category] = complaint_categories.get(category, 0) + 1

            # Calculate total days from logs and closing times
            if logs:
                start_date = datetime.strptime(logs[0]["date"], "%d-%m-%y %H:%M")
                close_dates = [
                    datetime.strptime(log["date"], "%d-%m-%y %H:%M")
                    for log in logs
                    if log["action"] == "closed"
                ]
                if close_dates:
                    total_days += (close_dates[-1] - start_date).days
                    total_close_time += sum(
                        (close_date - start_date).days for close_date in close_dates
                    )

        except Exception as e:
            print(f"Error processing issue {issue.get('_id')}: {e}")

    # Compute metrics
    total_issues = closed_issues_count + open_issues_count
    avg_close_time = total_close_time / closed_issues_count if closed_issues_count > 0 else 0
    most_common_category = max(complaint_categories, key=complaint_categories.get) if complaint_categories else "N/A"

    # PDF generation remains unchanged, update table_data with new metrics
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)

    # Page 1: Overview
    draw_border(pdf)
    add_sigma_header(pdf)
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(((PAGE_WIDTH - 2 * MARGIN) / 2) - 40, PAGE_HEIGHT - 150, "Maintenance Statistics Report")
    pdf.setFont("Helvetica", 12)
    pdf.drawString(((PAGE_WIDTH - 2 * MARGIN) / 2) - 25, PAGE_HEIGHT - 170, f"From {from_date_str} to {to_date_str}")
    table_data = [
        ["Total # of Complaints", str(total_issues)],
        ["# of Closed Complaints", str(closed_issues_count)],
        ["# of Open Complaints", str(open_issues_count)],
        ["Average Time Taken to Close a Complaint", f"{avg_close_time:.2f} days"],
        ["Most Common Complaint Category", most_common_category],
    ]
    add_table(pdf, table_data, PAGE_HEIGHT - 280, ((PAGE_WIDTH - 2 * MARGIN) / 2) - PAGE_WIDTH / 8)
    add_charts(pdf, from_date, to_date)
    pdf.showPage()

    # Page 2: Detailed Table
    draw_border(pdf)
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(PAGE_WIDTH / 2 - 100, PAGE_HEIGHT - 70, "Complaints in Given Time Range")
    pdf.setFont("Helvetica", 12)
    detailed_table_data = [
        ["Category", "Issue ID", "Raised By", "Date", "Location", "Days to Resolve"],
    ]
    for issue in issues:
        detailed_table_data.append([
            issue["issue"].get("issueCat", "Unknown"),
            issue.get("issueNo", "N/A"),
            issue["raised_by"].get("name", "N/A"),
            issue.get("date", "N/A"),
            issue["issue"].get("block", "N/A"),
            str(total_days),  # Placeholder; you can make this specific to each issue
        ])

    add_table_d(pdf, detailed_table_data, start_y=PAGE_HEIGHT - 100)
    add_footer(pdf, 2)
    pdf.showPage()

    # Blank page at the end
    add_blank_page(pdf)

    # Save and return the PDF
    pdf.save()
    buffer.seek(0)
    return Response(buffer, mimetype='application/pdf', headers={"Content-Disposition": "inline;filename=dynamic_report.pdf"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
