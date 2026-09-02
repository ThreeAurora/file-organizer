import os
import sys
import json
import calendar
import ctypes
import subprocess
import threading
import time
import shutil
import tkinter as tk
from tkinterdnd2 import DND_FILES, TkinterDnD
from tkinter import messagebox, filedialog, colorchooser, simpledialog

# ============================================================
# 高 DPI 适配（4K 屏等）
# ============================================================
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)  # 逐显示器感知
except:
    try:
        ctypes.windll.user32.SetProcessDPIAware()    # 旧版 API 兜底
    except:
        pass

# -- 标题栏永不灰化（拦截 WM_NCACTIVATE，始终按激活态绘制） --
_titlebar_hooks = {}  # 防 GC

def _get_top_hwnd(widget):
    """从 tkinter widget 获取顶层窗口 HWND"""
    try:
        wid = widget.winfo_id()
        # 先取根祖先，拿到真正带标题栏的顶层窗口
        hwnd = ctypes.windll.user32.GetAncestor(wid, 2)  # GA_ROOT=2
        if hwnd:
            return hwnd
    except:
        pass
    return None

def keep_titlebar_active(hwnd):
    """让窗口标题栏始终显示为激活态，焦点离开也不变灰"""
    if not hwnd:
        return
    try:
        user32 = ctypes.windll.user32
        GWLP_WNDPROC = -4
        WM_NCACTIVATE = 0x0086

        WNDPROC_T = ctypes.WINFUNCTYPE(
            ctypes.c_longlong, ctypes.c_void_p, ctypes.c_uint,
            ctypes.c_ulonglong, ctypes.c_longlong)

        user32.CallWindowProcW.argtypes = [
            ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint,
            ctypes.c_ulonglong, ctypes.c_longlong]
        user32.CallWindowProcW.restype = ctypes.c_longlong
        user32.SetWindowLongPtrW.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p]
        user32.SetWindowLongPtrW.restype = ctypes.c_void_p

        def new_wndproc(h, msg, wp, lp):
            if msg == WM_NCACTIVATE:
                wp = 1
            return user32.CallWindowProcW(old_proc, h, msg, wp, lp)

        callback = WNDPROC_T(new_wndproc)
        _titlebar_hooks[id(callback)] = callback
        old_proc = user32.SetWindowLongPtrW(
            ctypes.c_void_p(hwnd), GWLP_WNDPROC,
            ctypes.cast(callback, ctypes.c_void_p))
        _titlebar_hooks[hwnd] = old_proc
    except:
        pass

# ============================================================
# 配置区
# ============================================================

# -- 默认九个目标文件夹（名称、路径、颜色） --
DEFAULT_ZONES = [
    {"name": "文件夹 1", "path": "", "color": "#0d9488"},
    {"name": "文件夹 2", "path": "", "color": "#0d9488"},
    {"name": "文件夹 3", "path": "", "color": "#0d9488"},
    {"name": "文件夹 4", "path": "", "color": "#0d9488"},
    {"name": "文件夹 5", "path": "", "color": "#0d9488"},
    {"name": "文件夹 6", "path": "", "color": "#0d9488"},
    {"name": "文件夹 7", "path": "", "color": "#0d9488"},
    {"name": "文件夹 8", "path": "", "color": "#0d9488"},
    {"name": "文件夹 9", "path": "", "color": "#0d9488"},
]

# 配置文件路径（%APPDATA%/文件归档器/config.json）
CONFIG_PATH = os.path.join(os.environ.get('APPDATA', ''), '文件归档器', 'config.json')



def load_config():
    """加载配置，文件不存在则返回空白默认"""
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        zones = data.get('zones', [])
        if zones and len(zones) == 9:
            return zones
    except:
        pass
    return [dict(z) for z in DEFAULT_ZONES]


def load_settings():
    """加载开关状态，文件不存在返回默认"""
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        s = data.get('settings', {})
        return {
            'use_copy': s.get('use_copy', False),
            'use_day': s.get('use_day', True),
            'use_ctime': s.get('use_ctime', False),
            'is_topmost': s.get('is_topmost', True),
            'use_year_mode': s.get('use_year_mode', False),
            'use_everything': s.get('use_everything', False),
            'ev_path': s.get('ev_path', DEFAULT_EV_PATH),
        }
    except:
        pass
    return {'use_copy': False, 'use_day': True, 'use_ctime': False, 'is_topmost': True, 'use_year_mode': False, 'use_everything': False, 'ev_path': DEFAULT_EV_PATH}


def save_all():
    """保存所有配置：区域 + 窗口 + 通用颜色 + 开关状态"""
    try:
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
        else:
            data = {}
        data['zones'] = ZONE_CONFIGS
        data['window'] = {
            'x': root.winfo_x(), 'y': root.winfo_y(),
            'width': root.winfo_width(), 'height': root.winfo_height()
        }
        data['general_color'] = gen_color
        data['settings'] = {
            'use_copy': use_copy,
            'use_day': use_day,
            'use_ctime': use_ctime,
            'is_topmost': is_topmost,
            'use_year_mode': use_year_mode,
            'use_everything': use_everything,
            'ev_path': ev_path,
        }
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        messagebox.showerror("保存失败", f"无法写入配置文件：\n{e}")
        return False


# 当前生效的配置
ZONE_CONFIGS = load_config()


def load_window_state():
    """读取窗口位置/大小，首次启动返回 None"""
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        w = data.get('window', {})
        if w:
            return (w.get('x'), w.get('y'),
                    w.get('width', WINDOW_W), w.get('height', WINDOW_H))
    except:
        pass
    return None


_save_timer = None

def save_window_state():
    """将当前窗口位置/大小写入配置文件（复用 save_all）"""
    save_all()


def on_configure(event):
    """窗口移动/缩放时延迟保存状态"""
    global _save_timer
    if event.widget != root:
        return
    if _save_timer:
        root.after_cancel(_save_timer)
    _save_timer = root.after(1500, save_window_state)


def on_close():
    """退出前保存窗口状态"""
    save_window_state()
    save_all()
    root.destroy()


DEFAULT_EV_PATH = ""

def _open_folder(path):
    """根据 use_everything 选择打开方式"""
    if use_everything and ev_path and os.path.isfile(ev_path):
        subprocess.Popen([ev_path, "-s", path],
                         creationflags=subprocess.CREATE_NO_WINDOW)
        return
    os.startfile(path)


def _auto_find_ev():
    """自动查找 Everything，返回路径或 None"""
    import winreg
    candidates = [
        r"E:\Everything\Everything.exe",
        r"C:\Program Files\Everything\Everything.exe",
        r"C:\Program Files (x86)\Everything\Everything.exe",
    ]
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                            r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\Everything.exe") as key:
            candidates.insert(0, winreg.QueryValue(key, None))
    except:
        pass
    for p in candidates:
        if os.path.isfile(p):
            return p
    return None


