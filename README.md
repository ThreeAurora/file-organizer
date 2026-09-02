# 文件归档器

Windows 桌面文件归档工具：把文件拖到窗口分区上，按规则（年/月、ctime/mtime 时间模式、复制/移动）自动归档到目标目录。附带 Everything 搜索联动、分区配色与重命名、窗口状态记忆、高 DPI 适配等。

- 技术栈：Python + tkinter + tkinterdnd2（拖拽），ctypes 直调 Win32 API（标题栏激活态、DragAcceptFiles）
- 打包：PyInstaller 单文件 exe（`文件归档器.spec`，内嵌 icon.ico，UPX 压缩）
- 运行日志：`drop.log`（启动/拖放初始化记录）

## 构建

```bash
pyinstaller 文件归档器.spec
```

产物为 `dist/文件归档器.exe`（`build/`、`dist/`、`__pycache__/` 不入库，可再生）。

## 关于本仓库的历史说明

本项目曾在 Claude Code 中开发，但其会话编辑记录未能找回（已检索本地全部 AI 会话日志，无指向本项目的 Edit/Write 事件）。因此本仓库**以现状存档形式建立**，无法重建逐次提交历史。据文件时间戳可推断的开发脉络：

| 时间（2026 年） | 事件 |
|---|---|
| 06-29 | icon.ico 图标制作 |
| 07-04 23:37 | drop.log 最后运行记录（拖放初始化正常） |
| 07-05 00:27–00:29 | 文件归档器.py 最后修改 → .spec 更新 → 打包 dist/文件归档器.exe |

即：开发跨越 2026-06 下旬至 07-05 凌晨，以一次完整的打包收尾。
