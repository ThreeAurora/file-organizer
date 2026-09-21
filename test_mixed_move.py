# -*- coding: utf-8 -*-
"""验证混合模式（keep_time_fallback）的分流：

符合 年\月\日期层 的项走结构落点，其余按时间归类；一个不符不再整批
拒绝。「通用整理」区（没有分区根目录）勾着附带结构也照旧按时间归类。

不启动界面：把底层搬运、时间归类落点、move_worker 与结构校验/落点
函数的源码抠出来，在隔离命名空间里执行（同 test_structure_move.py）。
"""
import os
import shutil
import sys
import tempfile
import time

SRC_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "文件归档器.py")
src = open(SRC_FILE, encoding="utf-8").read()

i = src.index("# 无损搬运：「附带结构」用到的底层")
j = src.index("# 「附带结构」的落点规则（移植自「视频移动」）")
k = src.index("# 高 DPI 适配（4K 屏等）")
m = src.index("def get_target_info(")
n = src.index("def move_worker(")
p = src.index("def make_zone_handler(")

ns = {
    "os": os, "re": __import__("re"), "shutil": shutil,
    "ctypes": __import__("ctypes"),
    "time": time,
    "zone_meta": {},
    # 开关状态：混合模式 = 附带结构 + fallback 都开
    "use_copy": False,
    "use_keep_time": True,
    "keep_time_fallback": True,
    "use_ctime": False,
    "use_day": True,
    "is_processing": False,
}
from ctypes import wintypes  # noqa: E402
ns["wintypes"] = wintypes


class _Stub:
    def set(self, _text):
        pass

    def cget(self, _key):
        return "#000000"

    def config(self, **_kw):
        pass


class _Root:
    def after(self, _ms, fn=None):
        if fn:
            fn()


ns["_show_toast"] = lambda widget, text: ns.setdefault("toasts", []).append(text)
ns["status_var"] = _Stub()
ns["label"] = _Stub()
ns["root_window"] = _Root()

exec(compile(src[i:j], "<mover-chunk>", "exec"), ns)
exec(compile(src[m:n], "<target-chunk>", "exec"), ns)
exec(compile(src[n:p], "<worker-chunk>", "exec"), ns)
exec(compile(src[j:k], "<structure-chunk>", "exec"), ns)

get_target_info = ns["get_target_info"]
move_worker = ns["move_worker"]
_move_mixed = ns["_move_mixed"]
_move_structured = ns["_move_structured"]
get_creation_time = ns["get_creation_time"]
set_creation_time = ns["set_creation_time"]

OLD_UNIX = time.mktime((2017, 6, 13, 12, 30, 0, 0, 0, -1))
DAY_UNIX = time.mktime((2020, 7, 20, 12, 0, 0, 0, 0, -1))
OLD_FT = int((OLD_UNIX + 11644473600) * 10000000)

passed = []
failed = []


def check(label, cond, extra=""):
    if cond:
        passed.append(label)
    else:
        failed.append(label + ("  " + extra if extra else ""))


def listing(path):
    try:
        return str(os.listdir(path))
    except Exception as e:
        return "<列不出：%s>" % e


def stamp(path, ts=OLD_UNIX):
    set_creation_time(path, int((ts + 11644473600) * 10000000))
    os.utime(path, (ts, ts))


def aged(path, tol_ft=10_000_000, tol_s=2):
    ft = get_creation_time(path)
    return (ft is not None and abs(ft - OLD_FT) < tol_ft
            and abs(os.stat(path).st_mtime - OLD_UNIX) < tol_s)


def make_src_file(base, rel, content="x", ts=OLD_UNIX):
    path = os.path.join(base, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "w").write(content)
    stamp(path, ts)
    return path


ws = tempfile.mkdtemp(prefix="mixed_")
lib = os.path.join(ws, "lib")
zone = os.path.join(ws, "zone")
os.makedirs(zone)

# ---------------------------------------------------------------
# 1) 分流落点：结构项走结构，普通文件/文件夹按时间
# ---------------------------------------------------------------
f_struct = make_src_file(lib, r"2016\03\20160301\a.mp4")
f_plain = make_src_file(lib, r"杂项\b.txt")
folder_plain = os.path.join(lib, "无结构素材")
make_src_file(folder_plain, "内里.txt")
stamp(folder_plain)

ns["toasts"] = []
_move_mixed([f_struct, f_plain, folder_plain], ns["status_var"], ns["label"],
            ns["root_window"], zone)

p_struct = os.path.join(zone, "2016", "03", "2016-03-01", "a.mp4")
p_plain = os.path.join(zone, "2017", "06", "2017-06-13", "b.txt")
p_folder = os.path.join(zone, "2017", "06", "2017-06-13", "无结构素材")
check("1 结构项走结构落点", os.path.isfile(p_struct), p_struct)
check("1 普通文件按时间落点", os.path.isfile(p_plain), p_plain)
check("1 普通文件夹整棵按时间落点",
      os.path.isfile(os.path.join(p_folder, "内里.txt")), p_folder)
check("1 结构项创建时间保真", aged(p_struct))
check("1 时间项创建时间保真", aged(p_plain))
check("1 源都已搬走", not os.path.exists(f_struct) and not os.path.exists(f_plain))
check("1 成功时不弹分流提示", ns["toasts"] == [], str(ns.get("toasts")))
check("1 收尾 is_processing 复位", ns.get("is_processing") is False)