def _do_ev_select():
    """手动选择 Everything.exe"""
    global ev_path
    p = filedialog.askopenfilename(
        title="选择 Everything.exe",
        filetypes=[("Everything.exe", "Everything.exe"), ("可执行文件", "*.exe")])
    if p and os.path.isfile(p):
        ev_path = p
        save_all()


def _do_ev_find():
    """自动查找 Everything.exe"""
    global ev_path
    old = ev_path
    found = _auto_find_ev()
    if found:
        ev_path = found
        save_all()
        if old:
            _show_toast(ev_btn, f"已匹配到路径：{found}")
        else:
            _show_toast(ev_btn, "已找到 Everything")
    else:
        _show_toast(ev_btn, "未找到，请手动选择")


def darken(hex_color):
    """将 hex 颜色变暗 15%"""
    h = hex_color.lstrip('#')
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    r, g, b = int(r * 0.85), int(g * 0.85), int(b * 0.85)
    return f"#{r:02x}{g:02x}{b:02x}"

# -- 配色（浅色主题） --
WINDOW_BG = "#f1f5f9"
TEXT_MAIN = "#1e293b"
TEXT_MUTED = "#64748b"
GENERAL_COLOR = "#3b82f6"

# 控制栏
CTRL_BG = "#f8fafc"
SEG_TRACK = "#e2e8f0"
SEG_BORDER = "#cbd5e1"
SEG_SEL_BG = "#f8fafc"
SEG_SEL_FG = TEXT_MAIN
SEG_UNSEL_BG = "#e2e8f0"
SEG_UNSEL_FG = "#64748b"

# -- 窗口 --
WINDOW_W = 580
WINDOW_H = 560

# -- 字体 --
FONT_ZONE   = ("Microsoft YaHei", 11, "bold")
FONT_GENERAL = ("Microsoft YaHei", 13, "bold")
FONT_CTRL   = ("Microsoft YaHei", 10)

# ============================================================
# 全局状态
# ============================================================
is_processing = False
use_ctime = False
use_day = True
use_copy = False
use_year_mode = False
year_start = 0  # 那年今日模式下显示的第一个年份
_year_zone_idx = 0  # 那年今日绑定的文件夹索引
_year_picked = 0  # 那年今日中最后操作过的年份
use_everything = False  # 用 Everything 打开路径
ev_path = DEFAULT_EV_PATH  # Everything.exe 路径

# 弹窗单例引用（避免重复打开）
_settings_win = None
_help_win = None

zone_meta = {}
zone_widgets = []  # 存储 (zone_idx, sv_var, lbl) 用于设置后刷新界面


# ============================================================
# 核心逻辑
# ============================================================

def get_target_info(path, base_dir=None, override_ts=None):
    try:
        if override_ts:
            dt = time.localtime(override_ts)
        else:
            stat_result = os.stat(path)
            timestamp = stat_result.st_ctime if use_ctime else stat_result.st_mtime
            dt = time.localtime(timestamp)

        year_str = str(dt.tm_year)
        month_str = f"{dt.tm_mon:02d}"

        if base_dir is None:
            base_dir = os.path.dirname(path)

        if use_day:
            day_str = f"{year_str}-{month_str}-{dt.tm_mday:02d}"
            target_dir = os.path.join(base_dir, year_str, month_str, day_str)
        else:
            target_dir = os.path.join(base_dir, year_str, month_str)

        target_abs = os.path.abspath(target_dir)
        if os.path.abspath(path).startswith(target_abs):
            return None, None

        return target_dir, os.path.basename(path)
    except:
        return None, None


def move_worker(item_list, status_var, label, root_window, base_dir=None, override_ts=None):
    global is_processing
    total = len(item_list)
    created_dirs = set()

    for i, item_path in enumerate(item_list):
        if i % 50 == 0 or i == total - 1:
            percent = int(((i + 1) / total) * 100)
            status_var.set(f"{percent}%\n{i+1}/{total}")

        try:
            target_dir, name = get_target_info(item_path, base_dir, override_ts)
            if not target_dir:
                continue

            if target_dir not in created_dirs:
                os.makedirs(target_dir, exist_ok=True)
                created_dirs.add(target_dir)

            destination = os.path.join(target_dir, name)

            if os.path.normpath(item_path) == os.path.normpath(destination):
                continue

            root_name, ext = os.path.splitext(name)
            if os.path.isdir(item_path) and not ext:
                c = 1
                final_dest = destination
                while os.path.exists(final_dest):
                    final_dest = os.path.join(target_dir, f"{name}_{c}")
                    c += 1
            else:
                c = 1
                final_dest = destination
                while os.path.exists(final_dest):
                    final_dest = os.path.join(target_dir, f"{root_name}_{c}{ext}")
                    c += 1

            if use_copy:
                if os.path.isdir(item_path):
                    shutil.copytree(item_path, final_dest)
                else:
                    shutil.copy2(item_path, final_dest)
            else:
                shutil.move(item_path, final_dest)
        except Exception as e:
            print(f"Error moving {item_path}: {e}")

    meta = zone_meta.get(label, {"color": label.cget("bg"), "text": "..."})
    root_window.after(800, lambda: (
        status_var.set(meta["text"]),
        label.config(bg=meta["color"])
    ))
    is_processing = False


# ============================================================
# 拖放处理
# ============================================================

def make_zone_handler(zid, status_var, label, label_text):
    def handler(file_list):
        global is_processing
        if is_processing:
            return
        # 兼容 tkinterdnd2 event 对象和纯 list
        if not isinstance(file_list, list):
            try:
                file_list = root.tk.splitlist(file_list.data)
            except:
                return
        item_list = [p for p in file_list if os.path.exists(p)]
        if not item_list:
            return

        base_dir = ZONE_CONFIGS[zid]["path"]
        override_ts = None
        if _year_ui_active:
            # 那年今日模式：使用进入时所点文件夹的路径
            base_dir = ZONE_CONFIGS[_year_zone_idx]["path"]
            try:
                global _year_picked
                yr = int(status_var.get())
                _year_picked = yr
            except:
                yr = None
            if yr:
                today = time.localtime()
                override_dt = (yr, today.tm_mon, today.tm_mday,
                               today.tm_hour, today.tm_min, today.tm_sec,
                               today.tm_wday, today.tm_yday, today.tm_isdst)
                override_ts = time.mktime(override_dt)

        label.config(bg="orange")

        def run():
            global is_processing
            is_processing = True
            move_worker(item_list, status_var, label, root, base_dir, override_ts)

        threading.Thread(target=run, daemon=True).start()

    return handler


