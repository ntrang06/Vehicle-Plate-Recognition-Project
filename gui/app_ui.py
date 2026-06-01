import customtkinter as ctk
from tkinter import filedialog, messagebox
from PIL import Image
import cv2
import time

from core.detector import LicensePlateDetector
from core.services.image_service import ImageService
from core.services.video_service import VideoService
from core.services.cam_service import CamService

# Cấu hình giao diện chung
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")

class LicensePlateApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Cấu hình Window
        self.title("Ứng dụng nhận diện biển số xe")
        self.geometry("1280x760")
        
        self.color_bg_main = "#101010"
        self.color_bg_side = "#1A1A1A"
        self.color_accent  = "#00ADB5"
        self.color_danger  = "#E74C3C"
        self.color_btn_sec = "#2D2D2D"
        self.color_text    = "#EEEEEE"
        
        # Khởi tạo Services
        self.init_services()

        # Biến trạng thái
        self.current_stream = None
        self.is_running = False
        self.after_id = None
        self.prev_time = 0  # Biến để tính FPS
        
        # Grid Layout
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # Setup UI
        self.setup_sidebar()
        self.setup_main_screen()

    def init_services(self):
        print("Hệ thống của nhận diện đang chạy")
        try:
            self.detector = LicensePlateDetector(model_path='core/plate_model.pt')
            
            #khởi tạo kết nối db
            self.db_manager = None
            try:
                from database.db_manager import DatabaseManager
                self.db_manager = DatabaseManager(db_file='database/plates.db')
                print("Kết nối DB thành công.")
            except Exception as e:
                print(f"Lỗi kết nối DB: {e}")

            #khởi tạo services
            self.image_service = ImageService(self.detector, self.db_manager)
            self.video_service = VideoService(self.detector, self.db_manager)
            self.cam_service = CamService(self.detector, self.db_manager)
            
            print("Các services đã sẵn sàng")
        except Exception as e:
            print(f"Lỗi(app_ui.py): {e}")

    def setup_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=280, corner_radius=0, fg_color=self.color_bg_side)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(10, weight=1) 
        self.sidebar.grid_columnconfigure(0, weight=1)

        # HEADER
        self.lbl_logo = ctk.CTkLabel(self.sidebar, text="ỨNG DỤNG NHẬN DIỆN\nBIỂN SỐ XE", 
                                     font=ctk.CTkFont(family="Roboto", size=24, weight="bold"), 
                                     text_color=self.color_text)
        self.lbl_logo.grid(row=0, column=0, padx=20, pady=(40, 10))
        
        div = ctk.CTkFrame(self.sidebar, height=2, fg_color="#333333")
        div.grid(row=1, column=0, sticky="ew", padx=30, pady=(0, 30))

        # INPUT GROUP
        lbl_input = ctk.CTkLabel(self.sidebar, text="NGUỒN DỮ LIỆU", anchor="w", 
                                 font=ctk.CTkFont(size=12, weight="bold"), text_color="#888888")
        lbl_input.grid(row=2, column=0, sticky="w", padx=30, pady=(0, 10))

        btn_font = ctk.CTkFont(family="Roboto", size=14, weight="bold")

        self.btn_img = ctk.CTkButton(self.sidebar, text="CHỌN ẢNH", height=50, font=btn_font,
                                     fg_color=self.color_btn_sec, hover_color="#3A3A3A",
                                     corner_radius=8, anchor="w", 
                                     command=self.on_click_image)
        self.btn_img.grid(row=3, column=0, padx=20, pady=5, sticky="ew")

        self.btn_video = ctk.CTkButton(self.sidebar, text="CHỌN VIDEO", height=50, font=btn_font,
                                       fg_color=self.color_btn_sec, hover_color="#3A3A3A",
                                       corner_radius=8, anchor="w",
                                       command=self.on_click_video)
        self.btn_video.grid(row=4, column=0, padx=20, pady=5, sticky="ew")

        # CONTROL GROUP
        lbl_control = ctk.CTkLabel(self.sidebar, text="ĐIỀU KHIỂN", anchor="w", 
                                   font=ctk.CTkFont(size=12, weight="bold"), text_color="#888888")
        lbl_control.grid(row=5, column=0, sticky="w", padx=30, pady=(30, 10))

        self.btn_cam = ctk.CTkButton(self.sidebar, text="LIVE CAMERA", height=50, font=btn_font,
                                     fg_color=self.color_accent, hover_color="#008C9E",
                                     text_color="white", corner_radius=8,
                                     command=self.on_click_camera)
        self.btn_cam.grid(row=6, column=0, padx=20, pady=5, sticky="ew")

        self.btn_stop = ctk.CTkButton(self.sidebar, text="DỪNG HỆ THỐNG", height=50, font=btn_font,
                                      fg_color=self.color_danger, hover_color="#C0392B",
                                      state="disabled", corner_radius=8,
                                      command=self.stop_stream)
        self.btn_stop.grid(row=7, column=0, padx=20, pady=5, sticky="ew")

        # RESULT GROUP
        res_frame = ctk.CTkFrame(self.sidebar, width=240, height=140, 
                                 fg_color="black", corner_radius=12, 
                                 border_width=1, border_color="#333333")
        res_frame.grid(row=12, column=0, padx=20, pady=30)
        res_frame.pack_propagate(False)

        ctk.CTkLabel(res_frame, text="BIỂN SỐ NHẬN DIỆN", font=ctk.CTkFont(size=11), text_color="gray").pack(pady=(15,5))
        
        self.lbl_result = ctk.CTkLabel(res_frame, text="---", 
                                       font=ctk.CTkFont(family="Consolas", size=32, weight="bold"), 
                                       text_color=self.color_accent)
        self.lbl_result.pack(expand=True)

    def setup_main_screen(self):
        self.main_frame = ctk.CTkFrame(self, fg_color=self.color_bg_main, corner_radius=0)
        self.main_frame.grid(row=0, column=1, sticky="nsew")
        
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(0, weight=1)

        # Khung chứa video
        self.video_container = ctk.CTkFrame(self.main_frame, fg_color="#000000", 
                                            corner_radius=15, border_width=2, border_color="#333333")
        self.video_container.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        
        self.video_container.grid_rowconfigure(0, weight=1)
        self.video_container.grid_columnconfigure(0, weight=1)

        self.video_display = ctk.CTkLabel(self.video_container, text="SẴN SÀNG HOẠT ĐỘNG\nVui lòng chọn nguồn dữ liệu", 
                                          font=ctk.CTkFont(size=16), text_color="gray")
        self.video_display.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)

    
    # Xử lý sự kiện
    def on_click_image(self):
        self.stop_stream()
        path = filedialog.askopenfilename(filetypes=[("Images", "*.jpg *.png *.jpeg")])
        if path:
            try:
                processed_img, result = self.image_service.process_image(path)
                if processed_img is not None:
                    text = result['text'] if result and result.get('has_plate') else "NO PLATE"
                    self.lbl_result.configure(text=text)
                    self.show_frame(processed_img)
                    print(f" Xử lý ảnh xong: {text}")
            except Exception as e:
                print(f"Lỗi ảnh: {e}")

    def on_click_video(self):
        self.stop_stream()
        path = filedialog.askopenfilename(filetypes=[("Videos", "*.mp4 *.avi *.mkv")])
        if path:
            try:
                self.current_stream = self.video_service.process_video_stream(path, skip_frames=3)
                self.start_loop()
            except Exception as e:
                print(f"Lỗi video: {e}")

    def on_click_camera(self):
        self.stop_stream()
        try:
            self.current_stream = self.cam_service.process_cam_stream(cam_id=0, skip_frames=5)
            self.start_loop()
        except Exception as e:
            print(f"Lỗi Camera: {e}")
            messagebox.showerror("Lỗi", "Không thể mở Camera")

    def start_loop(self):
        self.is_running = True
        self.btn_stop.configure(state="normal", fg_color=self.color_danger)
        
        # Disable các nút input
        self.btn_img.configure(state="disabled")
        self.btn_video.configure(state="disabled")
        self.btn_cam.configure(state="disabled")
        
        # Reset thời gian để tính FPS
        self.prev_time = time.time()
        
        self.update_ui_loop()

    def update_ui_loop(self):
        if not self.is_running or self.current_stream is None:
            return

        try:
            # tính FPS
            curr_time = time.time()
            fps = 1 / (curr_time - self.prev_time) if (curr_time - self.prev_time) > 0 else 0
            self.prev_time = curr_time
            
            # Lấy data từ Generator
            data = next(self.current_stream)
            
            if isinstance(data, tuple):
                frame, result = data
                
                # log ra terminal
                if result and result.get('has_plate'):
                    text = result['text']
                    conf = result['conf']
                    self.lbl_result.configure(text=text)
                    
                    # Log màu xanh rờn cho nó ngầu
                    print(f"\033[92m[FPS: {int(fps)}] DETECTED: {text} | Conf: {conf}\033[0m")
            else:
                frame = data

            # vẽ FPS lên frame
            cv2.putText(frame, f"FPS: {int(fps)}", (20, 40), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

            self.show_frame(frame)
            self.after_id = self.after(30, self.update_ui_loop)

        except StopIteration:
            self.stop_stream()
            messagebox.showinfo("Thông báo", "Đã kết thúc video.")
        except Exception as e:
            print(f"Error Loop: {e}")
            self.stop_stream()

    def stop_stream(self, clear_ui=True):
        self.is_running = False
        self.current_stream = None
        if self.after_id:
            self.after_cancel(self.after_id)
            self.after_id = None
        
        self.btn_stop.configure(state="disabled", fg_color="#555555") 
        self.btn_img.configure(state="normal")
        self.btn_video.configure(state="normal")
        self.btn_cam.configure(state="normal")
        
        if clear_ui:
            self.video_display.configure(image=None, text="ĐÃ DỪNG HỆ THỐNG")
            self.lbl_result.configure(text="---")

    def show_frame(self, cv_img):
        if cv_img is None: return
        
        h_disp = self.video_container.winfo_height()
        w_disp = self.video_container.winfo_width()
        if h_disp < 100: h_disp, w_disp = 600, 800 
        
        h_img, w_img = cv_img.shape[:2]
        ratio = min(w_disp/w_img, h_disp/h_img)
        new_w, new_h = int(w_img * ratio), int(h_img * ratio)
        
        img_rgb = cv2.cvtColor(cv2.resize(cv_img, (new_w, new_h)), cv2.COLOR_BGR2RGB)
        ctk_img = ctk.CTkImage(Image.fromarray(img_rgb), size=(new_w, new_h))
        
        self.video_display.configure(image=ctk_img, text="") 
        self.video_display.image = ctk_img

if __name__ == "__main__":
    app = LicensePlateApp()
    app.mainloop()
