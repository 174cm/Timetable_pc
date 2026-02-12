import customtkinter as ctk
import os
import time
import threading
import sys
import winreg
from datetime import datetime
from tkinter import messagebox
from PIL import Image, ImageDraw
import pystray

# 윈도우 11 테마 설정
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class ModernShutdownApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # 기본 설정
        self.title("Auto Shutdown")
        self.geometry("400(650")
        self.configure(fg_color="#1a1a1a")

        # --- 아이콘 설정 (아이콘 이름: iconimage.ico) ---
        try:
            if hasattr(sys, '_MEIPASS'):
                # PyInstaller로 빌드된 환경에서의 경로
                icon_path = os.path.join(sys._MEIPASS, "iconimage.ico")
            else:
                # 로컬 개발 환경에서의 경로
                icon_path = "iconimage.ico"
            self.iconbitmap(icon_path)
        except Exception as e:
            print(f"아이콘 로드 실패: {e}")

        # 레지스트리 설정 (자동 실행용)
        self.reg_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        self.app_name = "AutoShutdownApp"

        # 제어 변수
        self.stop_event = threading.Event()
        self.stop_event.set()

        self.protocol('WM_DELETE_WINDOW', self.hide_to_tray)

        # --- UI 구성 ---
        self.label = ctk.CTkLabel(self, text="시스템 종료 예약", font=ctk.CTkFont(size=22, weight="bold"))
        self.label.pack(pady=(30, 20))

        self.input_frame = ctk.CTkFrame(self, fg_color="#2b2b2b", corner_radius=15)
        self.input_frame.pack(pady=10, padx=30, fill="both")

        ctk.CTkLabel(self.input_frame, text="남은 시간 (분 단위)").pack(pady=(15, 5))
        self.timer_entry = ctk.CTkEntry(self.input_frame, placeholder_text="예: 30", width=200)
        self.timer_entry.pack(pady=5)

        ctk.CTkLabel(self.input_frame, text="정해진 시각 (HH:MM)").pack(pady=(15, 5))
        self.time_entry = ctk.CTkEntry(self.input_frame, placeholder_text="예: 02:00", width=200)
        self.time_entry.pack(pady=5)

        self.repeat_var = ctk.BooleanVar(value=False)
        self.repeat_switch = ctk.CTkSwitch(self.input_frame, text="매일 반복", variable=self.repeat_var)
        self.repeat_switch.pack(pady=(10, 10))

        # 자동 실행 스위치
        self.autostart_var = ctk.BooleanVar(value=self.check_autostart_registry())
        self.autostart_switch = ctk.CTkSwitch(
            self.input_frame,
            text="부팅 시 자동 실행",
            variable=self.autostart_var,
            command=self.toggle_autostart
        )
        self.autostart_switch.pack(pady=(0, 20))

        # 버튼 영역
        self.start_button = ctk.CTkButton(self, text="예약 시작", command=self.start_thread,
                                          fg_color="#0067c0", hover_color="#005aab", font=ctk.CTkFont(weight="bold"))
        self.start_button.pack(pady=(20, 10), padx=30, fill="x")

        self.cancel_button = ctk.CTkButton(self, text="예약 취소", command=self.cancel_shutdown,
                                           fg_color="transparent", border_width=1, border_color="#f44336", text_color="#f44336")
        self.cancel_button.pack(pady=10, padx=30, fill="x")

        self.status_label = ctk.CTkLabel(self, text="대기 중", font=ctk.CTkFont(size=12), text_color="gray")
        self.status_label.pack(side="bottom", pady=20)

        self.create_tray_icon()

    def check_autostart_registry(self):
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.reg_path, 0, winreg.KEY_READ)
            winreg.QueryValueEx(key, self.app_name)
            winreg.CloseKey(key)
            return True
        except WindowsError:
            return False

    def toggle_autostart(self):
        if self.autostart_var.get():
            script_path = os.path.realpath(sys.argv[0])
            if script_path.endswith(".py"):
                cmd = f'"{sys.executable.replace("python.exe", "pythonw.exe")}" "{script_path}"'
            else:
                cmd = f'"{script_path}"'
            try:
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.reg_path, 0, winreg.KEY_WRITE)
                winreg.SetValueEx(key, self.app_name, 0, winreg.REG_SZ, cmd)
                winreg.CloseKey(key)
                self.status_label.configure(text="자동 실행 등록됨", text_color="#4CAF50")
            except Exception as e:
                messagebox.showerror("오류", f"등록 실패: {e}")
        else:
            try:
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.reg_path, 0, winreg.KEY_WRITE)
                winreg.DeleteValue(key, self.app_name)
                winreg.CloseKey(key)
                self.status_label.configure(text="자동 실행 해제됨", text_color="#f44336")
            except WindowsError:
                pass

    def create_tray_icon(self):
        try:
            if hasattr(sys, '_MEIPASS'):
                icon_path = os.path.join(sys._MEIPASS, "iconimage.ico")
            else:
                icon_path = "iconimage.ico"
            icon_image = Image.open(icon_path)
        except:
            # 이미지 로드 실패 시 대체 로고
            icon_image = Image.new('RGB', (64, 64), color="#1a1a1a")

        menu = (pystray.MenuItem('열기', self.show_window, default=True), pystray.MenuItem('종료', self.quit_app))
        self.tray_icon = pystray.Icon("AutoShutdown", icon_image, "Auto Shutdown", menu)
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def hide_to_tray(self): self.withdraw()
    def show_window(self): self.deiconify(); self.focus_force()
    def quit_app(self): self.stop_event.set(); self.tray_icon.stop(); self.destroy(); sys.exit()

    def start_thread(self):
        self.stop_event.clear()
        threading.Thread(target=self.run_logic, daemon=True).start()

    def run_logic(self):
        timer_val = self.timer_entry.get().strip()
        time_val = self.time_entry.get().strip()
        try:
            if timer_val:
                target_seconds = int(timer_val) * 60
                self.status_label.configure(text=f"{timer_val}분 뒤 종료 예정", text_color="#0067c0")
                if self.wait_and_check(target_seconds): return
                self.execute_shutdown()
            elif time_val:
                self.status_label.configure(text=f"{time_val}에 종료 예정", text_color="#0067c0")
                while not self.stop_event.is_set():
                    if datetime.now().strftime("%H:%M") == time_val:
                        self.execute_shutdown()
                        if not self.repeat_var.get(): break
                        time.sleep(61)
                    time.sleep(1)
        except Exception as e:
            self.status_label.configure(text=f"오류: {e}", text_color="#f44336")

    def wait_and_check(self, seconds):
        for _ in range(int(seconds)):
            if self.stop_event.is_set(): return True
            time.sleep(1)
        return False

    def execute_shutdown(self):
        if not self.stop_event.is_set():
            os.system("shutdown /s /t 60")
            self.after(0, lambda: messagebox.showinfo("알림", "60초 후 종료됩니다."))

    def cancel_shutdown(self):
        self.stop_event.set()
        os.system("shutdown -a")
        self.status_label.configure(text="예약 취소됨", text_color="#f44336")

if __name__ == "__main__":
    app = ModernShutdownApp()
    app.mainloop()