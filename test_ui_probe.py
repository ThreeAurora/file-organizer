# -*- coding: utf-8 -*-
"""进程内探针：默认开启「附带结构」+ 混合模式（设置窗口两项）。

在隔离 APPDATA 下把源码整份 exec 起来，直接操作真实 widget：验证
启动状态、设置窗口两个勾选框、保存落盘、时间按钮的显隐切换。
是进程内代理，**不代表真机肉眼可见性**——观感仍以用户实机为准。
"""
import importlib.util
import json
import os
import sys
import tempfile

SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "文件归档器.py")
FAKE_APPDATA = tempfile.mkdtemp(prefix="archprobe_")
os.environ["APPDATA"] = FAKE_APPDATA

ok = fail = 0


def check(desc, cond, extra=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  [OK] {desc}")
    else:
        fail += 1
        print(f"  [NG] {desc} {extra}")


def load(name):
    spec = importlib.util.spec_from_file_location(name, SRC)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def walk(w):
    for c in w.winfo_children():
        yield c
        yield from walk(c)


def find_btn(w, text):
    for c in walk(w):
        if c.winfo_class() == "Button" and c.cget("text") == text:
            return c
    return None


def find_checks(w):
    return [c for c in walk(w) if c.winfo_class() == "Checkbutton"]


def check_by_text(w, text):
    for c in find_checks(w):
        if c.cget("text") == text:
            return c
    return None


CFG = os.path.join(FAKE_APPDATA, "文件归档器", "config.json")

print("=" * 60)
print("组 1：全新安装（无配置）启动即开启「附带结构」，默认混合模式")
print("=" * 60)
m = load("arch1")
m.messagebox.showinfo = lambda *a, **k: None      # 别弹模态框
m.messagebox.showwarning = lambda *a, **k: None
check("keep_time_default 为真", m.keep_time_default is True, m.keep_time_default)
check("use_keep_time 启动即真", m.use_keep_time is True, m.use_keep_time)
check("keep_time_fallback 为真", m.keep_time_fallback is True, m.keep_time_fallback)
check("底栏按钮显示 ☑", m.keep_btn.cget("text") == "☑ 附带结构", m.keep_btn.cget("text"))
check("混合模式下修改时间按钮仍显示",
      m.time_mod_frame.winfo_manager() == "pack", m.time_mod_frame.winfo_manager())
check("混合模式下创建时间按钮仍显示",
      m.time_create_frame.winfo_manager() == "pack", m.time_create_frame.winfo_manager())

print()
print("=" * 60)
print("组 2：设置窗口有两项，均默认勾上，内容不裁切")
print("=" * 60)
btn = find_btn(m.root, "⚙ 设置")
check("找到「⚙ 设置」按钮", btn is not None)
m.open_settings()
w = m._settings_win
w.update_idletasks()
check("设置窗口已创建", w is not None and w.winfo_exists())
cbs = find_checks(w)
check("窗口里有两个勾选框", len(cbs) == 2, len(cbs))
cb_default = check_by_text(w, "启动时默认开启「附带结构」")
cb_fallback = check_by_text(w, "结构不符时按时间归类")
check("第一项文案", cb_default is not None)
check("第二项文案", cb_fallback is not None)
if cb_default:
    check("第一项初始为勾上", str(w.getvar(cb_default.cget("variable"))) == "1",
          repr(w.getvar(cb_default.cget("variable"))))
if cb_fallback:
    check("第二项初始为勾上", str(w.getvar(cb_fallback.cget("variable"))) == "1",
          repr(w.getvar(cb_fallback.cget("variable"))))
need_h = w.winfo_reqheight()
print(f"   设置窗口需要高度 {need_h}px，窗口高 {w.winfo_height()}px（460x300）")
check("内容装得下（不裁切）", need_h <= 300, need_h)

print()
print("=" * 60)
print("组 3：两项都取消 → 落盘；纯结构模式当场收起时间按钮")
print("=" * 60)
cb_default.invoke()                                # 取消「启动默认」
cb_fallback.invoke()                               # 取消「混合模式」
check("取消后第一项为假", str(w.getvar(cb_default.cget("variable"))) == "0")
check("取消后第二项为假", str(w.getvar(cb_fallback.cget("variable"))) == "0")
save_btn = find_btn(w, "保存")
check("找到保存按钮", save_btn is not None)
save_btn.invoke()
check("保存后窗口已关闭", not w.winfo_exists() or m._settings_win is None)
data = json.load(open(CFG, encoding="utf-8"))
check("config.json 写下 keep_time_default=False",
      data["settings"].get("keep_time_default") is False,
      data["settings"].get("keep_time_default"))
check("config.json 写下 keep_time_fallback=False",
      data["settings"].get("keep_time_fallback") is False,
      data["settings"].get("keep_time_fallback"))
check("config.json 同时记下本次 use_keep_time=True",
      data["settings"].get("use_keep_time") is True,
      data["settings"].get("use_keep_time"))
check("内存里的 keep_time_default 同步为假", m.keep_time_default is False)
check("内存里的 keep_time_fallback 同步为假", m.keep_time_fallback is False)
check("纯结构模式下修改时间按钮当场收起",
      m.time_mod_frame.winfo_manager() == "", m.time_mod_frame.winfo_manager())
check("纯结构模式下创建时间按钮当场收起",
      m.time_create_frame.winfo_manager() == "", m.time_create_frame.winfo_manager())

print()
print("=" * 60)
print("组 4：重启读回两项；再开设置勾回混合模式立即恢复按钮")
print("=" * 60)
m2 = load("arch2")
m2.messagebox.showinfo = lambda *a, **k: None
check("重启后 keep_time_default 读到假", m2.keep_time_default is False)
check("重启后 use_keep_time 按记录值=true（记住上次）", m2.use_keep_time is True,
      m2.use_keep_time)
check("重启后 keep_time_fallback 读到假", m2.keep_time_fallback is False)
check("重启后按钮仍是收起", m2.time_mod_frame.winfo_manager() == "")

m2.open_settings()
w2 = m2._settings_win
w2.update_idletasks()
cb2 = check_by_text(w2, "结构不符时按时间归类")
check("第二项读出未勾", str(w2.getvar(cb2.cget("variable"))) == "0",
      repr(w2.getvar(cb2.cget("variable"))))
cb2.invoke()
find_btn(w2, "保存").invoke()
check("勾回并保存后 keep_time_fallback=true", m2.keep_time_fallback is True)
check("混合模式恢复后按钮重现（modify）",
      m2.time_mod_frame.winfo_manager() == "pack", m2.time_mod_frame.winfo_manager())
check("混合模式恢复后按钮重现（create）",
      m2.time_create_frame.winfo_manager() == "pack", m2.time_create_frame.winfo_manager())
data2 = json.load(open(CFG, encoding="utf-8"))
check("config.json 同步 keep_time_fallback=True",
      data2["settings"].get("keep_time_fallback") is True,
      data2["settings"].get("keep_time_fallback"))

# 关掉底栏开关后重启，应记住「关」
m2.toggle_keep_time()
m3 = load("arch3")
check("关掉底栏开关后重启：use_keep_time=False（记住）", m3.use_keep_time is False,
      m3.use_keep_time)

print()
print("=" * 60)
print("组 5：改过文案的使用手册窗口仍能正常撑开")
print("=" * 60)
m.show_help()
hw = m._help_win
hw.update_idletasks()
check("手册窗口已创建", hw is not None and hw.winfo_exists())
need = hw.winfo_reqheight()
scr = hw.winfo_screenheight()
print(f"   手册需要高度 {need}px，屏幕 {scr}px，窗口高 {hw.winfo_height()}px")
check("手册没超屏（不裁切）", need <= scr - 90, need)

print()
print("=" * 60)
print(f"通过 {ok} 项，失败 {fail} 项")
print("=" * 60)
sys.exit(1 if fail else 0)
