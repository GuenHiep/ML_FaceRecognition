import cv2
import numpy as np
import os

# Định nghĩa cascade classifier
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

# Dữ liệu để huấn luyện
faces = []
labels = []
label_dict = {}
current_label = 0

# Lấy tất cả ảnh khuôn mặt trong dataset
for user_name in os.listdir('dataset'):
    user_folder = os.path.join('dataset', user_name)
    if os.path.isdir(user_folder):
        label_dict[current_label] = user_name
        for filename in os.listdir(user_folder):
            if filename.endswith('.jpg'):
                img_path = os.path.join(user_folder, filename)
                img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
                faces.append(img)
                labels.append(current_label)
        current_label += 1

# Huấn luyện mô hình LBPH
recognizer = cv2.face.LBPHFaceRecognizer_create()
recognizer.train(faces, np.array(labels))

# Lưu mô hình đã huấn luyện
recognizer.save('training/recognizer.yml')
print("Mô hình đã được huấn luyện và lưu.")
