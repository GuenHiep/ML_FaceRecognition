from flask import Flask
from routes.auth import auth
from routes.attendance import attendance
from routes.students import students
from routes.teachers import teachers
from routes.subjects import subjects
from routes.classes import classes


app = Flask(__name__)
app.secret_key = "QDJSUIEWFNQKOWFMDVI"

# Đăng ký các Blueprint
app.register_blueprint(auth)
app.register_blueprint(attendance, url_prefix="/attendance")
app.register_blueprint(students, url_prefix="/students")
app.register_blueprint(teachers, url_prefix="/teachers")
app.register_blueprint(subjects, url_prefix="/subjects")
app.register_blueprint(classes, url_prefix="/classes")

if __name__ == "__main__":
    app.run(debug=True)
