import cv2
import numpy as np
import mysql.connector
from datetime import datetime
import time
import socket
import pickle
import sys

# Kết nối đến MySQL
def get_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="tuananh1582",
        database="face_re"
    )

# Lấy dữ liệu sinh viên từ bảng `student`
def get_students_data():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, idsv, users_name, class FROM student")
    students = {}
    for row in cursor.fetchall():
        students[row['idsv']] = {
            'id': row['id'],
            'name': row['users_name'],
            'class': row['class']
        }  
    cursor.close()
    conn.close()
    return students

# Lấy địa chỉ IP của máy
def get_ip_address():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(0)
    try:
        s.connect(('10.254.254.254', 1))
        ip_address = s.getsockname()[0]
    except:
        ip_address = '127.0.0.1'
    finally:
        s.close()
    return ip_address

# Lấy idsv từ đối số dòng lệnh
logged_in_ids = sys.argv[1]  # Lấy idsv của sinh viên đã đăng nhập từ dòng lệnh

# Debugging: Print the `idsv` passed from login
print(f"Received IDSV: {logged_in_ids}")

# Điểm danh và lưu vào bảng attendance
def mark_attendance_in_db(idsv, users_name, class_name, ip_address):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO attendance (idsv, users_name, class, ip_address, timestamp) VALUES (%s, %s, %s, %s, %s)", 
        (idsv, users_name, class_name, ip_address, datetime.now())
    )
    conn.commit()
    cursor.close()
    conn.close()

# Định nghĩa cascade classifier
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

# Đọc mô hình nhận diện đã huấn luyện
recognizer = cv2.face.LBPHFaceRecognizer_create()
recognizer.read('training/recognizer.yml')

# Lấy dữ liệu sinh viên
students_data = get_students_data()

# Đọc label_dict từ file pickle (nếu đã tồn tại)
with open('training/label_dict.pkl', 'rb') as f:
    label_dict = pickle.load(f)

# Khởi tạo camera
cap = cv2.VideoCapture(0)

start_time = time.time() 
max_duration = 30  
attendance_marked = False 
success_message = "" 

while True:
    ret, frame = cap.read()
    if not ret:
        break
    
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    # Phát hiện khuôn mặt
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
    
    for (x, y, w, h) in faces:
        # Vẽ hình chữ nhật quanh khuôn mặt
        cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 0, 0), 2)
        
        # Nhận diện khuôn mặt
        roi_gray = gray[y:y+h, x:x+w]
        label, confidence = recognizer.predict(roi_gray)
        
        # Lấy thông tin sinh viên từ students_data
        if label in label_dict and confidence < 50:
            student_idsv = label_dict[label]
            #print(str(student_idsv) == logged_in_ids)
            if str(student_idsv) == logged_in_ids:
                student_data = students_data.get(student_idsv)
                if student_data:
                    users_name = student_data['name']
                    student_id = student_data['id']
                    class_name = student_data['class']
                    ip_address = get_ip_address()
                    
                    cv2.putText(frame, f"{users_name} ({student_idsv})", (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                    
                    if not attendance_marked:
                        mark_attendance_in_db(student_idsv, users_name, class_name, ip_address)
                        
                        success_message = "Successfully!!!"
                        attendance_marked = True
                        break  

    elapsed_time = time.time() - start_time
    if elapsed_time > max_duration:
        print("30 giây đã hết.")
        cv2.putText(frame, "Time is up! 30 seconds passed.", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        break

    if success_message:
        cv2.putText(frame, success_message, (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    
    cv2.imshow('Recognizing Face', frame)
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Giải phóng camera và đóng tất cả cửa sổ
cap.release()
cv2.destroyAllWindows()