def make_general_handler(status_var, label):
    def handler(file_list):
        global is_processing
        if is_processing:
            return
        if not isinstance(file_list, list):
            try:
                file_list = root.tk.splitlist(file_list.data)
            except:
                return
        item_list = [p for p in file_list if os.path.exists(p)]
        if not item_list:
            return

        label.config(bg="orange")

        def run():
            global is_processing
            is_processing = True
            move_worker(item_list, status_var, label, root, base_dir=None)

        threading.Thread(target=run, daemon=True).start()

    return handler


def _show_toast(widget, text):
    """浅色浮动提示，短暂显示后消失"""
    toast = tk.Toplevel(root)
    toast.overrideredirect(True)
    toast.attributes("-topmost", True)
    tk.Label(toast, text=text, bg="#334155", fg="#f1f5f9",
             font=("Microsoft YaHei", 9), padx=14, pady=5).pack()
    toast.update_idletasks()
    x = widget.winfo_rootx() + (widget.winfo_width() - toast.winfo_width()) // 2
    y = widget.winfo_rooty() + widget.winfo_height() + 6
    toast.geometry(f"+{x}+{y}")
    toast.after(400, toast.destroy)


def make_zone_menu(zid, sv_var, lbl_widget):
    """右键菜单工厂（那年今日模式下无菜单）"""
    def show(e):
        if _year_ui_active:
            return
        cfg_dict = ZONE_CONFIGS[zid]
        menu = tk.Menu(root, tearoff=0)
        if cfg_dict["path"]:
            menu.add_command(label="修改名称", command=lambda: rename_zone(cfg_dict, sv_var, lbl_widget))
            menu.add_command(label="重新选择路径", command=lambda: reselect_path(cfg_dict, sv_var, lbl_widget))
            menu.add_separator()
        menu.add_command(label="配置颜色", command=lambda: pick_zone_color(cfg_dict, lbl_widget))
        menu.post(e.x_root, e.y_root)
    return show


def make_open_cb(zid, sv_var, lbl_widget):
    """点击回调工厂（模块级，zid 为 ZONE_CONFIGS 索引）"""
    def cb(e):
        if is_processing:
            return
        if _year_ui_active:
            # 年份九宫格中，使用进入时所点文件夹的路径
            cfg_dict = ZONE_CONFIGS[_year_zone_idx]
            if not cfg_dict["path"]:
                d = filedialog.askdirectory(title="选择目标文件夹")
                if d:
                    cfg_dict["path"] = d.replace("\\", "/") + "/"
                    cfg_dict["name"] = os.path.basename(d)
                    save_all()
                return
            try:
                global _year_picked
                yr = int(sv_var.get())
                _year_picked = yr
            except:
                return
            today = time.localtime()
            target = os.path.join(cfg_dict["path"],
                str(yr), f"{today.tm_mon:02d}", f"{yr}-{today.tm_mon:02d}-{today.tm_mday:02d}")
            if os.path.exists(target):
                _open_folder(target)
            else:
                _show_toast(lbl_widget, "路径不存在")
            return
        cfg_dict = ZONE_CONFIGS[zid]
        if use_year_mode and not _year_ui_active:
            # 那年今日已选中但未激活 → 无路径先选路径，再进入
            if not cfg_dict["path"]:
                d = filedialog.askdirectory(title="选择目标文件夹")
                if d:
                    cfg_dict["path"] = d.replace("\\", "/") + "/"
                    cfg_dict["name"] = os.path.basename(d)
                    save_all()
                else:
                    return
            _enter_year_mode(zid)
            return
        p = cfg_dict["path"]
        if not p:
            d = filedialog.askdirectory(title="选择目标文件夹")
            if d:
                cfg_dict["path"] = d.replace("\\", "/") + "/"
                cfg_dict["name"] = os.path.basename(d)
                sv_var.set(cfg_dict["name"])
                zone_meta[lbl_widget] = {"color": cfg_dict["color"], "text": cfg_dict["name"]}
                save_all()
        elif os.path.exists(p):
            _open_folder(p)
        else:
            messagebox.showwarning("路径不存在", "路径不存在，请检查路径设置！")
    return cb


def update_year_mode_ui():
    """根据 _year_ui_active 切换显示（只改文字颜色，不动 widget 结构）"""
    current_year = time.localtime().tm_year
    if _year_ui_active:
        time_mod_frame.pack_forget()
        time_create_frame.pack_forget()
        gen_frame.grid_remove()
        year_ctrl_frame.grid()
        new_day_btn.pack(side="left", ipady=2, padx=(4, 4), after=topmost_btn)
        new_month_btn.pack(side="left", ipady=2, padx=(4, 4), after=new_day_btn)
        for i, (zid, sv, lbl) in enumerate(zone_widgets):
            yr = year_start + i
            sv.set(str(yr))
            lbl.config(bg="#0d9488")
            lbl.master.config(bg="#0d9488")
            zone_meta[lbl] = {"color": "#0d9488", "text": str(yr)}
        _update_flip_btns()
    else:
        time_mod_frame.pack(side="left", padx=0, before=copy_btn)
        time_create_frame.pack(side="left", padx=0, before=ev_frame)
        new_day_btn.pack_forget()
        new_month_btn.pack_forget()
        year_ctrl_frame.grid_remove()
        gen_frame.grid()
        for i, (zid, sv, lbl) in enumerate(zone_widgets):
            cg = ZONE_CONFIGS[zid]
            c = cg["color"]
            sv.set(cg["name"] if cg["path"] else "请选择路径")
            lbl.config(bg=c)
            lbl.master.config(bg=c)
            zone_meta[lbl] = {"color": c, "text": cg["name"]}


# ============================================================
# 控制按钮回调
# ============================================================

def set_time_mode(ctime):
    global use_ctime
    if is_processing:
        return
    use_ctime = ctime
    if ctime:
        btn_create.config(bg=SEG_SEL_BG, fg=SEG_SEL_FG)
        btn_modify.config(bg=SEG_UNSEL_BG, fg=SEG_UNSEL_FG)
    else:
        btn_modify.config(bg=SEG_SEL_BG, fg=SEG_SEL_FG)
        btn_create.config(bg=SEG_UNSEL_BG, fg=SEG_UNSEL_FG)
    save_all()


def toggle_day_mode():
    global use_day
    if is_processing:
        return
    use_day = not use_day
    day_btn.config(text="☑ 具体到日" if use_day else "☐ 具体到日")
    save_all()


def toggle_copy_mode():
    global use_copy
    if is_processing:
        return
    use_copy = not use_copy
    copy_btn.config(text="☑ 仅复制" if use_copy else "☐ 仅复制")
    save_all()


def toggle_year_mode():
    global use_year_mode, year_start
    if is_processing:
        return
    use_year_mode = not use_year_mode
    if use_year_mode:
        year_start = time.localtime().tm_year - 8
    else:
        # 关闭那年今日时，如果在 year 模式则退出
        if _year_ui_active:
            _exit_year_mode()
    year_btn.config(text="☑ 那年今日" if use_year_mode else "☐ 那年今日")
    save_all()


