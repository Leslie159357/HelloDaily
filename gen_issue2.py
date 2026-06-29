#!/usr/bin/env python3
"""HelloDaily — 从 HelloGitHub 偷一期内容做示例"""

import json, sys, re, os
from datetime import date

today = "2026-06-30"
issue_num = 2
issue_str = f"第 {issue_num:03d} 期"

# HelloGitHub 第 123 期的数据
data = [
    {"name":"C 项目","items":[{"name":"keyd","full_name":"rvaiya/keyd","stars":5609,"desc":"Linux 系统级改键工具。基于内核输入层实现，配置在 X11、Wayland 和 TTY 终端中均可生效。支持按下长按设置不同动作、自定义按键组合，以及为不同键盘单独配置按键映射规则。"},{"name":"mbedtls","full_name":"Mbed-TLS/mbedtls","stars":6732,"desc":"灵活易用的 TLS 加密库，体积小巧易于移植，适用于物联网和嵌入式系统等资源有限的设备。可实现加密原语、X.509 证书操作以及 SSL/TLS 和 DTLS 协议。"}]},
    {"name":"C# 项目","items":[{"name":"PaperTodo","full_name":"snownico0722/PaperTodo","stars":300,"desc":"极简的 Windows 桌面便签工具。每张便签是独立无边框浮动窗口，无主窗口无账号无分类管理，内容自动保存。支持待办纸和笔记纸两种形态，可折叠成置顶小胶囊。"}]},
    {"name":"C++ 项目","items":[{"name":"luanti","full_name":"luanti-org/luanti","stars":13034,"desc":"开源体素游戏引擎，可以用 Lua 快速做出自己的 3D 方块游戏。内置内容商店可直接下载社区模组，支持单人局域网和多人联机，可在 Windows、macOS、Linux 和 Android 上运行。"},{"name":"SpeedyNote","full_name":"alpha-liu-01/SpeedyNote","stars":1244,"desc":"专为低成本设备优化的跨平台手写笔记应用，目标是在老旧平板上实现接近 iPad 的书写体验。支持压感书写、多图层、PDF 批注和手写 OCR。"}]},
    {"name":"Go 项目","items":[{"name":"chinese-poetry-api","full_name":"palemoky/chinese-poetry-api","stars":908,"desc":"开箱即用的中国古诗词 API 服务，收录唐诗宋词元曲等近 40 万首作品。提供 REST API 和 GraphQL 接口，支持全文搜索、IP 限流和 Docker 一键部署。"},{"name":"fight-the-landlord","full_name":"palemoky/fight-the-landlord","stars":338,"desc":"终端里的斗地主游戏，支持联网对战、房间匹配、断线重连。集成了快手开源的 DouZero 斗地主 AI，可作为机器人补位或对战。"},{"name":"gopass","full_name":"gopasspw/gopass","stars":6949,"desc":"专为团队设计的命令行密码管理器。默认用 GPG 加密和 Git 管理凭据，可通过 Git 仓库在多设备和团队之间同步密码密钥与证书。"},{"name":"tinyauth","full_name":"tinyauthapp/tinyauth","stars":7527,"desc":"极简身份认证中间件，通过 Docker 一键部署，可为任何 Web 应用添加 OAuth 登录。无需修改现有代码，无缝集成 Traefik、Caddy、Nginx 等反向代理。"}]},
    {"name":"JavaScript 项目","items":[{"name":"emdash","full_name":"emdash-cms/emdash","stars":10940,"desc":"基于 Astro 构建的无服务器 CMS，可作为 WordPress 替代品。支持 WordPress 导入、可视化编辑、全文搜索、定时发布，直接运行在 Cloudflare 或本地 Node.js 上。"},{"name":"r2-web","full_name":"vikiboss/r2-web","stars":229,"desc":"纯前端的 Cloudflare R2 文件管理器，打开网页输入凭证就能管理桶里的文件。内置图片视频音频文本预览，支持拖拽上传和图片压缩。"},{"name":"react-scan","full_name":"aidenybai/react-scan","stars":21411,"desc":"自动发现 React 应用性能问题的可视化调试工具。无需改代码，加个 script 标签就能高亮显示不必要的重渲染，适用于 React、Next.js、Vite 等项目。"},{"name":"tiny-world-builder","full_name":"jasonkneen/tiny-world-builder","stars":1252,"desc":"基于 Three.js 的 3D 体素世界编辑器，类似迷你版《我的世界》。打开网页就能搭地形修道路盖房子，支持本地保存和导入导出。"},{"name":"tolaria","full_name":"refactoringhq/tolaria","stars":17091,"desc":"基于 Git 的本地 Markdown 知识库桌面应用。每个知识库即一个 Git 仓库，天然拥有版本历史。内置 MCP 服务器，支持 Claude Code、Codex 等 AI 工具直接读写。"}]},
    {"name":"Kotlin 项目","items":[{"name":"shiguangschedule","full_name":"XingHeYuZhuan/shiguangschedule","stars":308,"desc":"面向中国高校师生的 Android 课程表，可通过适配脚本一键导入教务系统数据。支持今日课表、桌面小组件、上课自动静音或开启勿扰模式。"}]},
    {"name":"Python 项目","items":[{"name":"ASCILINE","full_name":"YusufB5/ASCILINE","stars":2178,"desc":"跨平台实时 ASCII 视频渲染引擎，30 FPS 流畅播放。支持 URL 直接播放、音视频同步，无需 GPU 即可运行，把视频变成字符流。"},{"name":"black","full_name":"psf/black","stars":41586,"desc":"Python 官方代码格式化工具，一条命令统一代码风格。配置少结果可重现，彻底消除团队的代码风格之争。"},{"name":"mpmath","full_name":"mpmath/mpmath","stars":1103,"desc":"任意精度的 Python 数学库，支持求根、线性代数、微积分、复数和实数运算。处理普通浮点数不够用的高精度计算场景。"},{"name":"Scrapling","full_name":"D4Vinci/Scrapling","stars":66721,"desc":"自适应 Python 爬虫框架，网页改版后自动重新定位目标元素。内置抓取器支持多会话并发和断点续爬，集成 MCP 服务。"},{"name":"winpodx","full_name":"kernalix7/winpodx","stars":1332,"desc":"在 Linux 上运行 Windows 应用的工具。后台用容器起 Windows 系统，通过 FreeRDP 把每个应用变成独立 Linux 窗口，支持固定任务栏和文件关联。"}]},
    {"name":"Rust 项目","items":[{"name":"llmfit","full_name":"AlexsJones/llmfit","stars":28709,"desc":"自动检测本机硬件并推荐适合本地运行的大模型。从质量速度适配度等维度给模型打分排序，支持 Ollama、llama.cpp、MLX、vLLM 等主流推理环境。"},{"name":"rerun","full_name":"rerun-io/rerun","stars":10995,"desc":"专为机器人和物理 AI 打造的多模态数据可视化平台。支持图像、点云、时序数据等传感器数据，内置实时查看器支持回放和多传感器对比。"},{"name":"smolvm","full_name":"smol-machines/smolvm","stars":3981,"desc":"亚秒级冷启动虚拟机管理工具，冷启动不到一秒。兼容 Docker 镜像，支持将虚拟机打包成单个可执行文件方便迁移。"}]},
    {"name":"Skills","items":[{"name":"academic-research-skills","full_name":"Imbad0202/academic-research-skills","stars":35035,"desc":"面向学术研究的 Claude Code 技能包，把查文献、引用验证、数据核查等交给 AI 处理。让你专注于提出问题和解读结论。"},{"name":"ponytail","full_name":"DietrichGebert/ponytail","stars":64069,"desc":"让 AI 编程助手少写代码，防止过度工程化。可减少约 54% 代码量、20% 花费和 27% 时间。"},{"name":"stop-slop","full_name":"hardikpandya/stop-slop","stars":12774,"desc":"去掉 AI 味的写作技能包，让模型在生成润色时主动规避套路句式、商业黑话、无意义金句。"},{"name":"text-to-cad","full_name":"earthtojake/text-to-cad","stars":7118,"desc":"一句话生成 CAD 模型的技能包。支持自然语言或参考图片生成 CAD 模型，可导出 STL、3MF、GLB 等格式。"}]},
    {"name":"Swift 项目","items":[{"name":"Atoll","full_name":"Ebullioscopic/Atoll","stars":2369,"desc":"把 MacBook 刘海变成灵动岛的 macOS 工具。支持 Apple Music 控制、CPU/GPU/内存监控、计时器、剪贴板历史和日历预览。"},{"name":"MacTools","full_name":"ggbond268/MacTools","stars":233,"desc":"住在菜单栏里的 macOS 工具集合。支持防休眠、自动隐藏 Dock、系统静音、Xcode 清理、弹出磁盘、清空废纸篓等功能。"}]},
    {"name":"人工智能","items":[{"name":"CapsWriter-Offline","full_name":"HaujetZhao/CapsWriter-Offline","stars":5758,"desc":"完全离线的语音输入工具，按住 CapsLock 说话松开转文字。支持实时语音识别、音频转录、热词替换，录音全保存在本地。"},{"name":"GOD","full_name":"XiaoLuoLYG/GOD","stars":641,"desc":"本地优先的多智能体模拟和实时操控平台。支持暂停回放、注入干预指令、向全体成员提问，一键重置模拟世界。"},{"name":"OpenMAIC","full_name":"THU-MAIC/OpenMAIC","stars":18906,"desc":"清华团队开发的多智能体互动课堂平台。AI 老师和智能体同学实时授课讨论，支持白板绘图、语音合成、3D 可视化和在线编程。"},{"name":"train-llm-from-scratch","full_name":"FareedKhan-dev/train-llm-from-scratch","stars":7587,"desc":"从零训练大语言模型的实战教程。用 PyTorch 从底层实现 Transformer、预训练、监督微调和评测的完整流程。"},{"name":"vllm-omni","full_name":"vllm-project/vllm-omni","stars":5303,"desc":"vLLM 官方开源的全模态推理框架，支持图像视频音频的输入生成。同时支持自回归模型和扩散 Transformer 等非自回归模型。"}]},
    {"name":"其它","items":[{"name":"Echo-Loop","full_name":"echo-loop/Echo-Loop","stars":1073,"desc":"专注于英语听说训练的应用，把一段音频从陌生练到听懂会说。支持逐句精听、跟读评分、段落复述，生词存入闪卡复习。"},{"name":"micro-radar","full_name":"AnthonySturdy/micro-radar","stars":378,"desc":"基于 ESP32-C3 的桌面航班雷达，通过 Wi-Fi 从 OpenSky API 获取附近实时航班数据，显示在 1.28 寸圆形屏幕上。"},{"name":"optocamzero","full_name":"dorukkumkumoglu/optocamzero","stars":533,"desc":"基于 Raspberry Pi Zero 自制的迷你口袋数码相机。1.4 寸 LCD 屏幕，支持 2592×2592 像素拍摄、GIF 录制和 Wi-Fi 传输。"},{"name":"tab-harbor","full_name":"V-IOLE-T/tab-harbor","stars":464,"desc":"Chrome 新标签页工作台插件，自动按域名分组整理标签页。支持手动分组、快捷链接、会话保存恢复和一键清理重复标签。"}]}
]

