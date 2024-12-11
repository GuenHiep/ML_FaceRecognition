import cv2
import os
import sys

if len(sys.argv) < 2:
    print("ID Sinh Viên (IDSV) không được cung cấp!")
    exit()

idsv = sys.argv[1]

# Khởi tạo đối tượng camera
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("Không thể mở camera")
    exit()

# Tạo thư mục cho ID sinh viên
dataset_folder = f'dataset/{idsv}'
if not os.path.exists(dataset_folder):
    os.makedirs(dataset_folder)

# Định nghĩa cascade classifier cho nhận diện khuôn mặt
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

# Khởi tạo số ảnh đã chụp
count = 0

while True:
    ret, frame = cap.read()
    if not ret:
        print("Không thể đọc khung hình từ camera")
        break

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)  # Chuyển đổi ảnh sang grayscale
    
    # Phát hiện khuôn mặt trong ảnh
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
    
    for (x, y, w, h) in faces:
        # Vẽ hình chữ nhật quanh khuôn mặt
        cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 0, 0), 2)
        
        # Cắt khuôn mặt và lưu ảnh vào thư mục
        face = gray[y:y+h, x:x+w]
        cv2.imwrite(f"{dataset_folder}/{count}.jpg", face)  # Lưu ảnh khuôn mặt
        count += 1

    # Hiển thị video với hình chữ nhật quanh khuôn mặt
    cv2.imshow('Capturing Images', frame)
    
    # Dừng khi chụp đủ 300 ảnh hoặc nhấn 'q' để dừng
    if count >= 300:
        print("Đã chụp đủ 300 ảnh!")
        break
    if cv2.waitKey(1) & 0xFF == ord('q'):
        print("Chụp ảnh bị dừng bởi người dùng.")
        break

# Giải phóng camera và đóng tất cả cửa sổ
cap.release()
cv2.destroyAllWindows()