def toggle_everything():
    global use_everything
    if is_processing:
        return
    use_everything = not use_everything
    ev_btn.config(text="☑ Everything" if use_everything else "☐ Everything")
    save_all()
    save_all()


_year_ui_active = False  # 那年今日界面是否已激活


def _enter_year_mode(zid):
    """那年今日开关点了之后，再点九宫格才进入，zid 为点击的格子索引"""
    global _year_ui_active, _year_zone_idx, _year_picked
    _year_zone_idx = zid
    _year_ui_active = True
    _year_picked = time.localtime().tm_year
    update_year_mode_ui()


def _exit_year_mode():
    global _year_ui_active
    _year_ui_active = False
    update_year_mode_ui()


def _create_year_today():
    """新建今天：在年份格子对应文件夹下创建那年今天的目录"""
    cfg = ZONE_CONFIGS[_year_zone_idx]
    if not cfg["path"]:
        _show_toast(day_btn, "未配置路径")
        return
    today = time.localtime()
    yr = _year_picked or time.localtime().tm_year
    target = os.path.join(cfg["path"],
        str(yr), f"{today.tm_mon:02d}", f"{yr}-{today.tm_mon:02d}-{today.tm_mday:02d}")
    existed = os.path.isdir(target)
    os.makedirs(target, exist_ok=True)
    _show_toast(new_day_btn, "已创建" if not existed else "已存在")


def _create_year_month():
    """新建本月：创建该年该月全部日期文件夹"""
    cfg = ZONE_CONFIGS[_year_zone_idx]
    if not cfg["path"]:
        _show_toast(day_btn, "未配置路径")
        return
    today = time.localtime()
    yr = _year_picked or time.localtime().tm_year
    mo = today.tm_mon
    _, days = calendar.monthrange(yr, mo)
    base = os.path.join(cfg["path"], str(yr), f"{mo:02d}")
    created = 0
    for d in range(1, days + 1):
        target = os.path.join(base, f"{yr}-{mo:02d}-{d:02d}")
        if not os.path.isdir(target):
            os.makedirs(target, exist_ok=True)
            created += 1
    if created:
        _show_toast(new_month_btn, f"已创建 {created} 个文件夹")
    else:
        _show_toast(new_month_btn, "全部已存在")


def _update_flip_btns():
    """根据 year_start 禁用/启用来回翻页按钮"""
    cur = time.localtime().tm_year
    if year_start <= 1900:
        left_btn.config(state="disabled", fg=TEXT_MUTED)
    else:
        left_btn.config(state="normal", fg=TEXT_MAIN)
    if year_start >= cur - 8:
        right_btn.config(state="disabled", fg=TEXT_MUTED)
    else:
        right_btn.config(state="normal", fg=TEXT_MAIN)


def _year_flip(delta):
    """翻页：delta 为正则往后翻，为负则往前翻"""
    global year_start
    year_start += delta
    current_year = time.localtime().tm_year
    year_start = max(1900, min(year_start, current_year - 8))
    for i, (zid, sv, lbl) in enumerate(zone_widgets):
        yr = year_start + i
        sv.set(str(yr))
        zone_meta[lbl] = {"color": "#0d9488", "text": str(yr)}
    _update_flip_btns()


def pick_zone_color(cfg_dict, lbl_widget):
    """右键：配置区域颜色"""
    result = colorchooser.askcolor(color=cfg_dict["color"], title="选择颜色")
    if result[1]:
        cfg_dict["color"] = result[1]
        lbl_widget.config(bg=result[1])
        # 更新所属 frame 的背景
        lbl_widget.master.config(bg=result[1])
        zone_meta[lbl_widget] = {"color": result[1], "text": cfg_dict["name"]}
        save_all()


def rename_zone(cfg_dict, sv_var, lbl_widget):
    """右键：修改区域名称"""
    new_name = simpledialog.askstring("修改名称", "输入新名称：",
                                      initialvalue=cfg_dict["name"])
    if new_name and new_name.strip():
        cfg_dict["name"] = new_name.strip()
        sv_var.set(cfg_dict["name"])
        zone_meta[lbl_widget] = {"color": cfg_dict["color"], "text": cfg_dict["name"]}
        save_all()


def reselect_path(cfg_dict, sv_var, lbl_widget):
    """右键：重新选择路径"""
    d = filedialog.askdirectory(title="选择目标文件夹",
                                initialdir=cfg_dict["path"] if os.path.exists(cfg_dict["path"]) else None)
    if d:
        cfg_dict["path"] = d.replace("\\", "/") + "/"
        cfg_dict["name"] = os.path.basename(d)
        sv_var.set(cfg_dict["name"])
        zone_meta[lbl_widget] = {"color": cfg_dict["color"], "text": cfg_dict["name"]}
        save_all()


# ============================================================
# 设置对话框
# ============================================================

