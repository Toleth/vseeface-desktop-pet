# -*- coding: utf-8 -*-
"""
VSeeFace 桌面透明角色 (VSeeFace Desktop Pet)

原理：
  VSeeFace 通过 Spout2 输出一份「带 Alpha 通道、且不含 UI」的画面，
  本程序接收这份画面，并用逐像素透明（per-pixel alpha）的分层窗口直接画在桌面上，
  因此不需要 OBS 之类的直播软件，也不需要绿幕抠像。

使用前提（只需在 VSeeFace 里设置一次）：
  VSeeFace -> Settings(设置) -> General(常规) -> 勾选 "Spout2 Image Capture Support"

操作：
  左键拖动 = 移动角色
  右键      = 菜单（鼠标穿透 / 置顶 / 重置位置 / 退出）
  托盘图标  = 同上

依赖: pip install SpoutGL pillow
"""
import ctypes
import json
import os
import sys
import time
from ctypes import (POINTER, Structure, byref, c_int, c_long, c_ssize_t, c_ubyte, c_uint,
                    c_uint32, c_uint64, c_ushort, c_void_p, c_wchar, c_wchar_p)

APP = 'VSeeFaceDesktopPet'
# 打包成单文件 exe 后 __file__ 指向临时解压目录，配置要存到 exe 旁边
if getattr(sys, 'frozen', False):
    BASE = os.path.dirname(sys.executable)
else:
    BASE = os.path.dirname(os.path.abspath(__file__))
CONF = os.path.join(BASE, 'vsf_pet_config.json')
LOG = os.path.join(BASE, 'vsf_debug.log')


def trace(msg):
    try:
        with open(LOG, 'a', encoding='utf-8') as f:
            f.write('%s %s\n' % (time.strftime('%Y-%m-%d %H:%M:%S'), msg))
    except Exception:
        pass


_DLL_DIR_HANDLES = []


def setup_dll_dirs():
    """单文件打包后，SpoutGL 的 pyd 依赖位于子目录中的 DLL，需要显式注册搜索路径。"""
    if not getattr(sys, 'frozen', False):
        return
    base = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
    for sub in ('', 'SpoutGL', 'spoutgl.libs', 'numpy.libs', 'numpy', 'numpy\\core'):
        p = os.path.join(base, sub)
        if os.path.isdir(p):
            try:
                _DLL_DIR_HANDLES.append(os.add_dll_directory(p))
            except Exception:
                pass

# 打包为无控制台程序时 stdout/stderr 为 None，避免 print 崩溃
if sys.stdout is None:
    sys.stdout = open(os.devnull, 'w')
if sys.stderr is None:
    sys.stderr = open(os.devnull, 'w')

user32 = ctypes.WinDLL('user32', use_last_error=True)
gdi32 = ctypes.WinDLL('gdi32', use_last_error=True)
opengl32 = ctypes.WinDLL('opengl32', use_last_error=True)
shell32 = ctypes.WinDLL('shell32', use_last_error=True)
kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)

HWND = c_void_p
HINSTANCE = c_void_p
LRESULT = c_ssize_t
WPARAM = c_uint64
LPARAM = c_ssize_t
WNDPROC = ctypes.WINFUNCTYPE(LRESULT, HWND, c_uint, WPARAM, LPARAM)

# ---------------- constants ----------------
WS_POPUP = 0x80000000
WS_EX_LAYERED = 0x00080000
WS_EX_TOPMOST = 0x00000008
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_TRANSPARENT = 0x00000020
WS_EX_NOACTIVATE = 0x08000000
GWL_EXSTYLE = -20
ULW_ALPHA = 0x2
AC_SRC_OVER = 0
AC_SRC_ALPHA = 1
BI_RGB = 0

WM_DESTROY = 0x0002
WM_CLOSE = 0x0010
WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
WM_MOUSEMOVE = 0x0200
WM_RBUTTONUP = 0x0205
WM_MOUSEACTIVATE = 0x0021
WM_DISPLAYCHANGE = 0x007E
MA_NOACTIVATE = 3
WM_APP = 0x8000
WM_TRAY = WM_APP + 1

