#!/usr/bin/env python3
"""HelloDaily 第 003 期 - HelloGitHub 第 121 期内容"""

import json, sys, re, os
from datetime import date

output_dir = "/root/HelloDaily/content"
today = "2026-07-01"
issue_num = 3
issue_str = f"第 {issue_num:03d} 期"

# Fetch data from HelloGitHub
import urllib.request
html = urllib.request.urlopen("https://hellogithub.com/periodical/volume/121", timeout=15).read().decode("utf-8")
idx = html.find('"data":[')
start = html.find('[', idx)
depth = 1; i = start + 1
while i < len(html) and depth > 0:
    if html[i] == '[': depth += 1
    elif html[i] == ']': depth -= 1
    i += 1
data = json.loads(html[start:i])

lang_emoji = {
    "C 项目":"💠","C# 项目":"📦","C++ 项目":"⚡","Go 项目":"🔵","JavaScript 项目":"🟨",
    "Kotlin 项目":"🟣","Python 项目":"🐍","Rust 项目":"🦀","Skills":"🧠","Swift 项目":"🍎",
    "人工智能":"🤖","其它":"📦","开源书籍":"📚"
}

md = f"# 《HelloDaily》{issue_str}\n"
md += "> 兴趣是最好的老师，HelloDaily 帮你找到开源的乐趣！\n\n"
md += "## 目录\n\n（点击右上角目录图标）\n\n"
md += "## 内容\n> 以下为本期内容｜每天 09:00 更新\n\n"

for cat in data:
    name = cat["category_name"]
    items = cat["items"]
    emoji = lang_emoji.get(name, "📦")
    md += f"### {emoji} {name}\n\n"
    for idx, item in enumerate(items, 1):
        stars_f = f"{item['stars']:,}"
        desc = item['description'][:150].replace('\n', ' ')
        md += f"{idx}、[{item['full_name']}](https://github.com/{item['full_name']}) 🌟 {stars_f}\n"
        md += f"   {desc}\n\n"

md += '\n<p align="center">\n    <a href="HelloDaily-2026-06-30.md">『上一期』</a> | <a href="https://github.com/Leslie159357/HelloDaily">『GitHub』</a> | <a href="HelloDaily-2026-06-29.md">『下一期』</a>\n</p>\n\n'
md += "---\n"
md += '<p align="center">\n    👉 每天 09:00 自动更新 · GitHub Trending 精选 👈<br>\n</p>\n'

path = os.path.join(output_dir, f"HelloDaily-{today}.md")
with open(path, "w", encoding="utf-8") as f:
    f.write(md)
print(f"✅ 第 003 期已生成 ({len(data)} 分类)")
for c in data:
    print(f"   {c['category_name']}: {len(c['items'])} 个项目")
