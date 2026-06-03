import os
import cv2
import re
from ultralytics import YOLO
from paddleocr import PaddleOCR

class LicensePlateDetector:
    def __init__(self, model_path='core/plate_model.pt'):
        # Tìm mô hình yolo
        if os.path.exists(model_path):
            self.yolo = YOLO(model_path)
        else:
            print("Dùng YOLOv8n mặc định")
            self.yolo = YOLO('yolov8n.pt')

        # Tải paddleocr
        try:
            self.ocr = PaddleOCR(use_angle_cls=True, lang='en', show_log=False)
        except:
            print("Lỗi paddleOCR")

    # Cắt hết kí tự lạ
    def simple_clean_text(self, text):
        text = text.upper()
        clean_text = re.sub(r'[^A-Z0-9\-\.]', '', text)
        return clean_text

    def detect_plate(self, frame):
        # Trả về danh sách rỗng nếu không có frame
        if frame is None: return []

        detected_plates_list = [] # Lưu danh sách tất cả các biển số nhận diện được

        try:
            # Sửa ngưỡng conf từ 0.4 xuống 0.25 để nhận diện nhạy hơn, thêm iou=0.45 để tránh triệt tiêu box gần nhau
            results = self.yolo(frame, conf=0.25, iou=0.45, verbose=False)[0]
            
            h_img, w_img, _ = frame.shape

            # Duyệt qua TOÀN BỘ các box tìm thấy thay vì lọc lấy một cái duy nhất
            for box in results.boxes:
                conf = float(box.conf[0])
                xyxy = box.xyxy[0].tolist()
                x1, y1, x2, y2 = map(int, xyxy)

                # Padding vùng cắt biển số
                y1_pad = max(0, y1 - 5)
                y2_pad = min(h_img, y2 + 5)
                x1_pad = max(0, x1 - 5)
                x2_pad = min(w_img, x2 + 5)
                
                crop_img = frame[y1_pad:y2_pad, x1_pad:x2_pad]
                
                if crop_img.size == 0: 
                    continue

                # Phóng to ảnh crop x2 lần để OCR chính xác hơn
                ocr_img = cv2.resize(crop_img, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
                
                # Dùng ocr để đọc chữ trên từng biển số
                ocr_result = self.ocr.ocr(ocr_img, cls=True)
                
                raw_text = ""
                # Xếp lại các dòng chữ theo thứ tự từ trên xuống dưới
                if ocr_result and ocr_result[0]:
                    sorted_lines = sorted(ocr_result[0], key=lambda x: x[0][0][1])
                    
                    for line in sorted_lines:
                        text_line = line[1][0]
                        raw_text += text_line + " " 

                final_text = self.simple_clean_text(raw_text)

                # Nếu OCR đọc được chữ thì thêm thông tin biển này vào danh sách kết quả
                if final_text.strip():
                    detected_plates_list.append({
                        "has_plate": True,
                        "text": final_text, 
                        "conf": round(conf, 2),
                        "box": [x1, y1, x2, y2],
                        "crop_img": crop_img
                    })

            return detected_plates_list # Trả về mảng chứa tất cả các biển đọc được

        except Exception as e:
            print(f"Lỗi Detect: {e}")
            return []