MF_STRING = 0x0000
MF_SEPARATOR = 0x0800
MF_CHECKED = 0x0008
TPM_RETURNCMD = 0x0100
TPM_LEFTBUTTON = 0x0000

NIF_MESSAGE, NIF_ICON, NIF_TIP = 1, 2, 4
NIM_ADD, NIM_DELETE = 0, 2
IDI_APPLICATION = 32512

MF_GRAYED = 0x0001


class POINT(Structure):
    _fields_ = [('x', c_long), ('y', c_long)]


class SIZE(Structure):
    _fields_ = [('cx', c_long), ('cy', c_long)]


class RECT(Structure):
    _fields_ = [('left', c_long), ('top', c_long), ('right', c_long), ('bottom', c_long)]


class BLENDFUNCTION(Structure):
    _fields_ = [('BlendOp', c_ubyte), ('BlendFlags', c_ubyte),
                ('SourceConstantAlpha', c_ubyte), ('AlphaFormat', c_ubyte)]


class WNDCLASSEXW(Structure):
    _fields_ = [('cbSize', c_uint), ('style', c_uint), ('lpfnWndProc', WNDPROC),
                ('cbClsExtra', c_int), ('cbWndExtra', c_int), ('hInstance', HINSTANCE),
                ('hIcon', c_void_p), ('hCursor', c_void_p), ('hbrBackground', c_void_p),
                ('lpszMenuName', c_wchar_p), ('lpszClassName', c_wchar_p), ('hIconSm', c_void_p)]


class MSG(Structure):
    _fields_ = [('hwnd', HWND), ('message', c_uint), ('wParam', WPARAM), ('lParam', LPARAM),
                ('time', c_uint32), ('pt', POINT), ('lPrivate', c_uint32)]


class BITMAPINFOHEADER(Structure):
    _fields_ = [('biSize', c_uint32), ('biWidth', c_int), ('biHeight', c_int),
                ('biPlanes', c_ushort), ('biBitCount', c_ushort), ('biCompression', c_uint32),
                ('biSizeImage', c_uint32), ('biXPelsPerMeter', c_int), ('biYPelsPerMeter', c_int),
                ('biClrUsed', c_uint32), ('biClrImportant', c_uint32)]


class BITMAPINFO(Structure):
    _fields_ = [('bmiHeader', BITMAPINFOHEADER), ('bmiColors', c_uint32 * 3)]


class NOTIFYICONDATAW(Structure):
    _fields_ = [('cbSize', c_uint32), ('hWnd', HWND), ('uID', c_uint), ('uFlags', c_uint),
                ('uCallbackMessage', c_uint), ('hIcon', c_void_p), ('szTip', c_wchar * 128),
                ('dwState', c_uint32), ('dwStateMask', c_uint32), ('szInfo', c_wchar * 256),
                ('uVersion', c_uint), ('szInfoTitle', c_wchar * 64), ('dwInfoFlags', c_uint32),
                ('guidItem', c_ubyte * 16), ('hBalloonIcon', c_void_p)]


class PIXELFORMATDESCRIPTOR(Structure):
    _fields_ = [('nSize', c_ushort), ('nVersion', c_ushort), ('dwFlags', c_uint32),
                ('iPixelType', c_ubyte), ('cColorBits', c_ubyte), ('cRedBits', c_ubyte),
                ('cRedShift', c_ubyte), ('cGreenBits', c_ubyte), ('cGreenShift', c_ubyte),
                ('cBlueBits', c_ubyte), ('cBlueShift', c_ubyte), ('cAlphaBits', c_ubyte),
                ('cAlphaShift', c_ubyte), ('cAccumBits', c_ubyte), ('cAccumRedBits', c_ubyte),
                ('cAccumGreenBits', c_ubyte), ('cAccumBlueBits', c_ubyte), ('cAccumAlphaBits', c_ubyte),
                ('cDepthBits', c_ubyte), ('cStencilBits', c_ubyte), ('cAuxBuffers', c_ubyte),
                ('iLayerType', c_ubyte), ('bReserved', c_ubyte), ('dwLayerMask', c_uint32),
                ('dwVisibleMask', c_uint32), ('dwDamageMask', c_uint32)]


