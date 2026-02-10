import customtkinter as ctk
import os
import time
import threading
import sys
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
        self.title("ShutdownApp")
        self.geometry("400x580")
        self.configure(fg_color="#1a1a1a")

        # 제어 변수
        self.stop_event = threading.Event()
        self.stop_event.set() # 처음엔 정지 상태

        # 창 닫기 버튼 클릭 시 트레이로 숨기기
        self.protocol('WM_DELETE_WINDOW', self.hide_to_tray)

        # --- UI 구성 ---
        self.label = ctk.CTkLabel(self, text="시스템 종료 예약", font=ctk.CTkFont(size=22, weight="bold"))
        self.label.pack(pady=(30, 20))

        # 입력 영역 카드
        self.input_frame = ctk.CTkFrame(self, fg_color="#2b2b2b", corner_radius=15)
        self.input_frame.pack(pady=10, padx=30, fill="both")

        ctk.CTkLabel(self.input_frame, text="남은 시간 (분 단위)").pack(pady=(15, 5))
        self.timer_entry = ctk.CTkEntry(self.input_frame, placeholder_text="예: 30", width=200, border_width=1)
        self.timer_entry.pack(pady=5)

        ctk.CTkLabel(self.input_frame, text="정해진 시각 (HH:MM)").pack(pady=(15, 5))
        self.time_entry = ctk.CTkEntry(self.input_frame, placeholder_text="예: 02:00", width=200, border_width=1)
        self.time_entry.pack(pady=5)

        self.repeat_var = ctk.BooleanVar(value=False)
        self.repeat_switch = ctk.CTkSwitch(self.input_frame, text="매일 이 시간에 반복", variable=self.repeat_var)
        self.repeat_switch.pack(pady=(10, 20))

        # 버튼 영역
        self.start_button = ctk.CTkButton(self, text="예약 시작", command=self.start_thread,
                                          corner_radius=8, fg_color="#0067c0", hover_color="#005aab", font=ctk.CTkFont(weight="bold"))
        self.start_button.pack(pady=(20, 10), padx=30, fill="x")

        self.cancel_button = ctk.CTkButton(self, text="예약 취소", command=self.cancel_shutdown,
                                           corner_radius=8, fg_color="transparent", border_width=1, border_color="#f44336", text_color="#f44336")
        self.cancel_button.pack(pady=10, padx=30, fill="x")

        # 상태 표시줄
        self.status_label = ctk.CTkLabel(self, text="대기 중", font=ctk.CTkFont(size=12), text_color="gray")
        self.status_label.pack(side="bottom", pady=20)

        # 트레이 아이콘 초기화
        self.create_tray_icon()

    # --- 트레이 아이콘 로직 ---
    def create_tray_icon(self):
        width, height = 64, 64
        image = Image.new('RGB', (width, height), color="#1a1a1a")
        dc = ImageDraw.Draw(image)
        dc.ellipse([8, 8, 56, 56], fill="#0067c0") # 아이콘 모양

        menu = (
            pystray.MenuItem('열기', self.show_window, default=True),
            pystray.MenuItem('종료', self.quit_app)
        )
        self.tray_icon = pystray.Icon("ShutdownApp", image, "시스템 종료 예약", menu)
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def hide_to_tray(self):
        self.withdraw()

    def show_window(self):
        self.deiconify()
        self.focus_force()

    def quit_app(self):
        self.stop_event.set()
        self.tray_icon.stop()
        self.destroy()
        sys.exit()

    # --- 예약 실행 로직 ---
    def start_thread(self):
        self.stop_event.clear()
        t = threading.Thread(target=self.run_logic, daemon=True)
        t.start()

    def run_logic(self):
        timer_val = self.timer_entry.get().strip()
        time_val = self.time_entry.get().strip()

        try:
            if timer_val:
                if not timer_val.isdigit(): raise ValueError("숫자만 입력 가능합니다.")
                target_seconds = int(timer_val) * 60
                self.status_label.configure(text=f"알림: {timer_val}분 뒤 종료 예정", text_color="#0067c0")

                # 5분 전 알림 처리
                if target_seconds > 300:
                    if self.wait_and_check(target_seconds - 300): return
                    self.show_warning_notification("5분 뒤 시스템이 종료됩니다!")
                    if self.wait_and_check(300): return
                else:
                    if self.wait_and_check(target_seconds): return

                self.execute_shutdown()

            elif time_val:
                try:
                    datetime.strptime(time_val, "%H:%M")
                except ValueError:
                    raise ValueError("시간 형식이 틀립니다 (HH:MM).")

                self.status_label.configure(text=f"알림: {time_val}에 종료 예정", text_color="#0067c0")

                while not self.stop_event.is_set():
                    now_dt = datetime.now()
                    now_str = now_dt.strftime("%H:%M")

                    if now_str == time_val:
                        self.execute_shutdown()
                        if not self.repeat_var.get(): break
                        time.sleep(61) # 중복 방지

                    # 5분 전 체크
                    target_dt = datetime.strptime(time_val, "%H:%M").replace(
                        year=now_dt.year, month=now_dt.month, day=now_dt.day
                    )
                    diff = (target_dt - now_dt).total_seconds()
                    if 299 < diff <= 300: # 딱 5분 전 근처일 때
                        self.show_warning_notification("5분 뒤 시스템이 종료됩니다!")
                        time.sleep(1.1)

                    time.sleep(1)
            else:
                raise ValueError("시간을 입력해주세요.")

        except ValueError as e:
            self.status_label.configure(text=f"오류: {e}", text_color="#f44336")

    def wait_and_check(self, seconds):
        for _ in range(int(seconds)):
            if self.stop_event.is_set(): return True
            time.sleep(1)
        return False

    def show_warning_notification(self, message):
        self.after(0, lambda: messagebox.showwarning("스케줄러 알림", message))

    def execute_shutdown(self):
        if not self.stop_event.is_set():
            os.system("shutdown /s /t 60")
            self.after(0, lambda: messagebox.showinfo("시스템 종료", "60초 후 컴퓨터가 종료됩니다."))

    def cancel_shutdown(self):
        self.stop_event.set()
        os.system("shutdown -a")
        self.status_label.configure(text="예약이 취소되었습니다.", text_color="#f44336")

if __name__ == "__main__":
    app = ModernShutdownApp()
    app.mainloop()