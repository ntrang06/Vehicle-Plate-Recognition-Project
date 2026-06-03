import cv2
import os
from datetime import datetime

class VideoService:
    def __init__(self, detector, db_manager=None):
        self.detector = detector
        self.db_manager = db_manager
        
        self.save_folder = "captured_images"
        os.makedirs(self.save_folder, exist_ok=True)
        
        # Biến session để quản lý tracking đa đối tượng (Dùng dict với key là biển số xe)
        self.active_sessions = {}  # Cấu trúc: { plate_text: { "best_conf": float, "best_frame": img, "missing_count": int, "box": [] } }
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

            current_results = []
            # Skip frame để tiết kiệm CPU
            if frame_count % (skip_frames + 1) == 0:
                current_results = self.detector.detect_plate(frame)  # Trả về một list các dict biển số
            
            plates_seen_this_frame = set()

            # 1. Cập nhật trạng thái session cho các biển số quét được ở frame hiện tại
            if isinstance(current_results, list) and len(current_results) > 0:
                for res in current_results:
                    if res.get('has_plate'):
                        plate_text = res['text']
                        conf = res['conf']
                        plates_seen_this_frame.add(plate_text)

                        # Nếu là biển số mới xuất hiện, tạo session mới cho biển đó
                        if plate_text not in self.active_sessions:
                            self.active_sessions[plate_text] = {
                                "best_conf": conf,
                                "best_frame": frame.copy(),
                                "missing_count": 0,
                                "box": res['box']
                            }
                        else:
                            # Nếu biển đã có session, kiểm tra xem độ tự tin frame này tốt hơn không để cập nhật frame đẹp nhất
                            self.active_sessions[plate_text]["missing_count"] = 0
                            if conf > self.active_sessions[plate_text]["best_conf"]:
                                self.active_sessions[plate_text]["best_conf"] = conf
                                self.active_sessions[plate_text]["best_frame"] = frame.copy()
                                self.active_sessions[plate_text]["box"] = res['box']

            # 2. Xử lý tăng missing_count đối với các biển nằm trong session nhưng frame này không nhìn thấy
            sessions_to_remove = []
            for plate_text, session_data in self.active_sessions.items():
                if plate_text not in plates_seen_this_frame:
                    session_data["missing_count"] += 1
                
                # Nếu vượt quá ngưỡng không thấy biển số này nữa, tiến hành lưu kết quả đẹp nhất vào DB và đánh dấu xoá session
                if session_data["missing_count"] > self.timeout_frames:
                    self._save_session_to_db(plate_text, session_data)
                    sessions_to_remove.append(plate_text)

            # Xoá các session đã hết thời gian (timeout)
            for plate_text in sessions_to_remove:
                del self.active_sessions[plate_text]

            # 3. Gom danh sách kết quả hiển thị (Ưu tiên kết quả frame hiện tại, nếu trùng hoặc mất tạm thời thì dùng tạm kết quả cũ trong session)
            display_results = []
            
            # Đưa các biển tìm thấy ở frame này vào danh sách hiển thị trước
            if isinstance(current_results, list):
                for res in current_results:
                    if res.get('has_plate'):
                        display_results.append(res)

            # Nếu frame này bị skip hoặc không nhận diện được, lấy tạm thông tin từ các session đang active để vẽ (tránh bị chớp nháy khung hình)
            for plate_text, session_data in self.active_sessions.items():
                if plate_text not in plates_seen_this_frame and session_data["missing_count"] < self.timeout_frames:
                    display_results.append({
                        "has_plate": True,
                        "text": plate_text,
                        "conf": session_data["best_conf"],
                        "box": session_data["box"]
                    })

            # Vẽ TOÀN BỘ các biển số hợp lệ lên khung hình hiện tại
            if display_results:
                self._draw_on_frame(frame, display_results)

            # Trả dữ liệu về cho app_ui.py hiển thị (Luôn trả về danh sách kết quả)
            yield frame, display_results
            frame_count += 1

        # Lưu nốt các session còn sót lại khi kết thúc video hoàn toàn
        for plate_text, session_data in self.active_sessions.items():
            self._save_session_to_db(plate_text, session_data)
        self.active_sessions.clear()

        cap.release()

    def _save_session_to_db(self, plate_text, session_data):
        if not self.db_manager: return
        
        try:
            conf = session_data['best_conf']
            best_frame = session_data['best_frame']
            box = session_data['box']
            
            # Copy ảnh gốc đẹp nhất để vẽ riêng khung của biển số đó trước khi lưu
            frame_to_save = best_frame.copy()
            x1, y1, x2, y2 = map(int, box)
            cv2.rectangle(frame_to_save, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(frame_to_save, f"{plate_text} ({conf})", (x1, y1 - 10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            # Lưu ảnh ra thư mục captured_images
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"anh_tu_video_{timestamp}_{plate_text}.jpg"
            path = os.path.join(self.save_folder, filename)
            
            cv2.imwrite(path, frame_to_save)
            
            # Lưu thông tin vào SQLite DB
            self.db_manager.save_plate(plate_text, path, conf)
            print(f"\n[Video] Đã lưu DB biển số: {plate_text} với độ tin cậy: {conf}")
            
        except Exception as e:
            print(f"Lỗi khi lưu session DB: {e}")

    # Hàm vẽ TOÀN BỘ các khung và text của danh sách biển lên frame
    def _draw_on_frame(self, frame, results_list):
        if not results_list: return
        
        for result in results_list:
            if not result or 'box' not in result: continue
            box = result['box']
            text = result['text']
            conf = result['conf']
            
            x1, y1, x2, y2 = map(int, box)
            # Vẽ hình chữ nhật xanh
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            # Viết chữ biển số
            cv2.putText(frame, f"{text} ({conf})", (x1, y1 - 10 if y1 - 10 > 10 else y1 + 20), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)