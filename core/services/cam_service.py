import cv2
import os
import time
from datetime import datetime

class CamService:
    def __init__(self, detector, db_manager=None):
        self.detector = detector
        self.db_manager = db_manager
        
        self.save_folder = "captured_images"
        os.makedirs(self.save_folder, exist_ok=True)
        
        # Cấu hình Session
        self.session_active = False
        self.best_result = None
        self.best_frame = None
        self.last_seen_time = 0
        self.timeout_seconds = 3.0 

    def process_cam_stream(self, cam_id=0, skip_frames=5):
        cap = cv2.VideoCapture(cam_id)
        frame_count = 0

        while True:
            ret, frame = cap.read()
            if not ret: break

            frame = cv2.resize(frame, (800, 600))
            current_time = time.time()

            #skip frame để tiết kiệm cpu
            current_result = None
            if frame_count % (skip_frames + 1) == 0:
                current_result = self.detector.detect_plate(frame)

            #tìm frame có độ tin cậy cao nhất để lưu
            if current_result and current_result['has_plate']:
                self.last_seen_time = current_time
                self.session_active = True
                
                if self.best_result is None or current_result['conf'] > self.best_result['conf']:
                    self.best_result = current_result
                    self.best_frame = frame.copy()
            
            #nếu vượt quá ngưỡng không thấy biển số thì lưu kết quả và reset
            if self.session_active:
                time_diff = current_time - self.last_seen_time
                if time_diff > self.timeout_seconds:
                    self._save_best_result()
                    self.session_active = False
                    self.best_result = None
                    self.best_frame = None

            #vẽ len frame để hiển thị
            draw_target = current_result if (current_result and current_result['has_plate']) else self.best_result
            
            if draw_target and draw_target['has_plate']:
                 if (current_time - self.last_seen_time) < self.timeout_seconds:
                    self._draw(frame, draw_target)

            yield frame, current_result
            frame_count += 1
            
        cap.release()

    def _save_best_result(self):
        if not self.db_manager or not self.best_result: return
        
        try:
            plate = self.best_result['text']
            conf = self.best_result['conf']
            
            #copy ảnh gốc để vẽ 
            frame_to_save = self.best_frame.copy()
            self._draw(frame_to_save, self.best_result)
            
            #save ra folder
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"anh_tu_camera_{timestamp}_{plate}.jpg"
            path = os.path.join(self.save_folder, filename)
            
            cv2.imwrite(path, frame_to_save)
            
            #lưu vào db
            self.db_manager.save_plate(plate, path, conf)
            print(f"\nĐã lưu ảnh (có khung): {plate}")
            
        except Exception as e:
            print(f"Lỗi: {e}")

    def _draw(self, frame, result):
        box = result['box']
        text = result['text']
        x1, y1, x2, y2 = map(int, box)
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(frame, text, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
