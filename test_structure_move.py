# -*- coding: utf-8 -*-
"""验证「附带结构」的落点规则（移植自「视频移动」）。

不启动界面：把底层搬运函数 + 结构校验/落点函数的源码抠出来，
在隔离命名空间里执行（同 test_keep_time.py 的做法）。
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

ns = {
    "os": os, "re": __import__("re"), "shutil": shutil,
    "ctypes": __import__("ctypes"),
    "zone_meta": {},
    "use_copy": False,
    "use_keep_time": True,
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
exec(compile(src[j:k], "<structure-chunk>", "exec"), ns)

parse_day_folder = ns["parse_day_folder"]
validate_structure = ns["validate_structure"]
_already_in_tree = ns["_already_in_tree"]
_is_inside = ns["_is_inside"]
_unique_dest = ns["_unique_dest"]
_move_structured = ns["_move_structured"]
get_creation_time = ns["get_creation_time"]
set_creation_time = ns["set_creation_time"]

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
    set_creation_time(path, OLD_FT)
    os.utime(path, (OLD_UNIX, OLD_UNIX))


def aged(path, tol_ft=10_000_000, tol_s=2):
    ft = get_creation_time(path)
    c_ok = ft is not None and abs(ft - OLD_FT) < tol_ft
    m_ok = abs(os.stat(path).st_mtime - OLD_UNIX) < tol_s
    return c_ok and m_ok


def make_src_file(base, rel, content="x"):
    p = os.path.join(base, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "w").write(content)
    backdate(p)
    return p


# ---------------------------------------------------------------
# 1) parse_day_folder：两种写法 + 非法值
# ---------------------------------------------------------------
ok, y, m, d, _ = parse_day_folder("20160301")
check("1 无横杠日期层", ok and (y, m, d) == ("2016", "03", "2016-03-01"))
ok, y, m, d, _ = parse_day_folder("2016-03-01")
check("1 横杠日期层", ok and (y, m, d) == ("2016", "03", "2016-03-01"))
check("1 月份13非法", not parse_day_folder("20161301")[0])
check("1 日子32非法", not parse_day_folder("20160132")[0])
check("1 半吊子格式拒", not parse_day_folder("2023-1126")[0])
check("1 随手名字拒", not parse_day_folder("视频合集")[0])

# ---------------------------------------------------------------
# 2) validate_structure：认 / 拒
# ---------------------------------------------------------------
ok, y, m, d, _ = validate_structure(r"G:\库\2017\06\20170613\a.mp4")
check("2 文件在日期层下", ok and (y, m, d) == ("2017", "06", "2017-06-13"))
ok, y, m, d, _ = validate_structure(r"G:\库\2017\06\20170613\素材")
check("2 文件夹在日期层下", ok and d == "2017-06-13")
check("2 年月对不上拒",
      not validate_structure(r"G:\库\2017\09\20170614\a.mp4")[0])
check("2 日期层本身拒",
      not validate_structure(r"G:\库\2017\06\20170613")[0])
check("2 横杠日期层本身拒",
      not validate_structure(r"G:\库\2017\06\2017-06-13")[0])
check("2 藏在日期层更深层拒",
      not validate_structure(r"G:\库\2017\06\20170613\素材\a.mp4")[0])
check("2 无结构拒",
      not validate_structure(r"G:\库\随便\这里\a.mp4")[0])
ok, y, m, d, _ = validate_structure(r"G:\库\年不明\月不明\20170613\a.mp4")
check("2 年月不规整时以日期层反推", ok and (y, m, d) == ("2017", "06", "2017-06-13"))

# ---------------------------------------------------------------
# 3) 防重名
# ---------------------------------------------------------------
ws = tempfile.mkdtemp(prefix="structure_")
dd = os.path.join(ws, "d")
os.makedirs(dd)
check("3 空目录原名", _unique_dest(dd, "a.txt") == os.path.join(dd, "a.txt"))
open(os.path.join(dd, "a.txt"), "w").close()
check("3 重名给_1", _unique_dest(dd, "a.txt") == os.path.join(dd, "a_1.txt"))
open(os.path.join(dd, "a_1.txt"), "w").close()
check("3 _1占了给_2", _unique_dest(dd, "a.txt") == os.path.join(dd, "a_2.txt"))
open(os.path.join(dd, "a_3.txt"), "w").close()
check("3 缺口时取第一个空位_2", _unique_dest(dd, "a.txt") == os.path.join(dd, "a_2.txt"))
check("3 拖入名本身带_3则从_4接",
      _unique_dest(dd, "a_3.txt") == os.path.join(dd, "a_4.txt"))

# ---------------------------------------------------------------
# 4) 库内判断 / 嵌套拦截
# ---------------------------------------------------------------
zone = os.path.join(ws, "zone")
os.makedirs(zone)
check("4 库内算在库里", _already_in_tree(os.path.join(zone, "x"), zone))
check("4 库外不在库里", not _already_in_tree(os.path.join(ws, "d"), zone))
check("4 自己不算在自己里", not _is_inside(zone, zone))

# ---------------------------------------------------------------
# 5) 整体流程：结构落点 + 时间保真 + 整批拒绝 + 跳过 + 重名
# ---------------------------------------------------------------
lib = os.path.join(ws, "lib")
zone2 = os.path.join(ws, "zone2")
os.makedirs(zone2)
f1 = make_src_file(lib, r"2016\03\20160301\a.mp4")
folder = os.path.join(lib, "2016", "03", "2016-03-01", "整包素材")
make_src_file(folder, "内里的b.mp4")
backdate(folder)

# 注意：拖的必须是【直接位于日期层之下】的东西；藏在更深层里的文件
# 要靠拖它的父文件夹一起走 —— 与「视频移动」规则一致
ns["zone_meta"] = {}
_move_structured([f1, folder], ns["status_var"], ns["label"],
                 ns["root_window"], zone2)

p1 = os.path.join(zone2, "2016", "03", "2016-03-01", "a.mp4")
p2 = os.path.join(zone2, "2016", "03", "2016-03-01", "整包素材")
check("5 无横杠统一成横杠落点", os.path.isfile(p1), p1)
check("5 文件夹整棵跟走", os.path.isfile(os.path.join(p2, "内里的b.mp4")), p2)
check("5 源已搬走", not os.path.exists(f1))
check("5 落点创建时间保真", aged(p1))
check("5 落点文件夹创建时间保真", aged(p2))

# 整批拒绝：一个不符，符合的也不动
f3 = make_src_file(lib, r"2018\05\20180501\c.mp4")
bad = make_src_file(lib, r"2018\05\没结构\d.mp4")
ns["toasts"] = []
_move_structured([f3, bad], ns["status_var"], ns["label"],
                 ns["root_window"], zone2)
check("5 不符整批拒·源未动", os.path.exists(f3))
check("5 不符整批拒·符合的也没动",
      not os.path.exists(os.path.join(zone2, "2018", "05", "2018-05-01", "c.mp4")))
check("5 拒绝时弹了说明", len(ns["toasts"]) == 1 and "结构不符" in ns["toasts"][0],
      str(ns.get("toasts")))
check("5 拒绝后 is_processing 复位", ns.get("is_processing") is False)

# 已在库里 -> 静默跳过，不算错
ns["toasts"] = []
_move_structured([p1], ns["status_var"], ns["label"], ns["root_window"], zone2)
check("5 库内静默跳过·没弹错", ns["toasts"] == [] and os.path.exists(p1))

# 重名 -> _1：往同一个日期目录再拖一个同名 a.mp4
f4 = make_src_file(lib, r"2016\03\20160301\a.mp4")
_move_structured([f4], ns["status_var"], ns["label"], ns["root_window"], zone2)
check("5 重名落成_1",
      os.path.isfile(os.path.join(zone2, "2016", "03", "2016-03-01", "a_1.mp4")),
      str(os.listdir(os.path.join(zone2, "2016", "03", "2016-03-01"))))
check("5 搬运后 is_processing 复位", ns.get("is_processing") is False)

shutil.rmtree(ws, ignore_errors=True)

print("=" * 62)
for p in passed:
    print("  [OK] " + p)
for f_ in failed:
    print("  [FAIL] " + f_)
print("=" * 62)
print("通过 %d 项，失败 %d 项" % (len(passed), len(failed)))
sys.exit(1 if failed else 0)
