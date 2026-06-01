import sqlite3
from datetime import datetime

class DatabaseManager:
    def __init__(self, db_file='database/plates.db'):
        #ketnoi db
        self.conn = sqlite3.connect(db_file, check_same_thread=False)
        self.cursor = self.conn.cursor()
        
        self.create_table()

    def create_table(self):
        sql = """
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plate_num TEXT NOT NULL,
            timestamp TEXT,
            image_path TEXT,
            confidence REAL
        )
        """
        self.cursor.execute(sql)
        self.conn.commit()
        print("Tạo bảng thành công")

    def save_plate(self, plate_num, image_path, conf):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        sql = "INSERT INTO history (plate_num, timestamp, image_path, confidence) VALUES (?, ?, ?, ?)"
        
        try:
            self.cursor.execute(sql, (plate_num, now, image_path, conf))
            self.conn.commit()
            print(f"Đã lưu: {plate_num} ({now})")
            return True
        except Exception as e:
            print(f"Lỗi lưu DB: {e}")
            return False

    def get_recent_plates(self, limit=5):
        sql = "SELECT * FROM history ORDER BY id DESC LIMIT ?"
        self.cursor.execute(sql, (limit,))
        return self.cursor.fetchall()

    def close(self):
        self.conn.close()