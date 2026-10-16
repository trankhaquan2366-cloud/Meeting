import customtkinter as ctk
import tkinter as tk
from PIL import Image, ImageTk
import os

# Set Appearance
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("CineAI Pro - Hệ Thống Quản Lý Rạp Phim AI")
        self.geometry("1100x700")
        self.minsize(900, 600)
        
        # Container to hold frames
        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.pack(fill="both", expand=True)
        
        # Grid layout for container
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)
        
        # Initialize Frames
        self.frames = {}
        
        for F in (LoginFrame, AdminFrame):
            page_name = F.__name__
            frame = F(parent=self.container, controller=self)
            self.frames[page_name] = frame
            # Put all frames in the same location
            frame.grid(row=0, column=0, sticky="nsew")
            
        self.show_frame("LoginFrame")
        
    def show_frame(self, page_name):
        frame = self.frames[page_name]
        frame.tkraise()
        if hasattr(frame, 'on_show'):
            frame.on_show()

class LoginFrame(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="#0a0c10")
        self.controller = controller
        
        # Center Box
        self.login_box = ctk.CTkFrame(self, width=400, height=500, corner_radius=20, fg_color="#1c222e")
        self.login_box.place(relx=0.5, rely=0.5, anchor="center")
        
        # Logo / Title
        self.lbl_logo = ctk.CTkLabel(self.login_box, text="CineAI Pro", font=ctk.CTkFont(family="Helvetica", size=32, weight="bold"), text_color="#00e5ff")
        self.lbl_logo.pack(pady=(40, 5))
        self.lbl_sub = ctk.CTkLabel(self.login_box, text="AI-Powered Cinema Management", font=ctk.CTkFont(size=14), text_color="gray")
        self.lbl_sub.pack(pady=(0, 30))
        
        # Inputs
        self.entry_username = ctk.CTkEntry(self.login_box, placeholder_text="Tên đăng nhập / Email", width=300, height=45, corner_radius=10)
        self.entry_username.pack(pady=10)
        
        self.entry_password = ctk.CTkEntry(self.login_box, placeholder_text="Mật khẩu", show="*", width=300, height=45, corner_radius=10)
        self.entry_password.pack(pady=10)
        
        # AI Status
        self.lbl_ai_status = ctk.CTkLabel(self.login_box, text="🛡️ AI Threat Detection: An toàn", text_color="#00ff88", font=ctk.CTkFont(size=12))
        self.lbl_ai_status.pack(pady=10)
        
        # Login Button
        self.btn_login = ctk.CTkButton(self.login_box, text="ĐĂNG NHẬP", width=300, height=45, corner_radius=10, 
                                       font=ctk.CTkFont(weight="bold"), fg_color="#00e5ff", hover_color="#00b3cc", text_color="black",
                                       command=self.login_event)
        self.btn_login.pack(pady=15)
        
        # Demo Logins
        self.lbl_demo = ctk.CTkLabel(self.login_box, text="Hoặc đăng nhập nhanh bằng AI:", text_color="gray", font=ctk.CTkFont(size=12))
        self.lbl_demo.pack(pady=(15, 5))
        
        self.demo_frame = ctk.CTkFrame(self.login_box, fg_color="transparent")
        self.demo_frame.pack(pady=5)
        
        self.btn_admin = ctk.CTkButton(self.demo_frame, text="Super Admin", width=90, height=30, fg_color="#2b2b2b", hover_color="#3b3b3b", command=self.login_event)
        self.btn_admin.grid(row=0, column=0, padx=5)
        
        self.btn_manager = ctk.CTkButton(self.demo_frame, text="Manager", width=90, height=30, fg_color="#2b2b2b", hover_color="#3b3b3b", command=self.login_event)
        self.btn_manager.grid(row=0, column=1, padx=5)
        
        self.btn_ai = ctk.CTkButton(self.demo_frame, text="AI Lead", width=90, height=30, fg_color="#2b2b2b", hover_color="#3b3b3b", command=self.login_event)
        self.btn_ai.grid(row=0, column=2, padx=5)

    def login_event(self):
        # Trigger navigation to Admin
        self.controller.show_frame("AdminFrame")


