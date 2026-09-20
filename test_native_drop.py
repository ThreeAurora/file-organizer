# -*- coding: utf-8 -*-
# 回归测试：原生 WM_DROPFILES 解析（替代 tkinterdnd2 后的通道）
#
# 构造一个合成 HDROP（GlobalAlloc + DROPFILES 头 + 宽字符路径表，
# 与 Explorer 投递 WM_DROPFILES 时的内存布局一致），用与
# 文件归档器.py::_handle_wm_dropfiles 完全相同的 DragQueryFileW
# 调用方式解析，验证：
#   1. 大批量（5000 条）路径一条不丢
#   2. 超过 260 字符、含 emoji 的路径不截断不闪退
#
# 运行：python test_native_drop.py

import ctypes
import sys
from ctypes import wintypes

assert sys.platform == "win32", "仅限 Windows"

LONG_EMOJI_PATH = (
    r"E:\AAAAA\新建文件夹 (1)\2026-07-17_09-15-56_PixPin_GitHub - "
    "Christoph-Wagner-firefox-better-history-ng：受 Vivaldi 启发的更好"
    "历史页面 ⛺ · GitHub --- GitHub - Christoph-Wagner-firefox-better-"
    "history-ng- A Better History page inspired by Vivaldi ⛺ · GitHub "
    "— Mozilla Firefox_firefox.webp"
)

BULK_COUNT = 5000


def build_hdrop(paths):
    class DROPFILES(ctypes.Structure):
        _fields_ = [
            ("pFiles", wintypes.DWORD),
            ("pt", wintypes.POINT),
            ("fNC", wintypes.BOOL),
            ("fWide", wintypes.BOOL),
        ]

    raw = "\0".join(paths) + "\0\0"
    blob = bytes(DROPFILES(ctypes.sizeof(DROPFILES),
                           wintypes.POINT(10, 10), False, True)) \
        + raw.encode("utf-16-le")

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
    kernel32.GlobalAlloc.restype = wintypes.HGLOBAL
    kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
    kernel32.GlobalLock.restype = wintypes.LPVOID
    kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
    kernel32.GlobalUnlock.restype = wintypes.BOOL

    GMEM_MOVEABLE = 0x0002
    h = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(blob))
    assert h, f"GlobalAlloc 失败: {ctypes.GetLastError()}"
    p = kernel32.GlobalLock(h)
    assert p, f"GlobalLock 失败: {ctypes.GetLastError()}"
    ctypes.memmove(p, blob, len(blob))
    kernel32.GlobalUnlock(h)
    return h


def parse_hdrop(hdrop):
    # 与 文件归档器.py::_handle_wm_dropfiles 逐行一致
    shell32 = ctypes.windll.shell32
    shell32.DragQueryFileW.argtypes = [
        wintypes.HANDLE, wintypes.UINT, wintypes.LPWSTR, wintypes.UINT]
    shell32.DragQueryFileW.restype = wintypes.UINT

    count = shell32.DragQueryFileW(hdrop, 0xFFFFFFFF, None, 0)
    paths = []
    for i in range(count):
        n = shell32.DragQueryFileW(hdrop, i, None, 0)
        if n <= 0:
            continue
        buf = ctypes.create_unicode_buffer(n + 1)
        shell32.DragQueryFileW(hdrop, i, buf, n + 1)
        paths.append(buf.value)
    return paths


def main():
    paths = [rf"E:\测试目录\文件_{i:05d}.txt" for i in range(BULK_COUNT)]
    paths.append(LONG_EMOJI_PATH)

    hdrop = build_hdrop(paths)
    try:
        got = parse_hdrop(hdrop)
    finally:
        shell32 = ctypes.windll.shell32
        shell32.DragFinish.argtypes = [wintypes.HANDLE]
        shell32.DragFinish(hdrop)

    assert len(got) == len(paths), f"数量不符: {len(got)} != {len(paths)}"
    assert got[-1] == LONG_EMOJI_PATH, "超长 emoji 路径被截断或变形"
    assert got[0] == paths[0] and got[-2] == paths[-2], "普通路径内容不符"
    print(f"OK: {len(got)} 条路径全部解析成功")
    print(f"OK: 超长路径 {len(LONG_EMOJI_PATH)} 字符（>260），emoji 完整保留")


if __name__ == "__main__":
    main()
