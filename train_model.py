from ultralytics import YOLO

def main():
    print("Bắt đầu quá trình huấn luyện mô hình YOLOv8...")

    # 1. Khởi tạo mô hình (Dùng bản nano cho nhẹ và nhanh)
    # Lần đầu chạy nó sẽ tự tải file yolov8n.pt (tầm 6MB) về máy
    model = YOLO('yolov8n.pt') 

    # 2. Cấu hình thông số huấn luyện
    results = model.train(
        data='dataset/data.yaml',  # Đường dẫn tới file yaml cấu hình dữ liệu
        epochs=50,                 # Số vòng lặp học (Để 50 là vừa đủ cho biển số)
        imgsz=640,                 # Kích thước ảnh đầu vào
        batch=8,                   # Số lượng ảnh xử lý 1 lần (để 8 an toàn cho VRAM 4GB)
        device=0,                  # Chỉ định GPU số 0 để train
        workers=2,                 # Số luồng CPU phụ giúp đẩy data (Windows để 2 hoặc 4)
        name='nhan_dien_bien_so',  # Tên thư mục lưu kết quả
        plots=True                 # Tự động vẽ biểu đồ sau khi train xong
    )

    print("Huấn luyện hoàn tất!")

if __name__ == '__main__':
    # BẮT BUỘC phải có dòng này trên Windows để tránh lỗi RuntimeError: freeze_support()
    main()