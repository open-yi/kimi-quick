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
W, H = CSS_W + 16, CSS_H + 85  # frame + title bar compensation

# ── Client hints inject ──────────────────────────────────────────
# ponytail: inject Sec-CH-UA-* headers via webview's request_sent event
# so Bing/Google serve correct mobile pages.
CLIENT_HINT_HEADERS = {
    "sec-ch-ua": '"Google Chrome";v="149", "Chromium";v="149", "Not)A;Brand";v="24"',
    "sec-ch-ua-arch": '""',
    "sec-ch-ua-bitness": '"64"',
    "sec-ch-ua-full-version-list": '"Google Chrome";v="149.0.7827.155", "Chromium";v="149.0.7827.155", "Not)A;Brand";v="24.0.0.0"',
    "sec-ch-ua-mobile": "?1",
    "sec-ch-ua-model": '"iPhone"',
    "sec-ch-ua-platform": '"iOS"',
    "sec-ch-ua-platform-version": '"18.5"',
    "sec-ch-ua-wow64": "?0",
}

def _inject_client_hints(window):
    def on_request(req):
        req.headers.update(CLIENT_HINT_HEADERS)
    window.events.request_sent += on_request

# ponytail: enable clipboard (Ctrl+C/V) + right-click context menu in WebView2
def _patch_webview_settings():
    from webview.platforms.edgechromium import EdgeChrome
    _orig = EdgeChrome.on_webview_ready

    def _on_ready(self, sender, args):
        _orig(self, sender, args)
        settings = sender.CoreWebView2.Settings
        settings.AreBrowserAcceleratorKeysEnabled = True
        settings.AreDefaultContextMenusEnabled = True
    EdgeChrome.on_webview_ready = _on_ready

_patch_webview_settings()

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

# ── Single instance ──────────────────────────────────────────────
mutex = kernel32.CreateMutexW(None, False, "KimiQuickApp_SingleInstance")
if kernel32.GetLastError() == 183:
    print("已在运行中", flush=True)
    sys.exit(0)

quit_flag = False
real_quit = False
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
                visible = user32.IsWindowVisible(hwnd)
                focused = user32.GetForegroundWindow() == hwnd
                if visible and focused:
                    user32.ShowWindow(hwnd, 0)
                elif visible and not focused:
                    # ponytail: steal focus back instead of hiding
                    user32.keybd_event(0x12, 0, 0, 0)
                    user32.keybd_event(0x12, 0, 2, 0)
                    user32.SetForegroundWindow(hwnd)
                else:
                    user32.SetWindowPos(hwnd, -1, x, y, W, H, 0)
                    user32.ShowWindow(hwnd, 5)
                    user32.keybd_event(0x12, 0, 0, 0)
                    user32.keybd_event(0x12, 0, 2, 0)
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
            user32.keybd_event(0x12, 0, 0, 0)
            user32.keybd_event(0x12, 0, 2, 0)
            user32.SetForegroundWindow(hwnd)
def tray_refresh(icon, item):
    try:
        if webview.windows:
            webview.windows[0].evaluate_js("location.reload()")
    except Exception:
        pass
def tray_quit(icon, item):
    global quit_flag, real_quit
    quit_flag = True
    real_quit = True
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
    _auto_hidden = False

    def auto_hide(self):
        if self._auto_hidden:
            return
        self._auto_hidden = True
        self.hide()

    def open_in_browser(self):
        import webbrowser
        try:
            if webview.windows:
                url = webview.windows[0].get_current_url()
                if url:
                    webbrowser.open(url)
        except Exception:
            pass

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

