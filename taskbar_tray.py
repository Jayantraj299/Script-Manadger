# taskbar_tray.py
import pystray
from PIL import Image, ImageDraw
import threading

class SystemTray:
    def __init__(self, app, title="Command Center"):
        self.app = app
        self.title = title
        self.icon = None
        self.thread = None

    def create_icon_image(self):
        # Creates a simple Green Dot icon. 
        # (You can replace this with Image.open("your_icon.png") later)
        width = 64
        height = 64
        image = Image.new('RGBA', (width, height), color=(0, 0, 0, 0))
        dc = ImageDraw.Draw(image)
        dc.ellipse((10, 10, 54, 54), fill="#2ecc71")
        return image

    def run(self):
        """Hides the app and starts the tray icon."""
        if self.icon: return

        # The 'default=True' makes it trigger on Left-Click
        menu = pystray.Menu(
            pystray.MenuItem("Quick Controls", self.show_mini, default=True),
            pystray.MenuItem("Open Full Dashboard", self.show_app),
            pystray.MenuItem("Quit Background Agent", self.quit_app)
        )

        self.icon = pystray.Icon("command_center", self.create_icon_image(), self.title, menu)
        
        self.thread = threading.Thread(target=self.icon.run, daemon=True)
        self.thread.start()

    def stop(self):
        """Removes the tray icon."""
        if self.icon:
            self.icon.stop()
            self.icon = None

    def show_mini(self, icon=None, item=None):
        # We do NOT stop the tray icon here. We just tell the main app
        # to pop up the mini borderless window.
        self.app.after(0, self.app.show_mini_dashboard)

    def show_app(self, icon=None, item=None):
        self.stop()
        self.app.after(0, self.app.restore_window)

    def quit_app(self, icon=None, item=None):
        self.stop()
        self.app.after(0, self.app.quit_app_fully)