# ---------------- prototypes ----------------
user32.RegisterClassExW.argtypes = [POINTER(WNDCLASSEXW)]
user32.RegisterClassExW.restype = c_ushort
user32.UnregisterClassW.argtypes = [c_wchar_p, HINSTANCE]
user32.CreateWindowExW.argtypes = [c_uint32, c_wchar_p, c_wchar_p, c_uint32, c_int, c_int, c_int,
                                   c_int, HWND, c_void_p, HINSTANCE, c_void_p]
user32.CreateWindowExW.restype = HWND
user32.DefWindowProcW.argtypes = [HWND, c_uint, WPARAM, LPARAM]
user32.DefWindowProcW.restype = LRESULT
user32.GetDC.argtypes = [HWND]
user32.GetDC.restype = c_void_p
user32.ReleaseDC.argtypes = [HWND, c_void_p]
user32.UpdateLayeredWindow.argtypes = [HWND, c_void_p, POINTER(POINT), POINTER(SIZE), c_void_p,
                                       POINTER(POINT), c_uint32, POINTER(BLENDFUNCTION), c_uint32]
user32.UpdateLayeredWindow.restype = ctypes.c_bool
user32.GetMessageW.argtypes = [POINTER(MSG), HWND, c_uint, c_uint]
user32.GetMessageW.restype = c_int
user32.PeekMessageW.argtypes = [POINTER(MSG), HWND, c_uint, c_uint, c_uint]
user32.PeekMessageW.restype = ctypes.c_bool
user32.TranslateMessage.argtypes = [POINTER(MSG)]
user32.DispatchMessageW.argtypes = [POINTER(MSG)]
user32.DispatchMessageW.restype = LRESULT
user32.PostQuitMessage.argtypes = [c_int]
user32.DestroyWindow.argtypes = [HWND]
user32.ShowWindow.argtypes = [HWND, c_int]
user32.SetWindowPos.argtypes = [HWND, HWND, c_int, c_int, c_int, c_int, c_uint]
user32.SetWindowPos.restype = ctypes.c_bool
user32.SetCapture.argtypes = [HWND]
user32.ReleaseCapture.argtypes = []
user32.GetCursorPos.argtypes = [POINTER(POINT)]
user32.GetSystemMetrics.argtypes = [c_int]
user32.GetSystemMetrics.restype = c_int
user32.CreatePopupMenu.restype = c_void_p
user32.AppendMenuW.argtypes = [c_void_p, c_uint, c_ssize_t, c_wchar_p]
user32.TrackPopupMenu.argtypes = [c_void_p, c_uint, c_int, c_int, c_int, HWND, c_void_p]
user32.TrackPopupMenu.restype = c_int
user32.DestroyMenu.argtypes = [c_void_p]
user32.SetForegroundWindow.argtypes = [HWND]
user32.LoadIconW.argtypes = [HINSTANCE, c_void_p]
user32.LoadIconW.restype = c_void_p
user32.LoadCursorW.argtypes = [HINSTANCE, c_void_p]
user32.LoadCursorW.restype = c_void_p
user32.MessageBoxW.argtypes = [HWND, c_wchar_p, c_wchar_p, c_uint]
user32.MessageBoxW.restype = c_int
user32.PostMessageW.argtypes = [HWND, c_uint, WPARAM, LPARAM]
user32.GetWindowRect.argtypes = [HWND, POINTER(RECT)]
user32.SetProcessDPIAware.restype = ctypes.c_bool

try:
    _glp = user32.GetWindowLongPtrW
    _slp = user32.SetWindowLongPtrW
except AttributeError:
    _glp = user32.GetWindowLongW
    _slp = user32.SetWindowLongW
_glp.argtypes = [HWND, c_int]
_glp.restype = c_ssize_t
_slp.argtypes = [HWND, c_int, c_ssize_t]
_slp.restype = c_ssize_t

