import customtkinter as ctk
import time

# Standard Widget Class
class Widget(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        
        self.lbl_time = ctk.CTkLabel(self, text="00:00:00", font=("Consolas", 40, "bold"), text_color="#3498db")
        self.lbl_time.pack(expand=True)
        
        self.update_clock()

    def update_clock(self):
        self.lbl_time.configure(text=time.strftime("%H:%M:%S"))
        self.after(1000, self.update_clock)
