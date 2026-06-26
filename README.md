# Kimi Quick

F4 一键呼出 Kimi 的 Windows 桌面工具。375×667 移动端视口，始终置顶，可拖拽，系统托盘常驻。单文件 exe，免安装，开机自启。

## 功能

│ 操作 │ 说明 │
│------│------│
│ F4 │ 全局切换窗口显示/隐藏 │
│ 拖拽顶部标题栏 │ 移动窗口位置 │
│ 标题栏按钮 │ 上一页、刷新、在浏览器打开、Bing、Google │
│ Kimi 图标 │ 点击回到 Kimi 首页 │
│ 托盘图标 │ 右键菜单：显示/隐藏、刷新、退出 │
│ 启动自动隐藏 │ 启动后 2 秒自动隐藏，F4 呼出 │
│ 鼠标滚轮 │ 滚动页面（模拟触屏滚动） │
│ Ctrl+C/V │ 复制粘贴文字 │
│ 右键菜单 │ 支持上下文菜单 │

## 下载

从 [Releases](../../releases) 下载 `KimiQuick.exe`，单文件免安装，双击运行。

## 开发

```bash
python -m venv venv
venv\Scripts\pip install -r requirements.txt
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
├── kimi.py              # 主程序 (~330 行)
├── kimi_favicon.ico     # 图标
├── requirements.txt
└── README.md
```
