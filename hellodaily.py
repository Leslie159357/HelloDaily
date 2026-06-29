#!/usr/bin/env python3
"""HelloDaily — 每日 GitHub 开源精选（数据源：HelloGitHub）"""

import urllib.request
import json as json_mod
import os
import re
import glob
import sys
from datetime import date

TRENDING_URL = "https://hellogithub.com/periodical/volume"
OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))


def fetch_hellogithub(volume=122):
    """从 HelloGitHub 某期月刊抓取项目数据"""
    url = f"{TRENDING_URL}/{volume}"
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (compatible; HelloDaily/1.0)",
        "Accept": "text/html",
    })
    try:
        html = urllib.request.urlopen(req, timeout=15).read().decode("utf-8")
    except Exception as e:
        print(f"  ⚠️ 第 {volume} 期请求失败: {e}")
        return []

    # 从 __NEXT_DATA__ 提取 JSON
    m = re.search(r'__NEXT_DATA__"\s*type="application/json">(.+?)</script>', html, re.DOTALL)
    if not m:
        print("⚠️ 无法解析 HelloGitHub 页面数据")
        return []

    data = json_mod.loads(m.group(1))
    try:
        volume_data = data["props"]["pageProps"]["volume"]
        categories = volume_data["data"]
    except (KeyError, TypeError) as e:
        print(f"⚠️ 页面数据结构不符预期: {e}")
        return []

    repos = []
    for cat in categories:
        cat_name = cat.get("category_name", "其他")
        for item in cat.get("items", []):
            desc = item.get("description", "").strip()
            if not desc:
                desc = item.get("description_en", "").strip()
            repos.append({
                "name": item.get("full_name", ""),
                "desc": desc,
                "lang": cat_name,
                "stars": f"{item.get('stars', 0):,}",
                "stars_today": "",
            })
    return repos


def lang_emoji(lang):
    # 去掉 " 项目" 后缀再匹配
    name = lang.replace(" 项目", "").replace("项目", "")
    emoji_map = {
        "Python": "🐍", "JavaScript": "🟨", "TypeScript": "🔷", "Java": "☕",
        "Go": "🔵", "Rust": "🦀", "C++": "⚡", "C": "💠", "Ruby": "💎",
        "Swift": "🍎", "Kotlin": "🟣", "PHP": "🐘", "Shell": "🐚",
        "HTML": "🌐", "CSS": "🎨", "Vue": "💚", "React": "⚛️",
        "人工智能": "🤖", "Skills": "🛠", "其他": "📦", "其它": "📦",
        "C#": "🎯", "Go": "🔵",
    }
    return emoji_map.get(name, "📦")


def get_used_volumes(content_dir):
    """从已有的 content 和 gen 文件中推断已用过的 HelloGitHub 期数"""
    used = set()
    # 从 gen_issue*.py 中提取 "HelloGitHub 第 X 期" 或 "volume/X"
    for f in glob.glob(os.path.join(OUTPUT_DIR, "gen_issue*.py")):
        with open(f, "r", errors="ignore") as fh:
            text = fh.read()
            for m in re.finditer(r'HelloGitHub\s*第\s*(\d+)\s*期', text):
                used.add(int(m.group(1)))
            for m in re.finditer(r'volume/(\d+)', text):
                used.add(int(m.group(1)))
    # 从已有 content 文件中提取 "HelloGitHub 第 X 期"
    for f in glob.glob(os.path.join(content_dir, "HelloDaily-*.md")):
        with open(f, "r", errors="ignore") as fh:
            text = fh.read()
            for m in re.finditer(r'HelloGitHub\s*第\s*(\d+)\s*期', text):
                used.add(int(m.group(1)))
    return used


def generate_markdown(repos, volume):
    today_dt = date.today()
    today = today_dt.isoformat()
    content_dir = os.path.join(OUTPUT_DIR, "content")

    # 计算期号
    from datetime import datetime as dt
    existing = sorted(glob.glob(os.path.join(content_dir, "HelloDaily-*.md")))
    first_date = None
    for f in existing:
        m2 = re.search(r'HelloDaily-(\d{4}-\d{2}-\d{2})', f)
        if m2:
            try:
                fd = date.fromisoformat(m2.group(1))
                if first_date is None or fd < first_date:
                    first_date = fd
            except:
                pass
    if first_date:
        issue_num = (today_dt - first_date).days + 1
    else:
        issue_num = 1

    issue_str = f"第 {issue_num:03d} 期"

    # Group by language
    by_lang = {}
    for r in repos:
        lang = r["lang"] or "其他"
        by_lang.setdefault(lang, []).append(r)

    sorted_langs = sorted(by_lang.keys(), key=lambda l: len(by_lang[l]), reverse=True)

    md = f"# 《HelloDaily》{issue_str}\n"
    md += f"> 兴趣是最好的老师，HelloDaily 帮你找到开源的乐趣！\n"
    md += f"> 本期内容精选自 HelloGitHub 第 {volume} 期\n\n"
    md += f"## 目录\n\n"
    md += f"（点击右上角目录图标）\n\n"
    md += f"## 内容\n"
    md += f"> 以下为本期内容｜每天 09:00 更新\n\n"

    for lang in sorted_langs:
        items = by_lang[lang]
        emoji = lang_emoji(lang)
        md += f"### {emoji} {lang}\n\n"
        for idx, r in enumerate(items, 1):
            stars_str = f"🌟 {r['stars']}" if r['stars'] else ""
            badge = f"{stars_str}" if stars_str else ""
            md += f"{idx}、[{r['name']}](https://github.com/{r['name']})"
            if badge:
                md += f" {badge}"
            md += "\n"
            if r['desc']:
                desc = r['desc'][:200] + "…" if len(r['desc']) > 200 else r['desc']
                md += f"   {desc}\n"
            md += "\n"

    # 导航
    filepath = os.path.join(content_dir, f"HelloDaily-{today}.md")
    all_files = sorted(glob.glob(os.path.join(content_dir, "HelloDaily-*.md")))
    prev_link = ""
    next_link = ""
    for i, f in enumerate(all_files):
        if f == filepath:
            if i > 0:
                prev_name = os.path.basename(all_files[i-1])
                prev_link = f'<a href="{prev_name}">『上一期』</a>'
            if i < len(all_files) - 1:
                next_name = os.path.basename(all_files[i+1])
                next_link = f'<a href="{next_name}">『下一期』</a>'
            break

    md += "\n\n"
    nav_parts = []
    if prev_link:
        nav_parts.append(prev_link)
    nav_parts.append(f'<a href="https://github.com/Leslie159357/HelloDaily">『GitHub』</a>')
    if next_link:
        nav_parts.append(next_link)
    md += f'<p align="center">\n    {" | ".join(nav_parts)}\n</p>\n\n'
    md += "---\n"
    md += '<p align="center">\n'
    md += '    👉 每天 09:00 自动更新 · HelloGitHub 精选 👈<br>\n'
    md += '</p>\n'
    return md, issue_num, today


