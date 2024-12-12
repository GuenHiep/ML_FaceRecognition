# app.py
from flask import Flask, render_template, request
from routes.authen import student_login_logic

app = Flask(__name__)
app.secret_key = "QDJSUIEWFNQKOWFMDVI"

@app.route("/", methods=["GET", "POST"])
def student_login():
    if request.method == "POST":
        return student_login_logic()
    return render_template("login.html")

if __name__ == "__main__":
    app.run(debug=True)
