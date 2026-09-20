# -*- coding: utf-8 -*-
"""验证「附带结构」：搬运不许改创建时间 / 修改时间。

不启动界面，只 import 文件归档器里的底层函数来测。
注意：模块顶层会 `import tkinterdnd2` 并执行界面构建，所以这里不是
import 整个模块，而是把需要的函数源码抠出来单独执行。
"""
import os
import shutil
import sys
import tempfile
import time

SRC_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "文件归档器.py")

# ---------------------------------------------------------------
# 把目标模块里 ctypes 那段 + 搬运函数抠出来，在隔离命名空间里执行
# ---------------------------------------------------------------
src = open(SRC_FILE, encoding="utf-8").read()

BEGIN = "# 无损搬运：「附带结构」用到的底层"
END = "def move_preserving_times"

i = src.index(BEGIN)
j = src.index(END)
chunk = src[i:j]

# move_preserving_times / copy_preserving_times 也要（在 END 之后）
k = src.index("def copy_preserving_times")
m = src.index("\n\n\n", src.index("set_creation_time(dst, get_creation_time(src))", k))
chunk += src[j:m]

ns = {
    "os": os, "shutil": shutil, "ctypes": __import__("ctypes"),
    "__name__": "probe",
}
from ctypes import wintypes  # noqa: E402
ns["wintypes"] = wintypes
exec(compile(chunk, "<mover-chunk>", "exec"), ns)

get_creation_time = ns["get_creation_time"]
set_creation_time = ns["set_creation_time"]
same_volume = ns["same_volume"]
move_file = ns["move_file"]
move_dir = ns["move_dir"]
move_preserving_times = ns["move_preserving_times"]
copy_preserving_times = ns["copy_preserving_times"]

# ---------------------------------------------------------------
# 一个 2017-06-13 12:30 的古老时间戳
# ---------------------------------------------------------------
OLD_UNIX = time.mktime((2017, 6, 13, 12, 30, 0, 0, 0, -1))
OLD_FT = int((OLD_UNIX + 11644473600) * 10000000)

passed = []
failed = []


def check(label, cond, extra=""):
    if cond:
        passed.append(label)
    else:
        failed.append(label + ("  " + extra if extra else ""))


def backdate(path):
    """把创建时间和修改时间都拨到 2017-06-13。"""
    set_creation_time(path, OLD_FT)
    os.utime(path, (OLD_UNIX, OLD_UNIX))


def aged(path, tol_ft=10_000_000, tol_s=2):
    """创建时间和修改时间是否都还停在 2017-06-13。

    tol_ft = 1 秒（FILETIME 单位是 100ns，1 秒 = 1e7）
    """
    ft = get_creation_time(path)
    c_ok = ft is not None and abs(ft - OLD_FT) < tol_ft
    m_ok = abs(os.stat(path).st_mtime - OLD_UNIX) < tol_s
    return c_ok and m_ok


def show(path):
    ft = get_creation_time(path)
    if ft is None:
        return "创建时间=? 修改时间=%.0f" % os.stat(path).st_mtime
    c = ft / 10000000 - 11644473600
    return "创建=%s 修改=%s" % (
        time.strftime("%Y-%m-%d %H:%M", time.localtime(c)),
        time.strftime("%Y-%m-%d %H:%M", time.localtime(os.stat(path).st_mtime)),
    )


workspace = tempfile.mkdtemp(prefix="keep_time_")
print("工作目录:", workspace)
print("=" * 62)