# ---------------------------------------------------------------
# 2) 日期层本体被拖入：校验拒 -> 落时间支，不整批拒绝
# ---------------------------------------------------------------
day_only = os.path.join(ws, "dayonly", "2020", "07", "20200720")
os.makedirs(day_only)
open(os.path.join(day_only, "x.txt"), "w").close()
stamp(day_only, DAY_UNIX)

f_struct2 = make_src_file(lib, r"2018\05\20180501\c.mp4")
ns["toasts"] = []
_move_mixed([f_struct2, day_only], ns["status_var"], ns["label"],
            ns["root_window"], zone)

check("2 同批结构项照常落位",
      os.path.isfile(os.path.join(zone, "2018", "05", "2018-05-01", "c.mp4")))
check("2 日期层本体转时间归类",
      os.path.isfile(os.path.join(zone, "2020", "07", "2020-07-20", "20200720",
                                  "x.txt")),
      str(os.listdir(zone)))
check("2 没有整批拒绝提示", ns["toasts"] == [], str(ns.get("toasts")))

# ---------------------------------------------------------------
# 3) 已在分区里的静默跳过（不算时间项，也不弹提示）
# ---------------------------------------------------------------
in_tree = os.path.join(zone, "2016", "03", "2016-03-01", "a.mp4")
ns["toasts"] = []
_move_mixed([in_tree], ns["status_var"], ns["label"], ns["root_window"], zone)
check("3 库内静默跳过·没弹提示", ns["toasts"] == [] and os.path.isfile(in_tree),
      str(ns.get("toasts")))

# ---------------------------------------------------------------
# 4) 时间支重名 _1 / 结构支重名 _1
# ---------------------------------------------------------------
f_dup = make_src_file(lib, r"杂项2\b.txt")
_move_mixed([f_dup], ns["status_var"], ns["label"], ns["root_window"], zone)
check("4 时间支重名落 _1",
      os.path.isfile(os.path.join(zone, "2017", "06", "2017-06-13", "b_1.txt")),
      listing(os.path.join(zone, "2017", "06", "2017-06-13")))

f_struct3 = make_src_file(lib, r"2016\03\20160301\a.mp4")
_move_mixed([f_struct3], ns["status_var"], ns["label"], ns["root_window"], zone)
check("4 结构支重名落 _1",
      os.path.isfile(os.path.join(zone, "2016", "03", "2016-03-01", "a_1.mp4")),
      listing(os.path.join(zone, "2016", "03", "2016-03-01")))

# ---------------------------------------------------------------
# 5) move_worker 的分流判定
# ---------------------------------------------------------------
# 5a 通用整理（没有分区根目录）：按时间落到文件自己旁边
gen = os.path.join(ws, "gen")
g1 = make_src_file(gen, "a.txt")
move_worker([g1], ns["status_var"], ns["label"], ns["root_window"], None)
check("5a 通用整理按时间归类",
      os.path.isfile(os.path.join(gen, "2017", "06", "2017-06-13", "a.txt")))

# 5b 通用整理 + 关掉混合模式：仍然按时间归类（勾了附带结构也不拒收）
ns["keep_time_fallback"] = False
g2 = make_src_file(gen, "c.txt")
move_worker([g2], ns["status_var"], ns["label"], ns["root_window"], None)
check("5b 纯结构模式下通用整理也照旧可用",
      os.path.isfile(os.path.join(gen, "2017", "06", "2017-06-13", "c.txt")))

# 5c 九宫格 + 关掉混合模式：整批拒绝的老语义不变
bad = make_src_file(lib, r"2019\01\没结构\d.mp4")
ns["toasts"] = []
move_worker([bad], ns["status_var"], ns["label"], ns["root_window"], zone)
check("5c 纯结构模式仍整批拒绝",
      os.path.exists(bad) and ns["toasts"] and "结构不符" in ns["toasts"][0],
      str(ns.get("toasts")))

# 5d 九宫格 + 混合模式：无结构项转时间归类
ns["keep_time_fallback"] = True
move_worker([bad], ns["status_var"], ns["label"], ns["root_window"], zone)
check("5d 混合模式下无结构项按时间落位",
      os.path.isfile(os.path.join(zone, "2017", "06", "2017-06-13", "d.mp4")),
      listing(os.path.join(zone, "2017", "06", "2017-06-13")))

# ---------------------------------------------------------------
# 6) 仅复制 + 混合：源仍在，副本照样保时间
# ---------------------------------------------------------------
ns["use_copy"] = True
f_copy = make_src_file(lib, r"2016\03\20160301\e.mp4")
_move_mixed([f_copy], ns["status_var"], ns["label"], ns["root_window"], zone)
p_copy = os.path.join(zone, "2016", "03", "2016-03-01", "e.mp4")
check("6 仅复制·源仍在", os.path.isfile(f_copy))
check("6 仅复制·副本落结构与保时间", os.path.isfile(p_copy) and aged(p_copy))
ns["use_copy"] = False

shutil.rmtree(ws, ignore_errors=True)

print("=" * 62)
for item in passed:
    print("  [OK] " + item)
for item in failed:
    print("  [FAIL] " + item)
print("=" * 62)
print("通过 %d 项，失败 %d 项" % (len(passed), len(failed)))
sys.exit(1 if failed else 0)
