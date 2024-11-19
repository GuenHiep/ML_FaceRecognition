import cv2
import os

# Khởi tạo đối tượng camera
cap = cv2.VideoCapture(0)

# Tạo thư mục dataset nếu chưa có
user_name = input("Nhập tên: ")
if not os.path.exists(f'dataset/{user_name}'):
    os.makedirs(f'dataset/{user_name}')

# Định nghĩa cascade classifier cho nhận diện khuôn mặt
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

# Khởi tạo số ảnh đã chụp
count = 0

while True:
    ret, frame = cap.read()
    if not ret:
        break
    
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    # Phát hiện khuôn mặt trong ảnh
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
    
    for (x, y, w, h) in faces:
        # Vẽ hình chữ nhật quanh khuôn mặt
        cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 0, 0), 2)
        
        # Cắt khuôn mặt và lưu ảnh
        face = gray[y:y+h, x:x+w]
        cv2.imwrite(f"dataset/{user_name}/{count}.jpg", face)
        count += 1

    # Hiển thị video
    cv2.imshow('Capturing Images', frame)
    
    # Dừng khi nhấn 'q'
    if count >= 300:
        break
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Giải phóng camera và đóng tất cả cửa sổ
cap.release()
cv2.destroyAllWindows()