class AdminFrame(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="#0a0c10")
        self.controller = controller
        
        # Grid layout for Admin
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        
        # --- Sidebar ---
        self.sidebar_frame = ctk.CTkFrame(self, width=220, corner_radius=0, fg_color="#12161f")
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(6, weight=1) # Push logout to bottom
        
        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="CineAI Pro", font=ctk.CTkFont(size=24, weight="bold"), text_color="#00e5ff")
        self.logo_label.grid(row=0, column=0, padx=20, pady=(30, 30))
        
        self.btn_dashboard = ctk.CTkButton(self.sidebar_frame, text="📊 Tổng quan AI", fg_color="transparent", text_color="#fff", hover_color="#1c222e", anchor="w")
        self.btn_dashboard.grid(row=1, column=0, padx=10, pady=5, sticky="ew")
        
        self.btn_schedule = ctk.CTkButton(self.sidebar_frame, text="📅 Xếp lịch AI", fg_color="transparent", text_color="gray", hover_color="#1c222e", anchor="w")
        self.btn_schedule.grid(row=2, column=0, padx=10, pady=5, sticky="ew")
        
        self.btn_seatmap = ctk.CTkButton(self.sidebar_frame, text="💺 Sơ đồ & Giá động", fg_color="transparent", text_color="gray", hover_color="#1c222e", anchor="w")
        self.btn_seatmap.grid(row=3, column=0, padx=10, pady=5, sticky="ew")
        
        self.btn_logout = ctk.CTkButton(self.sidebar_frame, text="Đăng xuất", fg_color="#ff3366", hover_color="#cc0033", command=self.logout_event)
        self.btn_logout.grid(row=7, column=0, padx=20, pady=20, sticky="s")
        
        # --- Main Content ---
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.main_frame.grid_columnconfigure((0, 1, 2), weight=1)
        self.main_frame.grid_rowconfigure(2, weight=1)
        
        # Top Bar
        self.header_label = ctk.CTkLabel(self.main_frame, text="Tổng quan Điều hành", font=ctk.CTkFont(size=28, weight="bold"))
        self.header_label.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 20))
        
        self.lbl_status = ctk.CTkLabel(self.main_frame, text="CineBrain v4.8: ONLINE", text_color="#00ff88", font=ctk.CTkFont(weight="bold"))
        self.lbl_status.grid(row=0, column=2, sticky="e", pady=(0, 20))
        
        # KPI Cards (Row 1)
        self.card1 = self.create_kpi_card(self.main_frame, "Doanh thu hôm nay", "$124,500", "+14.5% (AI)", "#00e5ff", 0)
        self.card2 = self.create_kpi_card(self.main_frame, "Lấp đầy phòng", "86%", "+5% nhờ AI", "#9d00ff", 1)
        self.card3 = self.create_kpi_card(self.main_frame, "Vé bán ra", "8,432", "+22%", "#ffb300", 2)
        
        # Dashboard Content Area (Row 2)
        self.content_area = ctk.CTkFrame(self.main_frame, fg_color="#1c222e", corner_radius=15)
        self.content_area.grid(row=2, column=0, columnspan=3, sticky="nsew", pady=20)
        
        self.content_lbl = ctk.CTkLabel(self.content_area, text="[Biểu đồ Phân tích Doanh thu Thực tế vs AI Dự báo]", font=ctk.CTkFont(size=16), text_color="gray")
        self.content_lbl.pack(expand=True)
        
        # AI Copilot Assistant (Row 3 - Footer/Docked)
        self.copilot_frame = ctk.CTkFrame(self.main_frame, height=60, corner_radius=15, fg_color="#12161f")
        self.copilot_frame.grid(row=3, column=0, columnspan=3, sticky="ew")
        
        self.copilot_entry = ctk.CTkEntry(self.copilot_frame, placeholder_text="Hỏi CineBrain AI (vd: Dự báo bắp nước cuối tuần)...", border_width=0, fg_color="transparent")
        self.copilot_entry.pack(side="left", fill="x", expand=True, padx=20, pady=10)
        
        self.copilot_btn = ctk.CTkButton(self.copilot_frame, text="Gửi AI", width=80, fg_color="#9d00ff", hover_color="#7a00cc")
        self.copilot_btn.pack(side="right", padx=10, pady=10)

    def create_kpi_card(self, parent, title, value, trend, color, col):
        card = ctk.CTkFrame(parent, height=120, corner_radius=15, fg_color="#1c222e")
        card.grid(row=1, column=col, sticky="nsew", padx=10)
        card.grid_propagate(False)
        
        lbl_title = ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=14), text_color="gray")
        lbl_title.pack(anchor="w", padx=20, pady=(20, 5))
        
        lbl_value = ctk.CTkLabel(card, text=value, font=ctk.CTkFont(size=28, weight="bold"), text_color="white")
        lbl_value.pack(anchor="w", padx=20)
        
        lbl_trend = ctk.CTkLabel(card, text=trend, font=ctk.CTkFont(size=12), text_color=color)
        lbl_trend.pack(anchor="w", padx=20, pady=(0, 20))
        return card

    def logout_event(self):
        self.controller.show_frame("LoginFrame")

if __name__ == "__main__":
    app = App()
    app.mainloop()
