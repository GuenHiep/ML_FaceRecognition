from flask import Flask
from config import SECRET_KEY
from routes import student_routes, teacher_routes, attendance_routes

app = Flask(__name__)
app.secret_key = SECRET_KEY

# Đăng ký blueprint
app.register_blueprint(student_routes.bp, url_prefix="/students")
app.register_blueprint(teacher_routes.bp, url_prefix="/teachers")
app.register_blueprint(attendance_routes.bp, url_prefix="/attendance")

if __name__ == "__main__":
    app.run(debug=True)
