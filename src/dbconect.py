import mysql.connector

# Kết nối đến MySQL
def get_connection():
    return mysql.connector.connect(
        host="localhost", 
        user="root", 
        password="tuananh1582",
        database="users"
    )

# Lấy dữ liệu người dùng từ MySQL
def get_users_data():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, idsv, users_name, user_password, class FROM users")
    users = {}
    for row in cursor.fetchall():
        users[row['idsv']] = {  # Sử dụng 'idsv' làm khóa
            'id': row['id'],
            'password': row['user_password'],  # Cột mật khẩu
            'name': row['users_name'],        # Cột tên
            'class': row['class']             # Cột lớp
        }
    cursor.close()
    conn.close()
    return users

# Điểm danh và lưu vào bảng attendance
def mark_attendance_in_db(idsv, users_name, class_name, ip_address):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO attendance (idsv, users_name, class, ip_address, timestamp) VALUES (%s, %s, %s, %s, NOW())", 
        (idsv, users_name, class_name, ip_address)
    )
    conn.commit()
    cursor.close()
    conn.close()

