import os
import cv2
import re
from ultralytics import YOLO
from paddleocr import PaddleOCR

class LicensePlateDetector:
    def __init__(self, model_path='core/plate_model.pt'):
        #tìm mô hình yolo
        if os.path.exists(model_path):
            self.yolo = YOLO(model_path)
        else:
            print("Dùng YOLOv8n mặc định")
            self.yolo = YOLO('yolov8n.pt')

        #tải paddleocr
        try:
            self.ocr = PaddleOCR(use_angle_cls=True, lang='en', show_log=False)
        except:
            print("Lỗi paddleOCR")

    #cắt hết kí tự lạ
    def simple_clean_text(self, text):
        text = text.upper()
        clean_text = re.sub(r'[^A-Z0-9\-\.]', '', text)
        return clean_text

    def detect_plate(self, frame):
        if frame is None: return self._empty_result()

        try:
            results = self.yolo(frame, conf=0.4, verbose=False)[0]
            
            best_box = None
            max_conf = 0.0

            #tìm box chứa biển số có độ tin cậy cao nhất
            for box in results.boxes:
                conf = float(box.conf[0])
                if conf > max_conf:
                    max_conf = conf
                    best_box = box.xyxy[0].tolist()

            if best_box is None:
                return self._empty_result()

            #crop mỗi ảnh biển số ra ảnh nhỏ hơn
            x1, y1, x2, y2 = map(int, best_box)
            h_img, w_img, _ = frame.shape
            
            #padding
            crop_img = frame[max(0, y1-5):min(h_img, y2+5), max(0, x1-5):min(w_img, x2+5)]

            #phóng to ảnh crop x2 lần
            ocr_img = cv2.resize(crop_img, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
            
            #dùng ocr để đọc biển số
            ocr_result = self.ocr.ocr(ocr_img, cls=True)
            
            raw_text = ""
            #xep lại các dòng chữ theo thứ tự từ trên xuống dưới
            if ocr_result and ocr_result[0]:
                sorted_lines = sorted(ocr_result[0], key=lambda x: x[0][0][1])
                
                for line in sorted_lines:
                    text_line = line[1][0]
                    raw_text += text_line + " " 

            final_text = self.simple_clean_text(raw_text)

            return {
                "has_plate": True,
                "text": final_text, 
                "conf": round(max_conf, 2),
                "box": [x1, y1, x2, y2],
                "crop_img": crop_img
            }

        except Exception as e:
            print(f"Lỗi Detect: {e}")
            return self._empty_result()

    def _empty_result(self):
        return {"has_plate": False, "text": "", "box": [], "conf": 0.0, "crop_img": None}