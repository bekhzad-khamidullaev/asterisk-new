from flask import Flask, request, send_file
from flask_httpauth import HTTPBasicAuth
import os
from urllib.parse import unquote

app = Flask(__name__)
auth = HTTPBasicAuth()

users = {
    "username": "password",
    "amiws": "t3sl@admin",
}

valid_tokens = {
    "G1gd4ueLR9yolqUwAmWhLcqdxOc0Z24Mecezk3vvKckadJkjHu38FtiXVoQzbqKu": "username"
}

audio_dir = "/var/spool/asterisk/monitor/"


@auth.verify_password
def verify_password(username, password):
    if username in users and password == users.get(username):
        return username


@auth.login_required
@app.route("/download", methods=["GET"])
def download_route():
    url_path = request.args.get("url")
    token = request.args.get("token")

    if token in valid_tokens:
        url_path = unquote(url_path)
        return download_file(url_path)
    else:
        return "Unauthorized token", 401


def download_file(url_path):
    year, month, day, filename = extract_parameters(url_path)

    file_path = os.path.join(audio_dir, year, month, day, filename)

    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    else:
        return "File not found", 404


def extract_parameters(url_path):
    parts = url_path.split("/")
    year, month, day, filename = parts[-4], parts[-3], parts[-2], parts[-1]
    return year, month, day, filename


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