gdi32.CreateCompatibleDC.argtypes = [c_void_p]
gdi32.CreateCompatibleDC.restype = c_void_p
gdi32.CreateDIBSection.argtypes = [c_void_p, POINTER(BITMAPINFO), c_uint32,
                                   POINTER(c_void_p), c_void_p, c_uint32]
gdi32.CreateDIBSection.restype = c_void_p
gdi32.SelectObject.argtypes = [c_void_p, c_void_p]
gdi32.SelectObject.restype = c_void_p
gdi32.DeleteObject.argtypes = [c_void_p]
gdi32.DeleteDC.argtypes = [c_void_p]
gdi32.ChoosePixelFormat.argtypes = [c_void_p, POINTER(PIXELFORMATDESCRIPTOR)]
gdi32.ChoosePixelFormat.restype = c_int
gdi32.SetPixelFormat.argtypes = [c_void_p, c_int, POINTER(PIXELFORMATDESCRIPTOR)]
gdi32.SetPixelFormat.restype = ctypes.c_bool
opengl32.wglCreateContext.argtypes = [c_void_p]
opengl32.wglCreateContext.restype = c_void_p
opengl32.wglMakeCurrent.argtypes = [c_void_p, c_void_p]
opengl32.wglMakeCurrent.restype = ctypes.c_bool
shell32.Shell_NotifyIconW.argtypes = [c_uint32, POINTER(NOTIFYICONDATAW)]
shell32.Shell_NotifyIconW.restype = ctypes.c_bool


# ---------------- OpenGL context for Spout ----------------
class GLContext:
    """Spout2 需要一个当前 OpenGL 上下文，这里用隐形 Win32 窗口建一个。"""

    def __init__(self):
        self._proc = WNDPROC(lambda h, m, w, l: user32.DefWindowProcW(h, m, w, l))
        wc = WNDCLASSEXW()
        self.cls = 'WBSpoutGLWnd_%d' % os.getpid()
        wc.cbSize = ctypes.sizeof(WNDCLASSEXW)
        wc.style = 0x0002 | 0x0020
        wc.lpfnWndProc = self._proc
        wc.hInstance = kernel32.GetModuleHandleW(None)
        wc.lpszClassName = self.cls
        user32.RegisterClassExW(byref(wc))
        self.hwnd = user32.CreateWindowExW(0, self.cls, 'wb', WS_POPUP, 0, 0, 1, 1,
                                           None, None, None, None)
        self.hdc = user32.GetDC(self.hwnd)
        pfd = PIXELFORMATDESCRIPTOR()
        pfd.nSize = ctypes.sizeof(PIXELFORMATDESCRIPTOR)
        pfd.nVersion = 1
        pfd.dwFlags = 0x00000004 | 0x00000020 | 0x00000001
        pfd.iPixelType = 0
        pfd.cColorBits = 32
        pfd.cAlphaBits = 8
        pfd.cDepthBits = 24
        pf = gdi32.ChoosePixelFormat(self.hdc, byref(pfd))
        gdi32.SetPixelFormat(self.hdc, pf, byref(pfd))
        self.hglrc = opengl32.wglCreateContext(self.hdc)
        self.ok = bool(self.hglrc) and bool(opengl32.wglMakeCurrent(self.hdc, self.hglrc))
        if not self.ok:
            raise RuntimeError('无法创建 OpenGL 上下文')