if __name__ == "__main__":
    content_dir = os.path.join(OUTPUT_DIR, "content")
    os.makedirs(content_dir, exist_ok=True)

    # 选一个没用过的期数
    used = get_used_volumes(content_dir)
    print(f"📚 HelloGitHub 已用期数: {sorted(used) or '无'}")

    # 从 122 开始往后找
    volume = 122
    while volume in used:
        volume += 1

    print(f"📖 正在获取 HelloGitHub 第 {volume} 期...")
    repos = fetch_hellogithub(volume)
    # 往前找不到就往后退
    while not repos and volume < 150:
        volume += 1
        if volume in used:
            continue
        print(f"⚠️ 第 {volume-1} 期不可用，尝试第 {volume} 期...")
        repos = fetch_hellogithub(volume)
    # 还找不到就往前找
    if not repos:
        volume = 122
        while volume in used:
            volume -= 1
        if volume >= 1:
            print(f"⚠️ 往前找到第 {volume} 期...")
            repos = fetch_hellogithub(volume)
    if not repos:
        print("❌ 全部获取失败")
        sys.exit(1)

    print(f"✅ 获取到 {len(repos)} 个项目")

    md, issue_num, today = generate_markdown(repos, volume)
    issue_str = f"第 {issue_num:03d} 期"

    # Save to content dir
    filename = f"HelloDaily-{today}.md"
    filepath = os.path.join(content_dir, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(md)
    print(f"✅ 已保存: {filepath}")

    # Update README
    readme_path = os.path.join(OUTPUT_DIR, "README.md")
    latest_link = f"[**{issue_str} · {today}**](content/{filename})"

    all_issues = sorted(glob.glob(os.path.join(content_dir, "HelloDaily-*.md")), reverse=True)
    entries_per_row = 5
    issue_links = []
    for i, fpath in enumerate(all_issues):
        fname = os.path.basename(fpath)
        num = len(all_issues) - i
        issue_links.append(f"[第 {num:03d} 期](content/{fname})")

    table_rows = []
    for i in range(0, len(issue_links), entries_per_row):
        row = issue_links[i:i+entries_per_row]
        while len(row) < entries_per_row:
            row.append("")
        table_rows.append(f"| {' | '.join(row)} |")

    table_body = "\n".join(table_rows)

    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(f"""<p align="center">
  <img src="https://raw.githubusercontent.com/521xueweihan/img_logo/master/logo/readme.gif"/><br>
  分享 GitHub 上有趣、入门级的开源项目。<br>
  兴趣是最好的老师，HelloDaily 帮你找到开源的乐趣！
</p>

<p align="center">
  <img src="https://img.shields.io/badge/HelloDaily-每日开源精选-ff69b4?style=for-the-badge&logo=github"/><br>
  🌟 每天 09:00 自动推送 HelloGitHub 精选项目<br>
  中文解读 · 按语言分类
</p>

<p align="center">
  <a href="https://github.com/Leslie159357/HelloDaily/stargazers"><img src="https://img.shields.io/github/stars/Leslie159357/HelloDaily?style=popout-square" alt="Stars"></a>
  <a href="https://github.com/Leslie159357/HelloDaily/blob/main/LICENSE"><img src="https://img.shields.io/github/license/Leslie159357/HelloDaily?style=popout-square" alt="License"></a>
  <a href="https://github.com/Leslie159357/HelloDaily/commits/main"><img src="https://img.shields.io/github/last-commit/Leslie159357/HelloDaily?style=popout-square" alt="Last Commit"></a>
  <img src="https://img.shields.io/badge/自动更新-09:00-blue?style=popout-square" alt="Update">
</p>

---

## 最新一期

📅 **[第 {issue_num:03d} 期 · {today}](content/{filename})**

## 往期

| :card_index: | :jack_o_lantern: | :beer: | :fish_cake: | :octocat: |
| ------- | ----- | ------------ | ------ | --------- |
{table_body}

## 关于

每天 09:00 自动抓取 **HelloGitHub** 精选内容，按语言分类，链接 + 🌟 总星数 + 中文解读，推送至仓库。

---

*每天 09:00 自动更新*
""")
    print(f"✅ README 已更新")
    print(f"\n📊 本期概览:")
    by_lang = {}
    for r in repos:
        l = r["lang"] or "其他"
        by_lang[l] = by_lang.get(l, 0) + 1
    for l, c in sorted(by_lang.items(), key=lambda x: -x[1]):
        print(f"   {lang_emoji(l)} {l}: {c} 个项目")
