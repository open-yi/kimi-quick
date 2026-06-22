# Kimi Quick

按 **F4** 键呼出/隐藏 Kimi 网页弹窗，375×667 移动端视口，始终置顶，全局热键。

## 功能

| 操作 | 说明 |
|------|------|
| F4 | 全局切换窗口显示/隐藏 |
| 拖拽顶部白条 | 移动窗口位置 |
| 关闭按钮 | 退出应用 |
| 托盘图标 | 右键菜单：显示/隐藏、刷新、退出 |
| 启动自动隐藏 | 启动后 2 秒自动隐藏，F4 呼出 |

## 安装

```bash
python -m venv venv
venv\Scripts\pip install pywebview pystray pillow pyinstaller
```

## 打包

```bash
venv\Scripts\python -m PyInstaller --onefile --windowed --icon=kimi_favicon.ico --add-data="kimi_favicon.ico;." --name=KimiQuick kimi.py
```

输出：`dist/KimiQuick.exe`（约 20MB，单文件免安装）

## 部署

1. 复制 `dist/KimiQuick.exe` 到 `C:\`
2. 创建快捷方式到 `shell:startup` 实现开机自启

## 技术栈

- **pywebview**（Edge WebView2）— 内嵌浏览器
- **pystray** — 系统托盘
- **ctypes** — Win32 API（热键、窗口样式、图标、拖拽）
- **PyInstaller** — 打包为单文件 exe

## 文件

```
kimi-tool/
├── kimi.py              # 主程序 (~215 行)
├── kimi_favicon.ico     # 图标
├── start.bat            # 开发启动脚本
├── README.md
├── venv/                # Python 虚拟环境
└── dist/
    └── KimiQuick.exe    # 打包输出
```