# ---------------- Spout source ----------------
class SpoutSource:
    def __init__(self):
        import SpoutGL
        self.SpoutGL = SpoutGL
        self.fmt = int(SpoutGL.enums.GL_RGBA)
        self.receiver = None
        self.name = None
        self.w = 0
        self.h = 0
        self.buf = None
        self.last_frame = None
        self._primed = False

    def available(self):
        if self.receiver is None:
            return []
        try:
            return list(self.receiver.getSenderList())
        except Exception:
            return []

    def connect(self, name=None):
        self.disconnect()
        self.receiver = self.SpoutGL.SpoutReceiver()
        self.receiver.setReceiverName(name or '')
        self.name = name
        self._primed = False
        if name:
            try:
                self.receiver.getSenderInfo(name)
            except Exception:
                pass
        return True

    def disconnect(self):
        if self.receiver is not None:
            try:
                self.receiver.releaseReceiver()
            except Exception:
                pass
            self.receiver = None

    def grab(self):
        """返回 (w, h, numpy RGBA array) 或 None"""
        if self.receiver is None:
            return None
        try:
            if not self._primed:
                # Spout 需要先用空 buffer 触发一次连接握手（只做一次）
                self.receiver.receiveImage(None, self.fmt, False, 0)
                self._primed = True
            w = self.receiver.getSenderWidth()
            h = self.receiver.getSenderHeight()
        except Exception:
            return None
        if not w or not h:
            return None
        import numpy as np
        if (w, h) != (self.w, self.h):
            self.w, self.h = w, h
        # 注意：Spout 会缓存缓冲区的映射，复用同一块内存会导致后续帧读到空数据，
        # 因此这里每帧重新分配。
        self.buf = np.zeros((h, w, 4), np.uint8)
        try:
            ok = self.receiver.receiveImage(self.buf, self.fmt, False, 0)
            self.receiver.isUpdated()
        except Exception:
            return None
        if not ok:
            return None
        return (w, h, self.buf)


