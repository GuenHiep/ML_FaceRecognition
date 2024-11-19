import cv2
import numpy as np
import os

# Định nghĩa cascade classifier
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

# Đọc mô hình nhận diện đã huấn luyện
recognizer = cv2.face.LBPHFaceRecognizer_create()
recognizer.read('training/recognizer.yml')

# Đọc tên người dùng từ thư mục dataset
label_dict = {}
user_labels = os.listdir('dataset')
for i, user_name in enumerate(user_labels):
    if os.path.isdir(os.path.join('dataset', user_name)):
        label_dict[i] = user_name

# Khởi tạo camera
cap = cv2.VideoCapture(0)

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
        
        # Hiển thị tên người nhận diện
        name = label_dict.get(label, "Unknown")
        cv2.putText(frame, f"Name: {name}", (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)
    
    # Hiển thị video
    cv2.imshow('Recognizing Face', frame)
    
    # Dừng khi nhấn 'q'
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Giải phóng camera và đóng tất cả cửa sổ
cap.release()
cv2.destroyAllWindows()
