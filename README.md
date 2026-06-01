# Ứng dụng nhận diện biển số xe 

> Sử dụng **YOLOv8n** và **PaddleOCR**, hỗ trợ nhận diện từ Ảnh, Video và Camera trực tiếp.

## Thành Viên Thực Hiện (Project Team)

| STT | Họ và Tên           | Vai trò (Role) |
|-----|---------------------|----------------|
| 1   | **Lê Thành Chỉnh**  | Nhóm trưởng   |
| 2   | **Trần Phát Tài**   | Thành viên    |
| 3   | **Võ Đoàn Duy Quang** | Thành viên    |


##  Tính Năng Nổi Bật

Ứng dụng cung cấp các chế độ xử lý khác nhau tùy theo nguồn dữ liệu:

### 1. Chế độ Ảnh Tĩnh (Image Service)

* **Xử lý tức thì:** Nhận diện và đọc biển số ngay lập tức sau khi chọn ảnh.
* **Tự động lưu:** Vẽ khung, ghi biển số và lưu ngay vào Database.

### 2. Chế độ Video & Camera

**Chọn ảnh tốt nhất:**
* Ứng dụng **KHÔNG** lưu ảnh tràn lan.
* Tự động theo dõi xe từ lúc xuất hiện cho đến khi đi khuất.
* So sánh liên tục và chỉ lưu **duy nhất 1 tấm ảnh rõ nét nhất** của phiên đó.


**Chống trùng lặp:**
* Ngăn chặn việc ghi trùng lặp dữ liệu khi xe dừng lâu một chỗ.
* Chỉ ghi nhận xe đã rời đi hoặc sau một khoảng thời gian chờ.


* **Live Cam:** Hỗ trợ Webcam hoặc IP Camera thời gian thực.

### 3. Quản Lý Dữ Liệu

* Tự động lưu lịch sử ra/vào vào database, sử dụng **SQLite**.
* Lưu đường dẫn ảnh bằng chứng kèm thông số độ tin cậy (`conf`).

---

## Hướng Dẫn Cài Đặt (Nhớ clone dự án về trước)

Hãy thực hiện tuần tự theo các bước sau để tránh lỗi thư viện:

### Bước 1: Chuẩn bị mã nguồn

Tải code về máy và mở Terminal tại thư mục gốc của dự án.

### Bước 2: Tạo môi trường ảo (Khuyên dùng)

* **Windows:** `python -m venv venv` sau đó `.\venv\Scripts\activate`

### Bước 3: Cài đặt PyTorch (Bắt buộc chạy trước)

Do dự án nhóm mình dùng phiên bản CUDA 11.8, bạn **CẦN** chạy lệnh này trước khi cài các thư viện khác:

```bash
pip install torch==2.1.2+cu118 torchvision==0.16.2+cu118 torchaudio==2.1.2+cu118 --index-url https://download.pytorch.org/whl/cu118

```

### Bước 4: Cài đặt các thư viện còn lại

Sau khi cài xong PyTorch, chạy lệnh sau:

```bash
pip install -r requirements.txt

```

*(Lưu ý thêm: Nếu bạn dùng GPU cho OCR, hãy cài thêm `paddlepaddle-gpu` nha)*

---

## Hướng Dẫn Sử Dụng

### 1. Chạy Giao Diện Chính (GUI)

Để mở phần mềm quản lý:

```bash
python main.py

```

## Cấu Trúc Thư Mục

```text
PROJECT_ROOT/
├── core/
│   ├── detector.py          # Class nhận diện (YOLO + OCR)
│   ├── plate_model.pt       # File Model YOLOv8n
│   └── services/            
│       ├── image_service.py # Xử lý ảnh 
│       ├── video_service.py # Xử lý Video 
│       └── cam_service.py   # Xử lý Camera 
├── database/
│   ├── db_manager.py        # Quản lý kết nối SQLite
│   └── plates.db            # File dữ liệu
├── gui/
│   ├── app_ui.py            # Mã nguồn giao diện
├── captured_images/         # Thư mục chứa ảnh chụp tự động
├── requirements.txt         # Danh sách thư viện
└── README.md                # Tài liệu hướng dẫn

---