def open_settings():
    global _settings_win
    if _settings_win and _settings_win.winfo_exists():
        _settings_win.lift()
        _settings_win.focus_force()
        return

    _settings_win = tk.Toplevel(root)
    settings_win = _settings_win
    settings_win.title("设置 - 目标文件夹")
    settings_win.geometry("580x490")
    settings_win.resizable(False, False)
    settings_win.configure(bg="#f8fafc")
    settings_win.transient(root)
    settings_win.grab_set()

    def on_destroy():
        global _settings_win
        _settings_win = None
        settings_win.destroy()
    settings_win.protocol("WM_DELETE_WINDOW", on_destroy)

    settings_win.update()
    keep_titlebar_active(_get_top_hwnd(settings_win))
    x = root.winfo_x() + (root.winfo_width() - 580) // 2
    y = root.winfo_y() + (root.winfo_height() - 490) // 2
    settings_win.geometry(f"+{x}+{y}")

    header = tk.Frame(settings_win, bg=WINDOW_BG, height=40)
    header.pack(fill="x", side="top")
    header.pack_propagate(False)
    tk.Label(header, text="设置目标文件夹", bg=WINDOW_BG, fg="#000000",
             font=("Microsoft YaHei", 11, "bold")).pack(side="left", padx=12, pady=6)

    cols = tk.Frame(settings_win, bg="#f8fafc")
    cols.pack(fill="x", padx=12, pady=(10, 2))
    tk.Label(cols, text="颜色", bg="#f8fafc", fg=TEXT_MAIN,
             font=("Microsoft YaHei", 8), width=3, anchor="w").pack(side="left", padx=(0, 6))
    tk.Label(cols, text="名称", bg="#f8fafc", fg=TEXT_MAIN,
             font=("Microsoft YaHei", 8), width=12, anchor="w").pack(side="left", padx=(0, 6))
    tk.Label(cols, text="路径", bg="#f8fafc", fg=TEXT_MAIN,
             font=("Microsoft YaHei", 8), width=30, anchor="w").pack(side="left", padx=(0, 6))
    tk.Label(cols, text="选择路径", bg="#f8fafc", fg=TEXT_MAIN,
             font=("Microsoft YaHei", 8)).pack(side="left")

    entries = []
    for i, zone in enumerate(ZONE_CONFIGS):
        row = tk.Frame(settings_win, bg="#f8fafc")
        row.pack(fill="x", padx=12, pady=3)

        current_color = tk.StringVar(value=zone["color"])

        color_btn = tk.Button(row, text="", bg=zone["color"], width=3,
                              relief="flat", cursor="hand2", bd=0,
                              activebackground=zone["color"])
        color_btn.pack(side="left", padx=(0, 6))

        def make_pick_cb(cv, cb):
            def pick():
                result = colorchooser.askcolor(color=cv.get(), title="选择颜色")
                if result[1]:
                    cv.set(result[1])
                    cb.config(bg=result[1])
            return pick
        color_btn.config(command=make_pick_cb(current_color, color_btn))

        name_var = tk.StringVar(value=zone["name"])
        name_entry = tk.Entry(row, textvariable=name_var, width=12,
                              font=("Microsoft YaHei", 9),
                              bg="white", fg=TEXT_MAIN, insertbackground=TEXT_MAIN,
                              relief="flat", bd=0, highlightbackground="#cbd5e1",
                              highlightthickness=1)
        name_entry.pack(side="left", padx=(0, 6))

        path_var = tk.StringVar(value=zone["path"])
        path_entry = tk.Entry(row, textvariable=path_var, width=30,
                              font=("Microsoft YaHei", 9),
                              bg="white", fg=TEXT_MAIN, insertbackground=TEXT_MAIN,
                              relief="flat", bd=0, highlightbackground="#cbd5e1",
                              highlightthickness=1)
        path_entry.pack(side="left", padx=(0, 4))

        def browse(pe=path_entry, nv=name_var):
            d = filedialog.askdirectory(title="选择目标文件夹")
            if d:
                pe.delete(0, "end")
                pe.insert(0, d.replace("\\", "/") + "/")
                nv.delete(0, "end")
                nv.insert(0, os.path.basename(d))

        browse_btn = tk.Button(row, text="…", bg="#e2e8f0", fg=TEXT_MAIN,
                               font=("Microsoft YaHei", 9), relief="flat",
                               cursor="hand2", bd=0, padx=6,
                               activebackground="#cbd5e1", activeforeground=TEXT_MAIN,
                               command=browse)
        browse_btn.pack(side="left")

        entries.append((name_var, path_var, current_color))

    btn_row = tk.Frame(settings_win, bg="#f8fafc")
    btn_row.pack(side="bottom", fill="x", padx=12, pady=12)

    def do_save():
        new_zones = []
        for i, (nv, pv, cv) in enumerate(entries):
            name = nv.get().strip()
            path = pv.get().strip()
            color = cv.get().strip()
            if not name or not path:
                messagebox.showwarning("未填完整", f"第 {i+1} 项名称或路径为空，请补全。",
                                       parent=settings_win)
                return
            new_zones.append({"name": name, "path": path, "color": color})

        if save_all():
            # 更新内存配置
            ZONE_CONFIGS[:] = new_zones
            # 即时刷新界面上的区域名称（zone_widgets 存的是 index，查 ZONE_CONFIGS）
            for zid, sv_var, lbl_w in zone_widgets:
                cg = ZONE_CONFIGS[zid]
                sv_var.set(cg["name"] if cg["path"] else "请选择路径")
                zone_meta[lbl_w] = {"color": cg["color"], "text": cg["name"]}
            messagebox.showinfo("已保存", "配置已保存。", parent=settings_win)
            on_destroy()

    tk.Button(btn_row, text="取消", bg="#e2e8f0", fg=TEXT_MAIN,
              font=("Microsoft YaHei", 9), relief="flat", cursor="hand2",
              activebackground="#cbd5e1", activeforeground=TEXT_MAIN,
              command=on_destroy, padx=20, ipady=2).pack(side="right", padx=(8, 0))
    tk.Button(btn_row, text="保存", bg="#3b82f6", fg="white",
              font=("Microsoft YaHei", 9), relief="flat", cursor="hand2",
              activebackground="#2563eb", activeforeground="white",
              command=do_save, padx=20, ipady=2).pack(side="right")


# ============================================================
# 帮助
# ============================================================