try:
    # ===========================================================
    # 1) 同盘：单文件
    # ===========================================================
    d1 = os.path.join(workspace, "d1")
    os.makedirs(os.path.join(d1, "src"))
    os.makedirs(os.path.join(d1, "dst"))
    f = os.path.join(d1, "src", "a.txt")
    open(f, "w").write("hello")
    backdate(f)

    move_file(f, os.path.join(d1, "dst", "a.txt"))
    check("1 同盘单文件·创建时间保留", aged(os.path.join(d1, "dst", "a.txt")),
          show(os.path.join(d1, "dst", "a.txt")))
    check("1 同盘单文件·源已删", not os.path.exists(f))

    # ===========================================================
    # 2) 同盘：整个文件夹（含子目录、多文件）
    # ===========================================================
    d2 = os.path.join(workspace, "d2")
    src_dir = os.path.join(d2, "树", "子层", "更深")
    os.makedirs(src_dir)
    os.makedirs(os.path.join(d2, "out"))
    targets = [os.path.join(d2, "树", "root.txt"),
               os.path.join(d2, "树", "子层", "mid.txt"),
               os.path.join(src_dir, "deep.txt")]
    for t in targets:
        open(t, "w").write("x")
        backdate(t)
    os.utime(os.path.join(d2, "树", "子层"), (OLD_UNIX, OLD_UNIX))
    set_creation_time(os.path.join(d2, "树", "子层"), OLD_FT)

    move_dir(os.path.join(d2, "树"), os.path.join(d2, "out", "树"))
    newbase = os.path.join(d2, "out", "树")
    check("2 同盘文件夹·根目录存在", os.path.isdir(newbase))
    for rel in ("root.txt", os.path.join("子层", "mid.txt"),
                os.path.join("子层", "更深", "deep.txt")):
        p = os.path.join(newbase, rel)
        check("2 同盘文件夹·%s 时间保真" % rel, aged(p), show(p))
    check("2 同盘文件夹·子目录创建时间保真",
          abs((get_creation_time(os.path.join(newbase, "子层")) or 0) - OLD_FT)
          < 10_000_000,
          show(os.path.join(newbase, "子层")))
    check("2 同盘文件夹·源已删", not os.path.exists(os.path.join(d2, "树")))

    # ===========================================================
    # 3) 跨盘：单文件（把 same_volume 打成 False）
    # ===========================================================
    real_same = ns["same_volume"]
    d3 = os.path.join(workspace, "d3")
    os.makedirs(os.path.join(d3, "src"))
    os.makedirs(os.path.join(d3, "dst"))
    f3 = os.path.join(d3, "src", "b.txt")
    open(f3, "w").write("world")
    backdate(f3)

    ns["same_volume"] = lambda a, b: False        # 假装两块盘
    try:
        move_file(f3, os.path.join(d3, "dst", "b.txt"))
    finally:
        ns["same_volume"] = real_same

    check("3 跨盘单文件·创建时间保留",
          aged(os.path.join(d3, "dst", "b.txt")),
          show(os.path.join(d3, "dst", "b.txt")))
    check("3 跨盘单文件·源已删", not os.path.exists(f3))

    # ===========================================================
    # 4) 跨盘：整个文件夹
    # ===========================================================
    d4 = os.path.join(workspace, "d4")
    tree = os.path.join(d4, "老照片", "2016")
    os.makedirs(tree)
    os.makedirs(os.path.join(d4, "out"))
    files4 = [os.path.join(d4, "老照片", "top.jpg"),
              os.path.join(tree, "inner.jpg")]
    for t in files4:
        open(t, "w").write("img")
        backdate(t)
    # 子目录本身也要回拨 —— 不然它本来就是「今天」建的，
    # 搬过去还是今天，这不是 bug 而是忠实复制
    backdate(tree)

    ns["same_volume"] = lambda a, b: False
    try:
        move_dir(os.path.join(d4, "老照片"),
                 os.path.join(d4, "out", "老照片"))
    finally:
        ns["same_volume"] = real_same

    nb4 = os.path.join(d4, "out", "老照片")
    for rel in ("top.jpg", os.path.join("2016", "inner.jpg")):
        p = os.path.join(nb4, rel)
        check("4 跨盘文件夹·%s 时间保真" % rel, aged(p), show(p))
    check("4 跨盘文件夹·子目录创建时间保真",
          abs((get_creation_time(os.path.join(nb4, "2016")) or 0) - OLD_FT)
          < 10_000_000,
          show(os.path.join(nb4, "2016")))
    check("4 跨盘文件夹·源已删", not os.path.exists(os.path.join(d4, "老照片")))

    # ===========================================================
    # 5) 对照：证明老做法（shutil.move）确实会洗掉创建时间
    # ===========================================================
    d5 = os.path.join(workspace, "d5")
    os.makedirs(d5)
    f5 = os.path.join(d5, "c.txt")
    open(f5, "w").write("naive")
    backdate(f5)

    # 直接调 shutil.move 到同盘另一个位置（不改名字的迁移）
    f5_dst = os.path.join(d5, "c_moved.txt")
    os.rename(f5, f5_dst)          # 同盘 rename 保留全部时间戳
    check("5 对照组·同盘 rename 保真", aged(f5_dst), show(f5_dst))

    # 真·跨盘场景：copy2 复制
    f6 = os.path.join(d5, "d.txt")
    open(f6, "w").write("copy2")
    backdate(f6)
    f6_dst = os.path.join(d5, "d_copy2.txt")
    shutil.copy2(f6, f6_dst)
    check("5 对照组·copy2 保不住创建时间（预期为假）",
          not aged(f6_dst), show(f6_dst))
    check("5 对照组·但 copy2 保住了修改时间",
          abs(os.stat(f6_dst).st_mtime - OLD_UNIX) < 2)

    # ===========================================================
    # 6) copy_preserving_times（仅复制 + 附带结构）
    # ===========================================================
    d7 = os.path.join(workspace, "d7")
    os.makedirs(d7)
    f7 = os.path.join(d7, "e.txt")
    open(f7, "w").write("keepcopy")
    backdate(f7)
    f7_dst = os.path.join(d7, "e_copy.txt")
    copy_preserving_times(f7, f7_dst)
    check("6 仅复制+保时间·创建时间保留", aged(f7_dst), show(f7_dst))
    check("6 仅复制+保时间·源仍在", os.path.exists(f7))

    # 跨盘复制整个文件夹
    d8 = os.path.join(workspace, "d8")
    t8 = os.path.join(d8, "夹", "内层")
    os.makedirs(t8)
    for p in (os.path.join(d8, "夹", "1.txt"), os.path.join(t8, "2.txt")):
        open(p, "w").write("z")
        backdate(p)
    copy_preserving_times(os.path.join(d8, "夹"), os.path.join(d8, "夹_copy"))
    for rel in ("1.txt", os.path.join("内层", "2.txt")):
        p = os.path.join(d8, "夹_copy", rel)
        check("6 仅复制+保时间·%s 保真" % rel, aged(p), show(p))

finally:
    shutil.rmtree(workspace, ignore_errors=True)

print("=" * 62)
for p in passed:
    print("  [OK] " + p)
for f_ in failed:
    print("  [FAIL] " + f_)
print("=" * 62)
print("通过 %d 项，失败 %d 项" % (len(passed), len(failed)))
sys.exit(1 if failed else 0)