lang_emoji = {
    "C 项目":"💠","C# 项目":"📦","C++ 项目":"⚡","Go 项目":"🔵","JavaScript 项目":"🟨","Kotlin 项目":"🟣",
    "Python 项目":"🐍","Rust 项目":"🦀","Skills":"🧠","Swift 项目":"🍎","人工智能":"🤖","其它":"📦"
}

md = f"# 《HelloDaily》{issue_str}\n"
md += f"> 兴趣是最好的老师，HelloDaily 帮你找到开源的乐趣！\n\n"
md += f"## 目录\n\n（点击右上角目录图标）\n\n"
md += f"## 内容\n> 以下为本期内容｜每天 09:00 更新\n\n"

for cat in data:
    name = cat["name"]
    items = cat["items"]
    emoji = lang_emoji.get(name, "📦")
    md += f"### {emoji} {name}\n\n"
    for idx, item in enumerate(items, 1):
        stars_f = f"{item['stars']:,}"
        md += f"{idx}、[{item['full_name']}](https://github.com/{item['full_name']}) 🌟 {stars_f}\n"
        md += f"   {item['desc']}\n\n"

md += f'\n<p align="center">\n    <a href="HelloDaily-2026-06-29.md">『上一期』</a> | <a href="https://github.com/Leslie159357/HelloDaily">『GitHub』</a>\n</p>\n\n'
md += "---\n"
md += '<p align="center">\n    👉 每天 09:00 自动更新 · GitHub Trending 精选 👈<br>\n</p>\n'

path = "/root/HelloDaily/content/HelloDaily-2026-06-30.md"
with open(path, "w", encoding="utf-8") as f:
    f.write(md)
print(f"✅ 已写入 {path}")