def show_help():
    """自定义帮助窗口——无系统提示音，现代设计"""
    global _help_win
    if _help_win and _help_win.winfo_exists():
        _help_win.lift()
        _help_win.focus_force()
        return

    _help_win = tk.Toplevel(root)
    hw = _help_win
    hw.title("使用手册")
    hw.geometry("780x550")
    hw.resizable(False, False)
    hw.configure(bg="white")
    hw.transient(root)

    def on_destroy():
        global _help_win
        _help_win = None
        hw.destroy()
    hw.protocol("WM_DELETE_WINDOW", on_destroy)

    hw.update_idletasks()
    hw.update()
    keep_titlebar_active(_get_top_hwnd(hw))
    x = root.winfo_x() + (root.winfo_width() - 780) // 2
    y = root.winfo_y() + (root.winfo_height() - 550) // 2
    hw.geometry(f"+{x}+{y}")

    # 标题
    tk.Label(hw, text="文件归档器 by 简单", bg="white", fg="#000000",
             font=("Microsoft YaHei", 16, "bold")).pack(pady=(14, 0))
    tk.Label(hw, text="按时间自动归类文件", bg="white", fg="#475569",
             font=("Microsoft YaHei", 11)).pack(pady=(0, 8))

    # 分隔线
    tk.Frame(hw, bg="#e2e8f0", height=1).pack(fill="x", padx=20)

    def _add_card(parent, title, body):
        card = tk.Frame(parent, bg="white")
        bar = tk.Frame(card, bg="#3b82f6", width=3)
        bar.pack(side="left", fill="y", padx=(0, 8))
        tk.Label(card, text=title, bg="white", fg="#1e293b",
                 font=("Microsoft YaHei", 12, "bold"), anchor="w",
                 justify="left").pack(anchor="w")
        tk.Label(card, text=body, bg="white", fg="#475569",
                 font=("Microsoft YaHei", 10), anchor="w",
                 justify="left").pack(anchor="w", pady=(2, 0))
        return card

    cols = tk.Frame(hw, bg="white")
    cols.pack(fill="both", expand=True, padx=16, pady=(6, 0))
    cols.columnconfigure(0, weight=1)
    cols.columnconfigure(1, weight=1)

    # 一句话跨两列
    _add_card(cols, "一句话",
              "按照文件的修改或创建时间（文件夹也行），自动归类到\n"
              "年/月/ 或 年/月/日/ 文件夹中。").grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 8))

    # 左列
    L = tk.Frame(cols, bg="white")
    L.grid(row=1, column=0, sticky="new", padx=(0, 8))
    _add_card(L, "怎么用",
              "拖放文件到上方九宫格 → 归档到对应文件夹\n"
              "拖放到「通用整理」→ 在原位置归档\n"
              "点击格子 → 打开文件夹（未配置则选择路径）\n"
              "右键格子 → 修改名称 / 重新选择路径 / 配置颜色").pack(fill="x", pady=(0, 8))
    _add_card(L, "底部选项",
              "第一排：仅复制 / 那年今日 / 具体到日 / 修改·创建时间\n"
              "第二排：置顶窗口 / Everything\n"
              "☑ 仅复制 → 复制文件（关闭后为移动文件）\n"
              "☑ 那年今日 → 见右侧那年今日说明\n"
              "☑ 具体到日 → 例：开启后归档到 2026/07/2026-07-01\n"
              "    关闭则只到 2026/07\n"
              "☑ 置顶窗口 → 窗口始终在最前\n"
              "☑ Everything → 点击格子后在 Everything 中搜索路径\n"
              "    （点「选择路径」或「自动查找」配置 Everything）").pack(fill="x")

    # 右列
    R = tk.Frame(cols, bg="white")
    R.grid(row=1, column=1, sticky="new", padx=(8, 0))
    _add_card(R, "那年今日",
              "☑ 那年今日 → 点击九宫格进入「年份九宫格」\n"
              "（展示近 9 年，如 2018-2026），可翻页\n"
              "拖文件到某年即归档至那年的今天\n"
              "例：今日 7/1，拖入「2018」→\n"
              "归档到 文件夹A/2018/07/2018-07-01\n"
              "「新建今天」→ 在当前文件夹下创建今天的日期文件夹\n"
              "「新建本月」→ 在当前文件夹下批量创建本月全部日期\n"
              "（已存在的日期自动跳过）").pack(fill="x", pady=(0, 8))
    _add_card(R, "题外话",
              "我有整理爱好，但文件数量达百万级，我无从下手\n"
              "所以它诞生了——简洁、极速\n"
              "我按时间归类文件，每天只整理那年今日，明确而有趣\n").pack(fill="x")

    tk.Button(hw, text="知道了", bg="#3b82f6", fg="white",
              font=("Microsoft YaHei", 11), relief="flat", cursor="hand2",
              activebackground="#2563eb", activeforeground="white",
              command=on_destroy, padx=30, ipady=3).pack(pady=(8, 10))


# ============================================================
# 启动
# ============================================================

try:
    root = TkinterDnD.Tk()
except:
    root = tk.Tk()

root.title("文件归档器")
root.attributes("-topmost", True)
win_state = load_window_state()
sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
if win_state:
    wx, wy, ww, wh = win_state
    # 防止窗口超出屏幕（比如换了显示器）
    wx = max(0, min(wx, sw - 200))
    wy = max(0, min(wy, sh - 200))
    ww = min(ww, sw)
    wh = min(wh, sh)
else:
    ww, wh = WINDOW_W, WINDOW_H
    if sw < 800 or sh < 600:
        ww, wh = min(ww, sw - 40), min(wh, sh - 80)
    wx = (sw - ww) // 2
    wy = (sh - wh) // 2
root.geometry(f"{ww}x{wh}+{wx}+{wy}")
root.configure(bg=WINDOW_BG)
root.bind('<Configure>', on_configure)
root.protocol("WM_DELETE_WINDOW", on_close)

try:
    if getattr(sys, 'frozen', False):
        ico = sys.executable
    else:
        ico = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'icon.ico')
    root.iconbitmap(default=ico)
except:
    pass

root.update()
root_hwnd = _get_top_hwnd(root)
keep_titlebar_active(root_hwnd)
# 注册原生 WM_DROPFILES，绕开 tkinterdnd2 的缓冲区限制
ctypes.windll.shell32.DragAcceptFiles(root_hwnd, True)
ex = ctypes.windll.user32.GetWindowLongPtrW(root_hwnd, -20)
ctypes.windll.user32.SetWindowLongPtrW(root_hwnd, -20, ex | 0x10)

# ---- 主网格容器 ----
main = tk.Frame(root, bg=WINDOW_BG)
main.pack(fill="both", expand=True, padx=5, pady=5)
for c in range(3):
    main.columnconfigure(c, weight=1, uniform="col")
for r in range(5):
    main.rowconfigure(r, weight=1 if r < 4 else 0)

# ---- 九个文件夹区域 (3 列 × 3 行) ----
for idx, cfg in enumerate(ZONE_CONFIGS):
    row, col = divmod(idx, 3)

    frame = tk.Frame(main, bg=cfg["color"], bd=1, relief="raised")
    frame.grid(row=row, column=col, padx=2, pady=2, sticky="nsew")

    display_text = cfg["name"] if cfg["path"] else "请选择路径"
    sv = tk.StringVar(value=display_text)
    lbl = tk.Label(frame, textvariable=sv, bg=cfg["color"], fg="white",
                   font=FONT_ZONE, cursor="hand2", wraplength=130)
    lbl.pack(fill="both", expand=True)

    handler = make_zone_handler(idx, sv, lbl, cfg["name"])
    for w in (lbl, frame):
        w.drop_target_register(DND_FILES)
        w.dnd_bind('<<Drop>>', handler)

    def mk_enter(l=lbl, f=frame, c=cfg):
        def fn(e):
            if not is_processing:
                clr = "#0d9488" if _year_ui_active else c["color"]
                h = darken(clr)
                l.config(bg=h)
                f.config(bg=h)
        return fn
    def mk_leave(l=lbl, f=frame, c=cfg):
        def fn(e):
            if not is_processing:
                clr = "#0d9488" if _year_ui_active else c["color"]
                l.config(bg=clr)
                f.config(bg=clr)
        return fn

    for w in (lbl, frame):
        w.bind("<Enter>", mk_enter())
        w.bind("<Leave>", mk_leave())

    # 右键菜单
    for w in (lbl, frame):
        w.bind("<Button-3>", make_zone_menu(idx, sv, lbl))

    # 点击：无路径则选择，有路径则打开
    for w in (lbl, frame):
        w.bind("<Button-1>", make_open_cb(idx, sv, lbl))

    zone_meta[lbl] = {"color": cfg["color"], "text": cfg["name"]}
    zone_widgets.append((idx, sv, lbl))

