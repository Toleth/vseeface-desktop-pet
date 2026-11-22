# VSeeFace 桌面透明角色（VSeeFace Desktop Pet）
这种无ui的方式只有在配套的obs才能实现，所以整了一个本机可使用的插件

 ⚠️ 这是一个**非官方的第三方配套插件**，与 VSeeFace 官方无关
 本仓库不包含 VSeeFace 本体、模型或任何素材；VSeeFace 需要用户自行安装

## 首次使用

1. 启动 VSeeFace，加载角色
2. 点窗口右侧的 **「设置」**
3. 设置面板顶部切到 **「常规」（General）**
4. 往下找到 **Spout2 Image Capture Support**，**勾选**
5. 双击 **VSeeFaceDesktopPet.exe**（或从源码运行，见下文）

## 操作方式

| 操作 | 效果 |
|---|---|
| **左键拖动** | 移动角色位置 |
| **右键** | 打开菜单 |
| **托盘图标右键** | 菜单 |

右键菜单项：

- **鼠标穿透** 
- **窗口总在最前** 
- **回到屏幕中央**
- **上下翻转显示**
- **重新连接 VSeeFace**
- **退出**

> 同一个程序只能开一个实例；重复双击会提示"已经在运行"

---

## 常见问题

**弹窗提示「没有检测到 VSeeFace 的 Spout2 输出」**
就是上面第 4 步的开关没勾。勾上后不用管它，会自动连上

**角色显示成一片空白/不显示**
检查 VSeeFace 里是否真的勾了 Spout2；另外确认 VSeeFace 正在渲染角色

**开了"鼠标穿透"之后点不到角色了**
从这个程序的**托盘图标**右键，取消勾选"鼠标穿透"

**角色大小改变**
在 VSeeFace 里调整窗口分辨率或相机位置，本程序的显示尺寸会跟着 Spout2 输出自动变化

**笔记本双显卡（集显 + 独显）上不显示**
Windows 设置 → 系统 → 显示 → 图形设置，把 `VSeeFace.exe` 和 `VSeeFaceDesktopPet.exe` 都设为同一个显卡（建议都用"高性能"），然后重新打开两者

**角色挡住任务栏 / 挡住操作**
右键 → 鼠标穿透；或者把角色拖到屏幕角落。

---

## 从源码运行 / 自行打包

环境要求：Windows 10/11 64 位，Python 3.11+（源码用了 `os.add_dll_directory`，需要 3.8+；SpoutGL 轮子要求 3.11+）。

```bat
pip install -r requirements.txt
python vseeface_desktop.py
```

生成单文件 exe：

```bat
build.bat
```

等价于：

```bat
python -m pip install -r requirements-dev.txt
python -m PyInstaller --noconfirm --onefile --windowed --name VSeeFaceDesktopPet ^
    --collect-all SpoutGL --hidden-import numpy vseeface_desktop.py
```

> 打包注意事项（已写进源码）：单文件模式下 `_spoutgl.pyd` 依赖 `spoutgl.libs` / `numpy.libs`
> 下带哈希名的 DLL，需要用 `os.add_dll_directory()` 注册搜索路径；否则 exe 会启动即退出。

---

## 附带的文件

| 文件 | 说明 |
|---|---|
| `VSeeFaceDesktopPet.exe` | 主程序，双击即用，无需安装（也建议放在 GitHub Releases 里） |
| `vseeface_desktop.py` | 源码 |
| `requirements.txt` / `requirements-dev.txt` | 运行 / 构建依赖 |
| `build.bat` | 一键打包脚本 |
| `LICENSE` | 本项目许可证（MIT） |
| `vsf_pet_config.json` | 运行时自动生成，记住角色位置（不纳入版本控制） |

---

## 许可证与第三方组件

**本项目代码：MIT**（见 `LICENSE`）。可以任意使用、修改、商用、再分发。

本工具依赖以下第三方组件，均为宽松许可证，但**分发二进制（exe）时必须保留其版权与许可声明**：

| 组件 | 用途 | 许可证 | 版权 |
|---|---|---|---|
| [SpoutGL](https://github.com/jlai/Python-SpoutGL) (Jason Lai) | Spout2 的 Python 绑定，含 `Spout.dll` / `_spoutgl.pyd` | BSD-3-Clause | Jason Lai |
| [Spout2 SDK](https://github.com/leadedge/Spout2) (Lynn Jarvis / leadedge) | `Spout.dll` 对应的底层帧共享库 | BSD-2-Clause | Lynn Jarvis |
| [numpy](https://numpy.org/) | Alpha 预乘与像素缓冲 | BSD-3-Clause（含 MIT / 0BSD / Zlib / CC0 组件） | NumPy Developers |
| [Pillow](https://python-pillow.org/) | 图像处理 | MIT-CMU | Pillow contributors |
| [PyInstaller](https://pyinstaller.org/) | 仅用于构建，不随程序分发其功能代码 | GPLv2-or-later + bootloader 例外（允许打包和分发非自由/商业程序） | PyInstaller contributors |

> 说明：`VSeeFaceDesktopPet.exe` 内打包了上述 BSD / MIT 系组件的二进制文件
> 若把 exe 上传到 GitHub Releases，请**随附本文件的「许可证与第三方组件」章节**或一份
> `THIRD_PARTY_NOTICES`，以满足 BSD 许可证"二进制分发须保留版权声明"的要求
>
> VSeeFace 本身是第三方软件，本仓库不分发其任何代码或资源；本工具仅接收它输出的
> Spout2 画面。「VSeeFace」名称仅用于说明兼容关系，不代表官方背书

---

## 系统要求

Windows 10 / 11，64 位。
