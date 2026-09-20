# -*- coding: utf-8 -*-
# 进程内拖放链路测试台：把真实程序跑起来，向主窗口 PostMessage 一条
# 合成 WM_DROPFILES（HDROP 内存布局与 Explorer 投递一致），验证
# 「窗口钩子 -> 落点判定 -> zone handler -> move_worker」整条链路。
#
# 用法：
#   python test_drop_harness.py            # 正常 stderr（控制台模式）
#   python test_drop_harness.py --nullio   # 模拟打包 exe 的 windowed 模式
#                                          # （stdout/stderr 为 None）
#
# 运行结束时打印 DISPATCH_RESULT=... 并退出；崩溃则带非零码。

import ctypes
import faulthandler
import importlib.util
import os
import sys
import tempfile
from ctypes import wintypes

faulthandler.enable()

if "--nullio" in sys.argv:
    sys.stdout = None
    sys.stderr = None

NO_DROP = "--no-drop" in sys.argv
BULK = "--bulk" in sys.argv

LONG_EMOJI_NAME = (
    "2026-07-17_09-15-56_PixPin_GitHub - Christoph-Wagner-firefox-better-"
    "history-ng：受 Vivaldi 启发的更好历史页面 ⛺ · GitHub --- GitHub - "
    "Christoph-Wagner-firefox-better-history-ng- A Better History page "
    "inspired by Vivaldi ⛺ · GitHub — Mozilla Firefox_firefox.webp"
)


def mark(msg):
    out = sys.__stdout__
    if out:
        out.write(f"MARK={msg}\n")
        out.flush()


APP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "文件归档器.py")
WM_DROPFILES = 0x0233


def build_hdrop(paths, pt):
    class DROPFILES(ctypes.Structure):
        _fields_ = [
            ("pFiles", wintypes.DWORD),
            ("pt", wintypes.POINT),
            ("fNC", wintypes.BOOL),
            ("fWide", wintypes.BOOL),
        ]

    raw = "\0".join(paths) + "\0\0"
    blob = bytes(DROPFILES(ctypes.sizeof(DROPFILES), pt, False, True)) \
        + raw.encode("utf-16-le")

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
    kernel32.GlobalAlloc.restype = wintypes.HGLOBAL
    kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
    kernel32.GlobalLock.restype = wintypes.LPVOID
    kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
    h = kernel32.GlobalAlloc(0x0002, len(blob))
    p = kernel32.GlobalLock(h)
    ctypes.memmove(p, blob, len(blob))
    kernel32.GlobalUnlock(h)
    return h


def main():
    user32 = ctypes.windll.user32
    user32.PostMessageW.argtypes = [
        wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]

    # 配置读写全部隔离到临时 APPDATA，绝不碰真实配置
    fake_appdata = tempfile.mkdtemp(prefix="drop_test_appdata_")
    os.environ["APPDATA"] = fake_appdata

    spec = importlib.util.spec_from_file_location("app_under_test", APP)
    app = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(app)  # 构建 GUI、注册原生拖放钩子
    assert app.CONFIG_PATH.startswith(fake_appdata), \
        f"配置未隔离: {app.CONFIG_PATH}"
    mark("IMPORT_OK")

    root, hwnd = app.root, app.root_hwnd
    root.update()
    mark("UPDATE_OK")

    moved = []
    app.move_worker = lambda *a, **k: moved.append(a[0])

    tmpdir = tempfile.mkdtemp(prefix="drop_test_")
    drop_paths = []
    if BULK:
        for i in range(5000):
            p = os.path.join(tmpdir, f"bulk_{i:05d}.txt")
            open(p, "w").close()
            drop_paths.append(p)
        long_p = os.path.join(tmpdir, LONG_EMOJI_NAME)
        open(long_p, "w").close()
        drop_paths.append(long_p)
        mark(f"BULK_READY={len(drop_paths)} maxlen={max(len(p) for p in drop_paths)}")
    else:
        f = os.path.join(tmpdir, "t.webp")
        open(f, "w").close()
        drop_paths.append(f)

    # 落点：通用整理区中央（换算成主窗口客户区坐标）
    origin = wintypes.POINT()
    user32.ClientToScreen(ctypes.c_void_p(hwnd), ctypes.byref(origin))
    gx = app.gen_lbl.winfo_rootx() + 5
    gy = app.gen_lbl.winfo_rooty() + 5
    drop_pt = wintypes.POINT(gx - origin.x, gy - origin.y)
    mark(f"DROP_PT={drop_pt.x},{drop_pt.y}")

    if not NO_DROP:
        hdrop = build_hdrop(drop_paths, drop_pt)
        r = user32.PostMessageW(ctypes.c_void_p(hwnd), WM_DROPFILES, hdrop, 0)
        assert r, "PostMessageW 失败"
        mark("POSTED")

    def check():
        got = [p for m in moved for p in m]
        result = {
            "no_drop": NO_DROP,
            "bulk": BULK,
            "expected": len(drop_paths),
            "move_worker_called": bool(moved),
            "moved_count": len(got),
            "long_path_intact": (LONG_EMOJI_NAME in " ".join(got)) if BULK else None,
        }
        try:
            root.destroy()
        except Exception:
            pass
        out = sys.__stdout__
        if out:
            out.write(f"DISPATCH_RESULT={result}\n")
            out.flush()

    root.after(3000, check)
    mark("MAINLOOP_ENTER")
    root.mainloop()
    mark("MAINLOOP_EXIT")

    got = [p for m in moved for p in m]
    if NO_DROP:
        print("HARNESS_OK (no-drop)")
        return 0
    if not moved:
        print("HARNESS_FAIL: move_worker 未被调用")
        return 1
    if len(got) != len(drop_paths):
        print(f"HARNESS_FAIL: 数量不符 {len(got)} != {len(drop_paths)}")
        return 1
    if BULK and LONG_EMOJI_NAME not in " ".join(got):
        print("HARNESS_FAIL: 超长 emoji 路径丢失")
        return 1
    print("HARNESS_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
