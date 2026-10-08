# Qt 静态资产来源

本目录保存 Qt 使用的资源及从原 Web 界面继承的来源记录。历史资源快照对应仓库版本为 `607f246518b0f41bb7240ba8777751ce25889ff7`（基于 LinuxCNC 2.9.10）。原生 AXIS 的工具栏改绘和生成器现已撤回；Web 界面现已移除，Qt 保留所用资源的许可证与出处，构建不读取已删除目录，也不加载远程 CDN。

## 已改绘的工具栏

以下文件属于该历史快照中的 Lucide 改绘：

```text
tool_estop.gif      tool_power.gif       tool_open.gif
tool_reload.gif     tool_run.gif         tool_step.gif
tool_pause.gif      tool_stop.gif        tool_blockdelete.gif
tool_optpause.gif   tool_zoomin.gif      tool_zoomout.gif
tool_axis_z.gif     tool_axis_z2.gif     tool_axis_x.gif
tool_axis_y.gif     tool_axis_y2.gif     tool_axis_p.gif
tool_rotate.gif     tool_clear.gif       resume_inhibit.gif
```

上游为 [Lucide](https://github.com/lucide-icons/lucide)，源版本 `951813ce76a859d4d8b145366972cbb237147a4e`。原始图标对应关系、尺寸、SVG 和改绘说明分别位于仓库的 [`manifest.json`](https://github.com/Xamber-Software/BetterLinuxCNC/blob/607f246518b0f41bb7240ba8777751ce25889ff7/share/axis/images/toolbar-source/manifest.json) 与 [`README.md`](https://github.com/Xamber-Software/BetterLinuxCNC/blob/607f246518b0f41bb7240ba8777751ce25889ff7/share/axis/images/toolbar-source/README.md)。改绘包括颜色、部分实心形状和 AXIS 专用标记；Qt 不再次改绘这些历史 GIF。

版权与许可证：

- Copyright (c) 2026 Lucide Icons and Contributors — ISC。
- 部分图标源于 Feather：Copyright (c) 2013-present Cole Bemis — MIT。

完整通知已原样保存为本目录的 [TOOLBAR-LICENSE](TOOLBAR-LICENSE)，来源是 [历史 LICENSE](https://github.com/Xamber-Software/BetterLinuxCNC/blob/607f246518b0f41bb7240ba8777751ce25889ff7/share/axis/images/toolbar-source/LICENSE)。适用 ISC and MIT，撤回原生资源不会改变已有副本的授权。GIF 透明边缘按 AXIS `#d9d9d9` 控件背景处理，这些 GIF 的来源记录作为历史说明保留，本目录不包含这些 GIF。当前深色工具栏使用 `BetterCnc.Ui` 中的原创矢量路径。

## 其他 AXIS 图像

```text
axis-16x16.png  axis-24x24.png  axis-32x32.png  axis-48x48.png
banner.gif     close.gif       spindle_ccw.gif spindle_cw.gif
std_error.gif  std_info.gif    std_warning.gif tool_verify.gif
```

这些文件来自相同 `share/axis/images/` 路径。按本仓库 [`debian/copyright`](../../../../../debian/copyright) 的 `Files: *` 归类，适用 `GPL-2+`，即 GPL version 2 或更高版本；版权为 The LinuxCNC Developers 及该文件所列贡献者。全文见仓库 [COPYING](../../../../../COPYING)。本目录目前保留 `axis-48x48.png`；上述历史列表不表示 Qt 包含或使用其余图像。

## 程序样例与界面依据

原 Web 界面的程序样例从 [`share/axis/images/axis.ngc`](https://github.com/Xamber-Software/BetterLinuxCNC/blob/e470d7aa6268a4ff56963cb8e162f2004ba89736/share/axis/images/axis.ngc) 复制，前端中文化时仅翻译了说明性注释，程序指令、参数及行数保持不变；按仓库通用 GPL-2+ 条目记录。`BetterCnc.Catalog` 的 `sampleProgram` 继承此历史样例，不作为生产状态；程序注释明确这是 AXIS splash G-code，不是实际铣削作业。

界面结构参考历史 `share/axis/tcl/axis.tcl` 和 `src/emc/usr_intf/axis/scripts/axis.py`，其中保留的上游版权声明列出 Jeff Epler、Chris Radek，并使用 GPL-2.0-or-later。Qt 界面沿用仓库的 GPL-2.0-or-later 授权。

原 Web 刀路区 SVG 为静态示意；当前 Qt 刀路区根据控制服务解释的线段与实际轨迹绘制。本文对仓库已有来源作记录，不改变各文件的原许可证；分发 Qt 界面时须一并保留适用的许可证和版权通知。