_inject_client_hints(window)
def on_loaded():
    window.evaluate_js("""
        var tb = document.createElement('div')
        tb.id = '__tb'
        tb.innerHTML = '<div id="__logo" style="display:flex;align-items:center;gap:6px;cursor:pointer"><img src="https://www.kimi.com/favicon.ico" style="width:18px;height:18px"><span style="font-size:13px;font-family:system-ui">Kimi</span></div><div style="display:flex;align-items:center;gap:10px;margin-left:auto">'
            + '<button id="__btn_back" title="上一页" style="background:none;border:none;cursor:pointer;padding:0;display:flex;align-items:center"><svg viewBox="0 0 24 24" width="16" height="16"><path fill="#555" d="M15.41 7.41L14 6l-6 6 6 6 1.41-1.41L10.83 12z"/></svg></button>'
            + '<button id="__btn_refresh" title="刷新" style="background:none;border:none;cursor:pointer;padding:0;display:flex;align-items:center"><svg viewBox="0 0 24 24" width="16" height="16"><path fill="#555" d="M17.65 6.35C16.2 4.9 14.21 4 12 4c-4.42 0-7.99 3.58-7.99 8s3.57 8 7.99 8c3.73 0 6.84-2.55 7.73-6h-2.08c-.82 2.33-3.04 4-5.65 4-3.31 0-6-2.69-6-6s2.69-6 6-6c1.66 0 3.14.69 4.22 1.78L13 11h7V4l-2.35 2.35z"/></svg></button>'
            + '<button id="__btn_open" title="在浏览器中打开" style="background:none;border:none;cursor:pointer;padding:0;display:flex;align-items:center"><svg viewBox="0 0 24 24" width="16" height="16"><path fill="#555" d="M19 19H5V5h7V3H5c-1.11 0-2 .9-2 2v14c0 1.1.89 2 2 2h14c1.1 0 2-.9 2-2v-7h-2v7zM14 3v2h3.59l-9.83 9.83 1.41 1.41L19 6.41V10h2V3h-7z"/></svg></button>'
            + '<button id="__btn_bing" title="Bing" style="background:none;border:none;cursor:pointer;padding:0;display:flex;align-items:center"><img src="https://www.bing.com/favicon.ico" style="width:16px;height:16px"></button>'
            + '<button id="__btn_google" title="Google" style="background:none;border:none;cursor:pointer;padding:0;display:flex;align-items:center"><svg viewBox="0 0 24 24" width="16" height="16"><path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"/><path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/><path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/><path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/></svg></button>'
            + '</div>'
        tb.style.cssText = 'color:#333;position:fixed;top:0;left:0;right:0;height:37px;z-index:2147483647;display:flex;align-items:center;padding:0 10px;cursor:move'
        document.body.appendChild(tb)
        tb.addEventListener('pointerdown', function(e) {
            if (e.target.closest('button') || e.target.closest('#__logo')) return;
            window.pywebview.api.start()
        })
        document.getElementById('__btn_refresh').addEventListener('click', function() { location.reload() })
        document.getElementById('__btn_back').addEventListener('click', function() { history.back() })
        document.getElementById('__btn_open').addEventListener('click', function() { window.pywebview.api.open_in_browser() })
        document.getElementById('__logo').addEventListener('click', function() { location.href = 'https://www.kimi.com' })
        document.getElementById('__btn_bing').addEventListener('click', function() { location.href = 'https://cn.bing.com' })
        document.getElementById('__btn_google').addEventListener('click', function() { location.href = 'https://www.google.com' })
        setTimeout(function() { window.pywebview.api.auto_hide() }, 2000)
        var style = document.createElement('style');
        style.textContent = `
            html {
                padding-top: 37px;
                overflow: hidden !important;
            }
            * {
                -webkit-user-select: text;
                user-select: text;
            }
        `;
        document.body.appendChild(style);
        // ponytail: mouse wheel scroll for mobile pages
        (function() {
            document.addEventListener('wheel', function(e) {
                var el = e.target;
                while (el && el !== document.body) {
                    var s = getComputedStyle(el);
                    var ov = s.overflowY || s.overflow;
                    if (/(auto|scroll)/.test(ov) && el.scrollHeight > el.clientHeight) {
                        el.scrollTop += e.deltaY;
                        e.preventDefault();
                        return;
                    }
                    el = el.parentElement;
                }
                window.scrollBy(0, e.deltaY);
                e.preventDefault();
            }, {passive: false});
        })();
        (function tryFocus(n) {
            var el = document.querySelector('input:not([type="hidden"]), textarea, [contenteditable]');
            if (el) { el.focus(); return; }
            if (n < 20) setTimeout(function() { tryFocus(n + 1); }, 500);
        })(0)
    """)

def on_closing():
    global real_quit
    if real_quit:
        return True  # allow actual close
    window.hide()
    return False  # ponytail: hide instead of destroy, avoid WebView2 reinit white screen

window.events.closing += on_closing
window.events.loaded += on_loaded
webview.start(debug=False, user_agent=UA, private_mode=False)