# ---- 通用整理区 (第 4 行，跨 3 列) ----
# 加载通用整理颜色（存配置，重启不丢失）
gen_color = GENERAL_COLOR
try:
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        _gc = json.load(f).get('general_color')
        if _gc:
            gen_color = _gc
except:
    pass

gen_frame = tk.Frame(main, bg=gen_color, bd=1, relief="raised")
gen_frame.grid(row=3, column=0, columnspan=3, padx=2, pady=(5, 2), sticky="nsew")

gen_sv = tk.StringVar(value="通用整理\n（拖入此处按原位置归档）")
gen_lbl = tk.Label(gen_frame, textvariable=gen_sv, bg=gen_color, fg="white",
                   font=FONT_GENERAL, cursor="hand2", wraplength=460)
gen_lbl.pack(fill="both", expand=True)

gen_handler = make_general_handler(gen_sv, gen_lbl)
for w in (gen_lbl, gen_frame):
    w.drop_target_register(DND_FILES)
    w.dnd_bind('<<Drop>>', gen_handler)

# 通用整理右键：配置颜色
def save_gen_color():
    """通用颜色保存（复用 save_all）"""
    save_all()

def pick_gen_color():
    global gen_color
    result = colorchooser.askcolor(color=gen_color, title="选择颜色")
    if result[1]:
        gen_color = result[1]
        gen_lbl.config(bg=result[1])
        gen_frame.config(bg=result[1])
        zone_meta[gen_lbl] = {"color": result[1], "text": "通用整理\n（拖入此处按原位置归档）"}
        save_gen_color()

gen_menu = tk.Menu(root, tearoff=0)
gen_menu.add_command(label="配置颜色", command=pick_gen_color)

def show_gen_menu(e):
    gen_menu.post(e.x_root, e.y_root)

# 悬停使用动态变暗
def gen_enter(e):
    if not is_processing:
        d = darken(gen_color)
        gen_lbl.config(bg=d)
        gen_frame.config(bg=d)
def gen_leave(e):
    if not is_processing:
        gen_lbl.config(bg=gen_color)
        gen_frame.config(bg=gen_color)

for w in (gen_lbl, gen_frame):
    w.bind("<Enter>", gen_enter)
    w.bind("<Leave>", gen_leave)
    w.bind("<Button-3>", show_gen_menu)

zone_meta[gen_lbl] = {"color": gen_color, "text": "通用整理\n（拖入此处按原位置归档）"}

# ---- 那年今日控制区（与通用整理区同位置，默认隐藏） ----
year_ctrl_frame = tk.Frame(main, bg=CTRL_BG, bd=1, relief="raised")
year_ctrl_frame.grid(row=3, column=0, columnspan=3, padx=2, pady=(5, 2), sticky="nsew")
year_ctrl_frame.columnconfigure(0, weight=1)
year_ctrl_frame.columnconfigure(1, weight=1)
year_ctrl_frame.columnconfigure(2, weight=1)
year_ctrl_frame.rowconfigure(0, weight=1)

ret_btn = tk.Button(year_ctrl_frame, text="返回", bg=CTRL_BG, fg=TEXT_MAIN,
                    font=FONT_GENERAL, relief="flat", cursor="hand2", bd=0,
                    activebackground="#e8ecf1", activeforeground=TEXT_MAIN,
                    command=lambda: _exit_year_mode())
ret_btn.grid(row=0, column=0, padx=4, pady=8, ipady=4, sticky="nsew")

left_btn = tk.Button(year_ctrl_frame, text="◀  往前 9 年", bg=CTRL_BG, fg=TEXT_MAIN,
                     font=FONT_GENERAL, relief="flat", cursor="hand2", bd=0,
                     activebackground="#e8ecf1", activeforeground=TEXT_MAIN,
                     command=lambda: _year_flip(-9))
left_btn.grid(row=0, column=1, padx=4, pady=8, ipady=4, sticky="nsew")

right_btn = tk.Button(year_ctrl_frame, text="往后 9 年  ▶", bg=CTRL_BG, fg=TEXT_MAIN,
                      font=FONT_GENERAL, relief="flat", cursor="hand2", bd=0,
                      activebackground="#e8ecf1", activeforeground=TEXT_MAIN,
                      command=lambda: _year_flip(9))
right_btn.grid(row=0, column=2, padx=4, pady=8, ipady=4, sticky="nsew")

# 悬停效果
def _yctrl_enter(e): e.widget.config(bg="#e8ecf1")
def _yctrl_leave(e): e.widget.config(bg=CTRL_BG)
for _b in (ret_btn, left_btn, right_btn):
    _b.bind("<Enter>", _yctrl_enter)
    _b.bind("<Leave>", _yctrl_leave)

# 初始隐藏
year_ctrl_frame.grid_remove()

# ---- 底部控制栏 (第 5 行) ----
ctrl = tk.Frame(main, bg=CTRL_BG)
ctrl.grid(row=4, column=0, columnspan=3, padx=2, pady=(6, 2), sticky="ew")

# == 第一排 ==
row1 = tk.Frame(ctrl, bg=CTRL_BG)
row1.pack(fill="x", pady=(2, 0))

left_group = tk.Frame(row1, bg=CTRL_BG)
left_group.pack(side="left", padx=(6, 0))

# 修改时间 — 第一排
time_mod_frame = tk.Frame(left_group, bg=SEG_TRACK, bd=0,
                          highlightbackground=SEG_BORDER, highlightthickness=1)
time_mod_frame.pack(side="left", padx=0)
btn_modify = tk.Button(time_mod_frame, text="修改时间", bg=SEG_SEL_BG, fg=SEG_SEL_FG,
                       font=FONT_CTRL, relief="flat", cursor="hand2", bd=0,
                       activebackground="#e2e8f0", activeforeground=TEXT_MAIN,
                       command=lambda: set_time_mode(False))
btn_modify.pack(ipady=3, padx=4, pady=1)

copy_btn = tk.Button(left_group, text="☐ 仅复制", bg=CTRL_BG, fg=TEXT_MAIN,
                     font=FONT_CTRL, relief="flat", cursor="hand2", bd=0,
                     activebackground="#e8ecf1", activeforeground=TEXT_MAIN,
                     command=toggle_copy_mode)
copy_btn.pack(side="left", ipady=2, padx=(4, 4))

year_btn = tk.Button(left_group, text="☐ 那年今日", bg=CTRL_BG, fg=TEXT_MAIN,
                     font=FONT_CTRL, relief="flat", cursor="hand2", bd=0,
                     activebackground="#e8ecf1", activeforeground=TEXT_MAIN,
                     command=toggle_year_mode)
year_btn.pack(side="left", ipady=2, padx=(4, 4))

day_btn = tk.Button(left_group, text="☑ 具体到日", bg=CTRL_BG, fg=TEXT_MAIN,
                    font=FONT_CTRL, relief="flat", cursor="hand2", bd=0,
                    activebackground="#e8ecf1", activeforeground=TEXT_MAIN,
                    command=toggle_day_mode)
