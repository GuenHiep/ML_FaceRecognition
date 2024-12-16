import cv2
import numpy as np
import os
import pickle
from dbconect import get_connection

# Kết nối đến MySQL
# def get_connection():
#     return mysql.connector.connect(
#         host="localhost",
#         user="root",
#         password="tuananh1582",
#         database="face_re"
#     )

# Lấy dữ liệu sinh viên từ bảng `student`
def get_students_data():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, idsv FROM student")  # Lấy id và idsv từ bảng student
    students = {}
    for row in cursor.fetchall():
        students[row['idsv']] = row['id']
    cursor.close()
    conn.close()
    return students

face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

# Dữ liệu để huấn luyện
faces = []
labels = []
label_dict = {}
current_label = 0

students_data = get_students_data()

for idsv, student_id in students_data.items():
    user_folder = os.path.join('dataset', str(idsv))
    if os.path.isdir(user_folder):
        print(f"Processing student {idsv}...")
        label_dict[current_label] = idsv
        for filename in os.listdir(user_folder):
            if filename.endswith('.jpg'):
                img_path = os.path.join(user_folder, filename)
                try:
                    img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
                    if img is not None:
                        faces.append(img)
                        labels.append(current_label)
                    else:
                        print(f"Warning: Unable to load image {img_path}")
                except Exception as e:
                    print(f"Error processing {img_path}: {e}")
        current_label += 1
    else:
        print(f"Folder for student {idsv} does not exist!")

if len(faces) > 0:
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.train(faces, np.array(labels))

    output_path = 'training/recognizer.yml'
    recognizer.save(output_path)

    with open('training/label_dict.pkl', 'wb') as f:
        pickle.dump(label_dict, f)

    print(f"Model was saved")
    print(f"Label dictionary saved to training")
else:
    print("No faces found for training. Please check the dataset.")
