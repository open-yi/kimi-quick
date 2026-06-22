"""
Quick Web Popup — F4 toggle browser window, always-on-top.
Custom title bar (draggable) + system tray.
"""
import ctypes
import sys
import threading
import time
import webview
import pystray
from PIL import Image

URL = "https://www.kimi.com"
CSS_W, CSS_H = 375, 667
TITLE = "Kimi"
VK_F4 = 0x73
W, H = CSS_W + 16, CSS_H + 48  # frame + title bar compensation

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

# ── Single instance ──────────────────────────────────────────────
mutex = kernel32.CreateMutexW(None, False, "KimiQuickApp_SingleInstance")
if kernel32.GetLastError() == 183:
    print("已在运行中", flush=True)
    sys.exit(0)

quit_flag = False
hwnd = None

# ── F4 poller ────────────────────────────────────────────────────


def poll_f4():
    global hwnd
    f4_was_down = False
    for _ in range(100):
        hwnd = user32.FindWindowW(None, TITLE)
        if hwnd:
            # Remove minimize + maximize (keep close + icon)
            s = user32.GetWindowLongW(hwnd, -16)
            user32.SetWindowLongW(hwnd, -16, s & ~(0x00020000 | 0x00010000))
            user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, 0x0002 | 0x0001 | 0x0020)
            # Set window icon
            try:
                import os as _os
                if getattr(sys, 'frozen', False):
                    base = sys._MEIPASS
                else:
                    base = _os.path.dirname(_os.path.abspath(__file__))
                ico = _os.path.join(base, "kimi_favicon.ico")
                hicon = user32.LoadImageW(0, ico, 1, 0, 0, 0x10 | 0x40)
                if hicon:
                    user32.SendMessageW(hwnd, 0x0080, 0, hicon)
                    user32.SendMessageW(hwnd, 0x0080, 1, hicon)
            except Exception:
                pass
            break
        time.sleep(0.02)
    while not quit_flag:
        f4_down = user32.GetAsyncKeyState(VK_F4) & 0x8000
        if f4_down and not f4_was_down:
            if not hwnd or not user32.IsWindow(hwnd):
                hwnd = user32.FindWindowW(None, TITLE)
            if hwnd and user32.IsWindow(hwnd):
                if user32.IsWindowVisible(hwnd):
                    user32.ShowWindow(hwnd, 0)
                else:
                    user32.SetWindowPos(hwnd, -1, x, y, W, H, 0)
                    user32.ShowWindow(hwnd, 5)
                    user32.SetForegroundWindow(hwnd)
                    try:
                        if webview.windows:
                            webview.windows[0].evaluate_js(
                                "(function(){var e=document.querySelector('input:not([type=\"hidden\"]),textarea,[contenteditable]');if(e)e.focus()})()")
                    except Exception:
                        pass
        f4_was_down = f4_down
        time.sleep(0.05)

# ── Tray ─────────────────────────────────────────────────────────


def make_icon():
    import os
    if getattr(sys, 'frozen', False):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return Image.open(os.path.join(base, "kimi_favicon.ico"))


def tray_show_hide(icon, item):
    global hwnd
    if not hwnd or not user32.IsWindow(hwnd):
        hwnd = user32.FindWindowW(None, TITLE)
    if hwnd and user32.IsWindow(hwnd):
        if user32.IsWindowVisible(hwnd):
            user32.ShowWindow(hwnd, 0)
        else:
            user32.SetWindowPos(hwnd, -1, x, y, W, H, 0)
            user32.ShowWindow(hwnd, 5)
            user32.SetForegroundWindow(hwnd)


def tray_refresh(icon, item):
    try:
        if webview.windows:
            webview.windows[0].evaluate_js("location.reload()")
    except Exception:
        pass


def tray_quit(icon, item):
    global quit_flag
    quit_flag = True
    icon.stop()
    try:
        if webview.windows:
            webview.windows[0].destroy()
    except Exception:
        pass


def run_tray():
    try:
        icon = pystray.Icon("webpopup", make_icon(), "kimi",
                            menu=pystray.Menu(
            pystray.MenuItem("显示/隐藏 (F4)", tray_show_hide, default=True),
            pystray.MenuItem("刷新", tray_refresh),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("退出", tray_quit),
        ))
        icon.run()
    except Exception as e:
        print(f"[tray error] {e}", flush=True)


# ── Launch ───────────────────────────────────────────────────────
threading.Thread(target=poll_f4, daemon=True).start()
threading.Thread(target=run_tray, daemon=True).start()

screen_w = user32.GetSystemMetrics(0)
screen_h = user32.GetSystemMetrics(1)
x, y = max(0, (screen_w - W) // 2), max(0, (screen_h - H) // 2)

UA = "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1"


class DragApi:
    def start(self):
        global hwnd, quit_flag
        if not hwnd:
            hwnd = user32.FindWindowW(None, TITLE)
        if not hwnd:
            return
        pt = ctypes.wintypes.POINT()
        user32.GetCursorPos(ctypes.byref(pt))
        r = ctypes.wintypes.RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(r))
        sx, sy, wx, wy = pt.x, pt.y, r.left, r.top

        def drag_loop():
            while not quit_flag and (user32.GetAsyncKeyState(0x01) & 0x8000):
                user32.GetCursorPos(ctypes.byref(pt))
                user32.SetWindowPos(hwnd, 0,
                                    wx + pt.x - sx, wy + pt.y - sy, 0, 0, 0x0001 | 0x0004)
                time.sleep(0.01)

        threading.Thread(target=drag_loop, daemon=True).start()

    def hide(self):
        global hwnd
        if not hwnd:
            hwnd = user32.FindWindowW(None, TITLE)
        if hwnd and user32.IsWindow(hwnd):
            user32.ShowWindow(hwnd, 0)


window = webview.create_window(
    title=TITLE, url=URL, js_api=DragApi(),
    width=W, height=H, x=x, y=y,
    resizable=False, on_top=True, frameless=True,
    easy_drag=False, confirm_close=False,
)


def on_loaded():
    window.evaluate_js("""
        var tb = document.createElement('div')
        tb.id = '__tb'
        tb.innerHTML = '<img src="https://www.kimi.com/favicon.ico" style="width:18px;height:18px;margin-right:6px"><span style="font-size:13px;font-family:system-ui">Kimi</span>'
        tb.style.cssText = 'color:#333;position:fixed;top:0;left:0;right:0;height:32px;z-index:2147483647;background:#fff;display:flex;align-items:center;padding:0 10px;cursor:move'
        document.body.appendChild(tb)
        tb.addEventListener('pointerdown', function() { window.pywebview.api.start() })
        setTimeout(function() { window.pywebview.api.hide() }, 2000)
        var style = document.createElement('style');
        style.textContent = `
            html {
                padding-top: 32px;
                overflow: hidden;
            }
        `;
        document.body.appendChild(style);
        (function tryFocus(n) {
            var el = document.querySelector('input:not([type="hidden"]), textarea, [contenteditable]');
            if (el) { el.focus(); return; }
            if (n < 20) setTimeout(function() { tryFocus(n + 1); }, 500);
        })(0)
    """)


window.events.loaded += on_loaded
webview.start(debug=False, user_agent=UA, private_mode=False)