day_btn.pack(side="left", ipady=2, padx=(4, 4))

# 置顶窗口
is_topmost = True

def toggle_topmost():
    global is_topmost
    if is_processing:
        return
    is_topmost = not is_topmost
    root.attributes("-topmost", is_topmost)
    topmost_btn.config(text="☑ 置顶窗口" if is_topmost else "☐ 置顶窗口")
    save_all()

topmost_btn = tk.Button(left_group, text="☑ 置顶窗口", bg=CTRL_BG, fg=TEXT_MAIN,
                        font=FONT_CTRL, relief="flat", cursor="hand2", bd=0,
                        activebackground="#e8ecf1", activeforeground=TEXT_MAIN,
                        command=toggle_topmost)
topmost_btn.pack(side="left", ipady=2, padx=(4, 4))

# 年份模式专用按钮（默认隐藏）
new_day_btn = tk.Button(left_group, text="新建今天", bg=CTRL_BG, fg=TEXT_MAIN,
                        font=("Microsoft YaHei", 9), relief="flat", cursor="hand2",
                        bd=0, activebackground="#e8ecf1", activeforeground=TEXT_MAIN,
                        command=_create_year_today)
new_day_btn.pack(side="left", ipady=2, padx=(4, 4))
new_day_btn.pack_forget()

new_month_btn = tk.Button(left_group, text="新建本月", bg=CTRL_BG, fg=TEXT_MAIN,
                          font=("Microsoft YaHei", 9), relief="flat", cursor="hand2",
                          bd=0, activebackground="#e8ecf1", activeforeground=TEXT_MAIN,
                          command=_create_year_month)
new_month_btn.pack(side="left", ipady=2, padx=(4, 4))
new_month_btn.pack_forget()

# == 第二排 ==
row2 = tk.Frame(ctrl, bg=CTRL_BG)
row2.pack(fill="x", pady=(0, 2))

left_group2 = tk.Frame(row2, bg=CTRL_BG)
left_group2.pack(side="left", padx=(6, 0))

# 创建时间 — 第二排
time_create_frame = tk.Frame(left_group2, bg=SEG_TRACK, bd=0,
                             highlightbackground=SEG_BORDER, highlightthickness=1)
time_create_frame.pack(side="left", padx=0)
btn_create = tk.Button(time_create_frame, text="创建时间", bg=SEG_UNSEL_BG, fg=SEG_UNSEL_FG,
                       font=FONT_CTRL, relief="flat", cursor="hand2", bd=0,
                       activebackground="#e2e8f0", activeforeground=TEXT_MAIN,
                       command=lambda: set_time_mode(True))
btn_create.pack(ipady=3, padx=4, pady=1)

# Everything 开关 + 路径选择组
ev_frame = tk.Frame(left_group2, bg=CTRL_BG)
ev_frame.pack(side="left")

ev_btn = tk.Button(ev_frame, text="☐ Everything", bg=CTRL_BG, fg=TEXT_MAIN,
                   font=FONT_CTRL, relief="flat", cursor="hand2", bd=0,
                   activebackground="#e8ecf1", activeforeground=TEXT_MAIN,
                   command=toggle_everything)
ev_btn.pack(side="left", ipady=2)

# 分隔符暗示这两个按钮属于 Everything
ev_sep = tk.Frame(ev_frame, bg=SEG_BORDER, width=1)
ev_sep.pack(side="left", fill="y", padx=2, pady=3)

ev_select_btn = tk.Button(ev_frame, text="点击选择路径", bg=CTRL_BG, fg=TEXT_MUTED,
                          font=("Microsoft YaHei", 9), relief="flat", cursor="hand2",
                          bd=0, padx=4, activebackground="#e8ecf1",
                          command=_do_ev_select)
ev_select_btn.pack(side="left", ipady=1)

ev_find_btn = tk.Button(ev_frame, text="自动查找", bg=CTRL_BG, fg=TEXT_MUTED,
                        font=("Microsoft YaHei", 9), relief="flat", cursor="hand2",
                        bd=0, padx=4, activebackground="#e8ecf1",
                        command=_do_ev_find)
ev_find_btn.pack(side="left", ipady=1, padx=(0, 8))

# 帮助按钮
help_btn = tk.Button(row2, text="ℹ 使用手册", bg=CTRL_BG, fg=TEXT_MAIN,
                     font=FONT_CTRL, relief="flat", cursor="hand2", bd=0,
                     activebackground="#e8ecf1", activeforeground=TEXT_MAIN,
                     command=show_help)
help_btn.pack(side="right", padx=(0, 6), ipady=4)

def help_enter(e): help_btn.config(bg="#e8ecf1")
def help_leave(e): help_btn.config(bg=CTRL_BG)
help_btn.bind("<Enter>", help_enter)
help_btn.bind("<Leave>", help_leave)

# 开关按钮的悬停效果
def _toggle_enter(e): e.widget.config(bg="#e8ecf1")
def _toggle_leave(e): e.widget.config(bg=CTRL_BG)
for _btn in (day_btn, copy_btn, topmost_btn, year_btn, ev_btn):
    _btn.bind("<Enter>", _toggle_enter)
    _btn.bind("<Leave>", _toggle_leave)


for w in (day_btn, copy_btn, topmost_btn, year_btn, ev_btn, btn_modify, btn_create, help_btn):
    w.bind("<Button-1>", lambda e: None)

# -- 恢复上次开关状态 --
_settings = load_settings()
use_copy = _settings['use_copy']
copy_btn.config(text="☑ 仅复制" if use_copy else "☐ 仅复制")
use_day = _settings['use_day']
day_btn.config(text="☑ 具体到日" if use_day else "☐ 具体到日")
use_ctime = _settings['use_ctime']
if use_ctime:
    btn_create.config(bg=SEG_SEL_BG, fg=SEG_SEL_FG)
    btn_modify.config(bg=SEG_UNSEL_BG, fg=SEG_UNSEL_FG)
else:
    btn_modify.config(bg=SEG_SEL_BG, fg=SEG_SEL_FG)
    btn_create.config(bg=SEG_UNSEL_BG, fg=SEG_UNSEL_FG)
is_topmost = _settings['is_topmost']
root.attributes("-topmost", is_topmost)
topmost_btn.config(text="☑ 置顶窗口" if is_topmost else "☐ 置顶窗口")
use_year_mode = _settings['use_year_mode']
if use_year_mode:
    year_start = time.localtime().tm_year - 8
    year_btn.config(text="☑ 那年今日")
use_everything = _settings['use_everything']
if use_everything:
    ev_btn.config(text="☑ Everything")
ev_path = _settings.get('ev_path', '')

root.mainloop()
