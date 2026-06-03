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
        
        # Cấu hình Session đa đối tượng bằng dict
        self.active_sessions = {}  # Cấu trúc: { plate_text: { "best_conf": float, "best_frame": img, "last_seen_time": float, "box": [] } }
        self.timeout_seconds = 3.0 

    def process_cam_stream(self, cam_id=0, skip_frames=5):
        cap = cv2.VideoCapture(cam_id)
        frame_count = 0

        while True:
            ret, frame = cap.read()
            if not ret: break

            frame = cv2.resize(frame, (800, 600))
            current_time = time.time()

            # Skip frame để tiết kiệm CPU
            current_results = []
            if frame_count % (skip_frames + 1) == 0:
                current_results = self.detector.detect_plate(frame) # Nhận về 1 list các biển số

            plates_seen_this_frame = set()

            # 1. Cập nhật hoặc tạo mới session cho các biển số nhận diện được ở frame này
            if isinstance(current_results, list) and len(current_results) > 0:
                for res in current_results:
                    if res.get('has_plate'):
                        plate_text = res['text']
                        conf = res['conf']
                        plates_seen_this_frame.add(plate_text)

                        # Nếu là biển số mới xuất hiện trước camera
                        if plate_text not in self.active_sessions:
                            self.active_sessions[plate_text] = {
                                "best_conf": conf,
                                "best_frame": frame.copy(),
                                "last_seen_time": current_time,
                                "box": res['box']
                            }
                        else:
                            # Nếu biển đã ở trong vùng quét, cập nhật thời gian thấy và check ảnh nét nhất (conf cao nhất)
                            self.active_sessions[plate_text]["last_seen_time"] = current_time
                            if conf > self.active_sessions[plate_text]["best_conf"]:
                                self.active_sessions[plate_text]["best_conf"] = conf
                                self.active_sessions[plate_text]["best_frame"] = frame.copy()
                                self.active_sessions[plate_text]["box"] = res['box']

            # 2. Kiểm tra Timeout (Quá 3 giây không thấy xe nào đó nữa thì lưu DB và xóa session xe đó)
            sessions_to_remove = []
            for plate_text, session_data in self.active_sessions.items():
                time_diff = current_time - session_data["last_seen_time"]
                if time_diff > self.timeout_seconds:
                    self._save_best_result(plate_text, session_data)
                    sessions_to_remove.append(plate_text)

            for plate_text in sessions_to_remove:
                del self.active_sessions[plate_text]

            # 3. Gom danh sách kết quả hiển thị (để tránh bị nhấp nháy mất khung khi bị skip frame)
            display_results = []
            if isinstance(current_results, list):
                for res in current_results:
                    if res.get('has_plate'):
                        display_results.append(res)

            # Lấy thêm các biển đang nằm trong bộ nhớ đệm chưa bị quá hạn 3 giây để vẽ tiếp
            for plate_text, session_data in self.active_sessions.items():
                if plate_text not in plates_seen_this_frame:
                    if (current_time - session_data["last_seen_time"]) < self.timeout_seconds:
                        display_results.append({
                            "has_plate": True,
                            "text": plate_text,
                            "conf": session_data["best_conf"],
                            "box": session_data["box"]
                        })

            # Vẽ toàn bộ danh sách biển số lên frame hình trực tiếp
            if display_results:
                self._draw(frame, display_results)

            # SỬA DÒNG NÀY: Trả về display_results (chứa list) thay vì current_result dạng đơn lẻ cũ
            yield frame, display_results
            frame_count += 1
            
        cap.release()

    def _save_best_result(self, plate_text, session_data):
        if not self.db_manager: return
        
        try:
            conf = session_data['best_conf']
            best_frame = session_data['best_frame']
            box = session_data['box']
            
            # Copy ảnh gốc lúc nét nhất để vẽ khung riêng cho biển đó trước khi lưu
            frame_to_save = best_frame.copy()
            x1, y1, x2, y2 = map(int, box)
            cv2.rectangle(frame_to_save, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(frame_to_save, f"{plate_text} ({conf})", (x1, y1 - 10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            
            # Save ảnh ra thư mục captured_images
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"anh_tu_camera_{timestamp}_{plate_text}.jpg"
            path = os.path.join(self.save_folder, filename)
            
            cv2.imwrite(path, frame_to_save)
            
            # Lưu vào SQLite DB
            self.db_manager.save_plate(plate_text, path, conf)
            print(f"\n[Camera] Đã lưu DB biển số: {plate_text} | Conf: {conf}")
            
        except Exception as e:
            print(f"Lỗi lưu file ảnh từ camera: {e}")

    # Hàm vẽ toàn bộ danh sách biển số quét được lên màn hình camera
    def _draw(self, frame, results_list):
        if not results_list: return
        
        for result in results_list:
            if not result or 'box' not in result: continue
            box = result['box']
            text = result['text']
            
            # Thêm độ tự tin conf nếu có dữ liệu
            conf_str = f" ({result['conf']})" if 'conf' in result else ""
            
            x1, y1, x2, y2 = map(int, box)
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(frame, f"{text}{conf_str}", (x1, y1 - 10 if y1 - 10 > 10 else y1 + 20), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)