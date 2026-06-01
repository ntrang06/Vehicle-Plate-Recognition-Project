import cv2
import os
from datetime import datetime

class VideoService:
    def __init__(self, detector, db_manager=None):
        self.detector = detector
        self.db_manager = db_manager
        
        self.save_folder = "captured_images"
        os.makedirs(self.save_folder, exist_ok=True)
        
        #biến session
        self.session_active = False
        self.best_result = None
        self.best_frame = None
        self.missing_count = 0      
        self.timeout_frames = 30   

    def process_video_stream(self, video_path, skip_frames=3):
        if not os.path.exists(video_path):
            print(f"Lỗi: Không tìm thấy video tại {video_path}")
            return

        cap = cv2.VideoCapture(video_path)
        frame_count = 0

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret: break

            h, w = frame.shape[:2]
            if w > 800:
                frame = cv2.resize(frame, (800, int(h * 800/w)))

            #skip frame để tiết kiệm cpu
            current_result = None
            if frame_count % (skip_frames + 1) == 0:
                current_result = self.detector.detect_plate(frame)
            
            #tìm frame có độ tin cậy cao nhất để lưu
            if current_result and current_result['has_plate']:
                self.missing_count = 0
                self.session_active = True
                
                if self.best_result is None or current_result['conf'] > self.best_result['conf']:
                    self.best_result = current_result
                    self.best_frame = frame.copy()

            elif self.session_active:
                self.missing_count += 1

            #nếu vượt quá ngưỡng không thấy biển số thì lưu kết quả và reset
            if self.session_active and self.missing_count > self.timeout_frames:
                self._save_session_to_db()
                self.session_active = False
                self.best_result = None
                self.best_frame = None
                self.missing_count = 0

            #vẽ len frame để hiển thị
            display_result = current_result if (current_result and current_result['has_plate']) else self.best_result
            
            if display_result and display_result['has_plate']:
                 if self.missing_count < self.timeout_frames:
                    self._draw_on_frame(frame, display_result)

            yield frame, display_result
            frame_count += 1

        if self.session_active and self.best_result:
            self._save_session_to_db()

        cap.release()

    def _save_session_to_db(self):
        if not self.db_manager or not self.best_result: return
        
        try:
            plate = self.best_result['text']
            conf = self.best_result['conf']
            
            #copy ảnh gốc để vẽ khung và lưu
            frame_to_save = self.best_frame.copy()
            self._draw_on_frame(frame_to_save, self.best_result)
            
            #save về folder captued_images
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"anh_tu_video_{timestamp}_{plate}.jpg"
            path = os.path.join(self.save_folder, filename)
            
            cv2.imwrite(path, frame_to_save)
            
            #lưu vào db
            self.db_manager.save_plate(plate, path, conf)
            print(f"\nĐã lưu ảnh: {plate}")
            
        except Exception as e:
            print(f"Lỗi: {e}")

    #hàm vẽ khung và text lên frame
    def _draw_on_frame(self, frame, result):
        if not result or 'box' not in result: return
        box = result['box']
        text = result['text']
        conf = result['conf']
        x1, y1, x2, y2 = map(int, box)
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(frame, f"{text} ({conf})", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
