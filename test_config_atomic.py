# -*- coding: utf-8 -*-
"""配置健壮性测试：复现今晚「config.json 被清成 0 字节 → 弹保存失败」的场景，
验证修复后能否自愈。从源码里抠出三个函数在隔离命名空间执行，避开 tkinter。"""
import os, sys, json, tempfile, shutil, re

SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), '文件归档器.py')

src = open(SRC, encoding='utf-8', newline='').read()

# 抠出需要的函数
def grab(name, src):
    i = src.find(f'def {name}(')
    if i < 0:
        raise SystemExit(f'找不到 {name}')
    rest = src[i:]
    m = re.search(r'\n(?=def |\n# )', rest[10:])
    return rest[:10 + m.start()] if m else rest

ns = {'os': os, 'json': json, 'shutil': shutil}
for fn in ('_atomic_write_json', '_read_json_with_recovery'):
    code = grab(fn, src)
    exec(code, ns)
    print(f'已装载 {fn} ({len(code.splitlines())} 行)')

tmpdir = tempfile.mkdtemp(prefix='cfgtest_')
CFG = os.path.join(tmpdir, 'config.json')
GOOD = {
    'zones': [{'name': f'格{i}', 'path': f'G:/p{i}/', 'color': '#0d9488'} for i in range(9)],
    'window': {'x': 1, 'y': 2, 'width': 3, 'height': 4},
    'settings': {'use_copy': False, 'use_keep_time': True},
}

passed = failed = 0
def check(desc, cond, extra=''):
    global passed, failed
    if cond:
        passed += 1; print(f'  [OK] {desc}')
    else:
        failed += 1; print(f'  [NG] {desc} {extra}')

print('\n' + '='*62)
print('组 1：原子写基本功能')
print('='*62)
ns['_atomic_write_json'](CFG, GOOD)
check('文件已生成', os.path.exists(CFG))
check('内容是合法 JSON', json.loads(open(CFG, encoding='utf-8').read()) == GOOD)
check('没有残留 .tmp', not os.path.exists(CFG + '.tmp'))

print('\n' + '='*62)
print('组 2：复现今晚的故障 —— 配置被清成 0 字节')
print('='*62)
# 先造一个正常配置 + 它的 .bak
ns['_atomic_write_json'](CFG, GOOD)
check('正式文件正常', json.loads(open(CFG, encoding='utf-8').read()) == GOOD)
# 模拟「写一半被强杀」：把正式文件清空
open(CFG, 'w').close()
check('已模拟损坏（0 字节）', os.path.getsize(CFG) == 0)
# 现在读它，应该能自愈
data, note = ns['_read_json_with_recovery'](CFG)
check('读到了数据（从 .bak 自愈）', data is not None, f'note={note}')
check('自愈内容与原数据一致', data == GOOD, f'got={data}')
check('正式文件已被写回', os.path.getsize(CFG) > 0)
check('写回内容正确', json.loads(open(CFG, encoding='utf-8').read()) == GOOD)
print(f'   （自愈备注：{note}）')

print('\n' + '='*62)
print('组 3：坏数据但无备份可用（极端）')
print('='*62)
CFG2 = os.path.join(tmpdir, 'no_bak.json')
open(CFG2, 'w').write('{bad json')
data2, note2 = ns['_read_json_with_recovery'](CFG2)
check('返回 None 而不是崩溃', data2 is None, f'got={data2}')
check('备注说明原因', bool(note2))
print(f'   （备注：{note2[:70]}）')

print('\n' + '='*62)
print('组 4：原子写的「中间态不破坏正式文件」')
print('='*62)
ns['_atomic_write_json'](CFG, GOOD)
before = open(CFG, encoding='utf-8').read()
# 故意让序列化失败（塞一个不可序列化对象）
class Bad: pass
try:
    ns['_atomic_write_json'](CFG, {'x': Bad()})
    check('应当抛异常', False)
except TypeError:
    check('序列化失败抛出异常', True)
after = open(CFG, encoding='utf-8').read()
check('正式文件未被破坏', before == after)
check('无残留 .tmp', not os.path.exists(CFG + '.tmp'))

print('\n' + '='*62)
print('组 5：.bak 是上一版，可回退')
print('='*62)
V1 = dict(GOOD); V1['tag'] = 'v1'
V2 = dict(GOOD); V2['tag'] = 'v2'
ns['_atomic_write_json'](CFG, V1)
ns['_atomic_write_json'](CFG, V2)
bak = json.loads(open(CFG + '.bak', encoding='utf-8').read())
cur = json.loads(open(CFG, encoding='utf-8').read())
check('正式文件是 v2', cur.get('tag') == 'v2')
check('.bak 保留的是 v1', bak.get('tag') == 'v1')

print('\n' + '='*62)
print('组 6：load_settings 的「附带结构」启动默认')
print('='*62)
ns['DEFAULT_EV_PATH'] = ''
ns['CONFIG_PATH'] = CFG
exec(grab('load_settings', src), ns)
load_settings = ns['load_settings']

# 全新安装：没有配置文件，也要默认开启
if os.path.exists(CFG):
    os.remove(CFG)
s = load_settings()
check('无配置时 keep_time_default 为真', s.get('keep_time_default') is True,
      f'got={s.get("keep_time_default")}')
check('无配置时记录值 use_keep_time 为假', s.get('use_keep_time') is False)

# 升级上来的老配置：settings 里没有这个键
ns['_atomic_write_json'](CFG, {'settings': {'use_copy': False}})
s = load_settings()
check('老配置缺键时仍默认开启', s.get('keep_time_default') is True)

# 用户显式关掉默认开启
ns['_atomic_write_json'](CFG, {'settings': {'keep_time_default': False,
                                            'use_keep_time': True}})
s = load_settings()
check('显式关掉后读到 False', s.get('keep_time_default') is False)
check('关掉后 use_keep_time 仍按记录值读出', s.get('use_keep_time') is True)

print('\n' + '='*62)
print(f'通过 {passed} 项，失败 {failed} 项')
print('='*62)
shutil.rmtree(tmpdir, ignore_errors=True)
sys.exit(1 if failed else 0)