# ---------------- Overlay window ----------------
class Overlay:
    def __init__(self, on_menu_action):
        self.on_menu_action = on_menu_action
        self.x = 100
        self.y = 100
        self.img_w = 0
        self.img_h = 0
        self.dragging = False
        self.drag_off = (0, 0)
        self.hbmp = None
        self.bits = None
        self.old_bmp = None
        self.topmost = True
        self.clickthrough = False
        self.flip = False
        self.need_auto_pos = False
        self.visible = True
        self._proc = WNDPROC(self._wndproc)
        self.cls = 'WBVSeFacePet_%d' % os.getpid()
        wc = WNDCLASSEXW()
        wc.cbSize = ctypes.sizeof(WNDCLASSEXW)
        wc.style = 0x0002 | 0x0020
        wc.lpfnWndProc = self._proc
        wc.hInstance = kernel32.GetModuleHandleW(None)
        wc.lpszClassName = self.cls
        wc.hCursor = user32.LoadCursorW(None, ctypes.c_void_p(32512))
        user32.RegisterClassExW(byref(wc))
        self.hwnd = user32.CreateWindowExW(
            WS_EX_LAYERED | WS_EX_TOPMOST | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE,
            self.cls, APP, WS_POPUP, self.x, self.y, 1, 1, None, None, None, None)
        self.memdc = gdi32.CreateCompatibleDC(None)
        user32.ShowWindow(self.hwnd, 5)  # SW_SHOW

    # ---- window proc ----
    def _wndproc(self, hwnd, msg, wp, lp):
        try:
            if msg == WM_MOUSEACTIVATE:
                return MA_NOACTIVATE
            if msg == WM_LBUTTONDOWN:
                pt = POINT()
                user32.GetCursorPos(byref(pt))
                self.dragging = True
                self.drag_off = (pt.x - self.x, pt.y - self.y)
                user32.SetCapture(hwnd)
                return 0
            if msg == WM_MOUSEMOVE and self.dragging:
                pt = POINT()
                user32.GetCursorPos(byref(pt))
                self.x = pt.x - self.drag_off[0]
                self.y = pt.y - self.drag_off[1]
                return 0
            if msg == WM_LBUTTONUP:
                if self.dragging:
                    self.dragging = False
                    user32.ReleaseCapture()
                    self.on_menu_action('moved', None)
                return 0
            if msg == WM_RBUTTONUP:
                self.show_menu()
                return 0
            if msg == WM_TRAY:
                low = lp & 0xFFFF
                if low in (0x0205, 0x0204):
                    self.show_menu()
                return 0
            if msg == WM_DISPLAYCHANGE:
                self.clamp_to_screen()
                return 0
            if msg == WM_DESTROY:
                user32.PostQuitMessage(0)
                return 0
        except Exception:
            pass
        return user32.DefWindowProcW(hwnd, msg, wp, lp)

    # ---- drawing ----
    def _ensure_buffer(self, w, h):
        if self.hbmp is not None:
            gdi32.SelectObject(self.memdc, self.old_bmp)
            gdi32.DeleteObject(self.hbmp)
            self.hbmp = None
        bi = BITMAPINFO()
        bi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        bi.bmiHeader.biWidth = w
        bi.bmiHeader.biHeight = -h
        bi.bmiHeader.biPlanes = 1
        bi.bmiHeader.biBitCount = 32
        bi.bmiHeader.biCompression = BI_RGB
        bits = c_void_p()
        self.hbmp = gdi32.CreateDIBSection(self.memdc, byref(bi), 0, byref(bits), None, 0)
        self.old_bmp = gdi32.SelectObject(self.memdc, self.hbmp)
        self.bits = bits
        self.img_w, self.img_h = w, h

    def blit(self, data, w: int, h: int):
        resized = (w, h) != (self.img_w, self.img_h)
        if resized:
            self._ensure_buffer(w, h)
            sw = user32.GetSystemMetrics(0)
            sh = user32.GetSystemMetrics(1)
            if self.need_auto_pos:
                # 第一次拿到画面：按真实尺寸放到屏幕底部居中
                self.need_auto_pos = False
                self.x = max(0, (sw - w) // 2)
                self.y = max(0, sh - h - 40)
            # 保证整个窗口落在屏幕内，避免角色被裁掉
            self.x = min(max(self.x, 0), max(0, sw - w))
            self.y = min(max(self.y, 0), max(0, sh - h))
        if hasattr(data, 'ctypes') and hasattr(data, 'nbytes'):
            ctypes.memmove(self.bits, data.ctypes.data, data.nbytes)
        else:
            ctypes.memmove(self.bits, data, w * h * 4)
        pt_dst = POINT(self.x, self.y)
        size = SIZE(w, h)
        pt_src = POINT(0, 0)
        bf = BLENDFUNCTION(AC_SRC_OVER, 0, 255, AC_SRC_ALPHA)
        user32.UpdateLayeredWindow(self.hwnd, None, byref(pt_dst), byref(size),
                                   self.memdc, byref(pt_src), 0, byref(bf), ULW_ALPHA)

    # ---- menu ----
    def show_menu(self):
        hmenu = user32.CreatePopupMenu()
        user32.AppendMenuW(hmenu, MF_STRING | (MF_CHECKED if self.clickthrough else 0), 1,
                           '鼠标穿透（点不到角色）')
        user32.AppendMenuW(hmenu, MF_STRING | (MF_CHECKED if self.topmost else 0), 2, '窗口总在最前')
        user32.AppendMenuW(hmenu, MF_STRING, 3, '回到屏幕中央')
        user32.AppendMenuW(hmenu, MF_STRING | (MF_CHECKED if self.flip else 0), 5, '上下翻转显示')
        user32.AppendMenuW(hmenu, MF_SEPARATOR, 0, None)
        user32.AppendMenuW(hmenu, MF_STRING, 4, '重新连接 VSeeFace')
        user32.AppendMenuW(hmenu, MF_STRING, 9, '退出')
        pt = POINT()
        user32.GetCursorPos(byref(pt))
        user32.SetForegroundWindow(self.hwnd)
        cmd = user32.TrackPopupMenu(hmenu, TPM_RETURNCMD | TPM_LEFTBUTTON, pt.x, pt.y, 0,
                                    self.hwnd, None)
        user32.DestroyMenu(hmenu)
        if cmd:
            self.on_menu_action(cmd, None)

    def set_clickthrough(self, on):
        ex = _glp(self.hwnd, GWL_EXSTYLE)
        ex = (ex | WS_EX_TRANSPARENT) if on else (ex & ~WS_EX_TRANSPARENT)
        _slp(self.hwnd, GWL_EXSTYLE, ex)
        self.clickthrough = on

    def set_topmost(self, on):
        user32.SetWindowPos(self.hwnd, ctypes.c_void_p(-1 if on else -2), 0, 0, 0, 0,
                            0x0001 | 0x0002 | 0x0010)
        self.topmost = on

    def center(self):
        sw = user32.GetSystemMetrics(0)
        sh = user32.GetSystemMetrics(1)
        self.x = max(0, (sw - (self.img_w or 400)) // 2)
        self.y = max(0, (sh - (self.img_h or 400)) // 2)

    def clamp_to_screen(self):
        sw = user32.GetSystemMetrics(0)
        sh = user32.GetSystemMetrics(1)
        self.x = min(max(self.x, -self.img_w + 60), sw - 60)
        self.y = min(max(self.y, 0), sh - 60)

    def destroy(self):
        user32.DestroyWindow(self.hwnd)


def to_bgra_premultiplied(img):
    """PIL RGBA 图像 -> UpdateLayeredWindow 需要的 BGRA 预乘 alpha 字节。"""
    try:
        import numpy as np
        arr = np.asarray(img.convert('RGBA'))
        a = arr[..., 3:4].astype(np.uint16)
        rgb = (arr[..., :3].astype(np.uint16) * a + 127) // 255
        out = np.empty(arr.shape, dtype=np.uint8)
        out[..., 0] = rgb[..., 2]
        out[..., 1] = rgb[..., 1]
        out[..., 2] = rgb[..., 0]
        out[..., 3] = arr[..., 3]
        return out.tobytes()
    except ImportError:
        prem = img.convert('RGBa')
        r, g, b, a = prem.split()
        return Image.merge('RGBA', (b, g, r, a)).tobytes()


def to_bgra_premultiplied_np(arr):
    """numpy RGBA (h,w,4) -> BGRA 预乘 alpha（UpdateLayeredWindow 需要）"""
    import numpy as np
    a = arr[..., 3:4].astype(np.uint16)
    rgb = (arr[..., :3].astype(np.uint16) * a + 127) // 255
    out = np.empty(arr.shape, dtype=np.uint8)
    out[..., 0] = rgb[..., 2]
    out[..., 1] = rgb[..., 1]
    out[..., 2] = rgb[..., 0]
    out[..., 3] = arr[..., 3]
    return out


def already_running():
    kernel32.CreateMutexW.argtypes = [c_void_p, ctypes.c_bool, c_wchar_p]
    kernel32.CreateMutexW.restype = c_void_p
    ctypes.set_last_error(0)
    h = kernel32.CreateMutexW(None, ctypes.c_bool(True), 'WB_VSeeFaceDesktopPet_Mutex')
    return ctypes.get_last_error() == 183, h


def main():
    trace('main start frozen=%s base=%s exe=%s' % (getattr(sys, 'frozen', False), BASE, sys.executable))
    setup_dll_dirs()
    _exists, _mutex = already_running()
    if _exists:
        user32.MessageBoxW(None, 'VSeeFace 桌面角色已经在运行了。\n\n'
                                 '如果看不到角色，请查看屏幕右下角托盘里的图标。',
                           APP, 0x40)
        return 0
    if sys.platform != 'win32':
        print('only windows')
        return 1
    try:
        user32.SetProcessDPIAware()
    except Exception:
        pass

    try:
        import SpoutGL  # noqa: F401
        from PIL import Image
        import numpy  # noqa: F401
    except Exception as e:
        trace('import failed: %r' % (e,))
        user32.MessageBoxW(None, '缺少依赖：%s\n\n请先运行：pip install SpoutGL pillow numpy' % e,
                           APP, 0x10)
        return 1
    trace('imports ok')

    gl = GLContext()
    trace('gl context ok=%s' % gl.ok)

    state = {'clickthrough': False, 'topmost': True, 'running': True}

    def on_action(cmd, _):
        if cmd == 'moved':
            save_conf(ov)
            return
        if cmd == 1:
            state['clickthrough'] = not state['clickthrough']
            ov.set_clickthrough(state['clickthrough'])
        elif cmd == 2:
            state['topmost'] = not state['topmost']
            ov.set_topmost(state['topmost'])
        elif cmd == 3:
            ov.center()
            save_conf(ov)
        elif cmd == 4:
            state['reconnect'] = True
        elif cmd == 5:
            ov.flip = not ov.flip
            save_conf(ov)
        elif cmd == 9:
            state['running'] = False
            user32.PostMessageW(ov.hwnd, WM_CLOSE, 0, 0)

    ov = Overlay(on_action)
    load_conf(ov)

    src = SpoutSource()
    src.connect(None)

    # tray icon
    nid = NOTIFYICONDATAW()
    nid.cbSize = ctypes.sizeof(NOTIFYICONDATAW)
    nid.hWnd = ov.hwnd
    nid.uID = 1
    nid.uFlags = NIF_MESSAGE | NIF_ICON | NIF_TIP
    nid.uCallbackMessage = WM_TRAY
    nid.hIcon = user32.LoadIconW(None, ctypes.c_void_p(IDI_APPLICATION))
    nid.szTip = 'VSeeFace 桌面角色'
    shell32.Shell_NotifyIconW(NIM_ADD, byref(nid))

    warned = False
    last_ok = time.time()
    last_discover = 0.0
    msg = MSG()
    interval = 1.0 / 30.0
    next_t = time.perf_counter()

    while state['running']:
        # pump messages
        while user32.PeekMessageW(byref(msg), None, 0, 0, 1):
            if msg.message == 0x0012:  # WM_QUIT
                state['running'] = False
                break
            user32.TranslateMessage(byref(msg))
            user32.DispatchMessageW(byref(msg))
        if not state['running']:
            break

        if state.pop('reconnect', False):
            src.disconnect()
            src.connect(None)
            warned = False

        # (re)discover sender
        if src.name is None:
            now = time.time()
            if now - last_discover < 1.0:
                time.sleep(0.01)
                continue
            last_discover = now
            names = src.available()
            target = next((n for n in names if 'vsee' in n.lower()), None)
            if target:
                src.connect(target)
                print('connected:', target)
            elif not warned:
                warned = True
                user32.MessageBoxW(
                    None,
                    '没有检测到 VSeeFace 的 Spout2 输出。\n\n'
                    '请在 VSeeFace 里设置一次：\n'
                    'Settings（设置） -> General（常规）\n'
                    '-> 勾选 "Spout2 Image Capture Support"\n\n'
                    '勾选后本程序会自动连上（无需重启本程序）。',
                    APP, 0x40)
                continue

        frame = src.grab()
        if frame:
            w, h, arr = frame
            try:
                if ov.flip:
                    arr = arr[::-1]
                ov.blit(to_bgra_premultiplied_np(arr), w, h)
                last_ok = time.time()
            except Exception as e:
                print('render error', e)
        else:
            if src.name is not None and time.time() - last_ok > 3:
                # sender lost -> go back to discovery
                if time.time() - last_ok > 6:
                    src.disconnect()

        next_t += interval
        delay = next_t - time.perf_counter()
        if delay > 0:
            time.sleep(delay)
        else:
            next_t = time.perf_counter()

    shell32.Shell_NotifyIconW(NIM_DELETE, byref(nid))
    save_conf(ov)
    src.disconnect()
    ov.destroy()
    return 0


def save_conf(ov):
    try:
        with open(CONF, 'w', encoding='utf-8') as f:
            json.dump({'x': ov.x, 'y': ov.y, 'clickthrough': ov.clickthrough,
                       'flip': ov.flip}, f)
    except Exception:
        pass


def load_conf(ov):
    try:
        with open(CONF, 'r', encoding='utf-8') as f:
            d = json.load(f)
        ov.x = int(d.get('x', ov.x))
        ov.y = int(d.get('y', ov.y))
        ov.flip = bool(d.get('flip', False))
    except Exception:
        ov.need_auto_pos = True
        ov.x = 100
        ov.y = 100


if __name__ == '__main__':
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except BaseException:
        import traceback
        trace('FATAL:\n' + traceback.format_exc())
        try:
            user32.MessageBoxW(None, '程序启动失败，详情见 vsf_debug.log', APP, 0x10)
        except Exception:
            pass
        sys.exit(1)
