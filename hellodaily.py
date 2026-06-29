#!/usr/bin/env python3
"""HelloDaily — 每日 GitHub 开源精选"""

import urllib.request
import json
import os
import re
import glob
from datetime import date
from html.parser import HTMLParser

TRENDING_URL = "https://github.com/trending"
OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))

class TrendingParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.repos = []
        self.in_article = False
        self.current = {}
        self.in_h2 = False
        self.in_desc = False
        self.in_p = False
        self.in_lang = False
        self.in_stars = False
        self.in_fork = False
        self._tag_stack = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self._tag_stack.append(tag)

        # Article = repo card
        if tag == "article":
            self.in_article = True
            self.current = {"name": "", "desc": "", "lang": "", "stars": "", "forks": "", "stars_today": ""}

        if not self.in_article:
            return

        # Repo name: h2 > a
        if tag == "h2":
            self.in_h2 = True
        if tag == "p" and self.in_article and not self.in_h2:
            self.in_desc = True
            self._desc_chars = ""

    def handle_data(self, data):
        if not self.in_article:
            return
        if self.in_h2:
            self.current["name"] = data.strip()
        if self.in_desc:
            self._desc_chars = self._desc_chars + data.strip() + " "

        # Language spans and star counts - skip complex parsing, read the HTML directly
        # Alternative: use regex-based approach on raw HTML

    def handle_endtag(self, tag):
        if tag == "article" and self.in_article:
            self.in_article = False
            name = self.current.get("name", "").strip()
            if name and "/" in name:
                # Clean up
                name = re.sub(r'\s+', ' ', name).strip()
                desc = self._desc_chars.strip() if hasattr(self, '_desc_chars') else ""
                desc = re.sub(r'\s+', ' ', desc).strip()
                self.current["name"] = name
                self.current["desc"] = desc
                self.repos.append(dict(self.current))
            self.current = {}

        if tag == self._tag_stack[-1]:
            self._tag_stack.pop()
        if tag == "h2":
            self.in_h2 = False
        if tag == "p" and self.in_desc:
            self.in_desc = False


def fetch_trending(language=""):
    """Fetch trending repos using a simpler regex approach"""
    url = f"{TRENDING_URL}/{language}" if language else TRENDING_URL
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (compatible; HelloDaily/1.0)",
        "Accept": "text/html",
    })
    html = urllib.request.urlopen(req, timeout=15).read().decode("utf-8")

    repos = []
    # Find all repo cards
    articles = re.split(r'<article', html)[1:]

    for art in articles:
        # Repo name
        name_match = re.search(r'h2[^>]*>.*?<a[^>]*href="/([^"]+)"', art, re.DOTALL)
        if not name_match:
            continue
        full_name = name_match.group(1).strip()
        owner, repo_name = full_name.split("/", 1) if "/" in full_name else (full_name, "")

        # Description
        desc_match = re.search(r'<p[^>]*class="[^"]*col-9[^"]*color-fg-muted[^"]*"[^>]*>(.*?)</p>', art, re.DOTALL)
        desc = ""
        if desc_match:
            desc = re.sub(r'<[^>]+>', '', desc_match.group(1)).strip()
            desc = desc.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&#39;", "'").replace("&quot;", '"')

        # Language
        lang_match = re.search(r'<span[^>]*itemprop="programmingLanguage"[^>]*>(.*?)</span>', art, re.DOTALL)
        lang = lang_match.group(1).strip() if lang_match else ""

        # Stars (total) - try multiple patterns
        stars = ""
        for s_pattern in [
            r'<a[^>]*href="/' + re.escape(full_name) + r'/stargazers"[^>]*>.*?<strong>(.*?)</strong>',
            r'<a[^>]*href="/' + re.escape(full_name) + r'/stargazers"[^>]*>.*?([\d,]+)\s*</a>',
            r'star-count[^>]*>[\s\n]*([\d,]+)',
            r'aria-label="[^"]*([\d,]+)\s*star',
        ]:
            s_match = re.search(s_pattern, art, re.DOTALL)
            if s_match:
                stars = s_match.group(1).strip().replace(",", "")
                if stars.isdigit():
                    # format with commas
                    stars = f"{int(stars):,}"
                    break

        # Stars today
        today_match = re.search(r'<span[^>]*class="[^"]*d-inline-block[^"]*float-sm-right[^"]*"[^>]*>.*?([\d,]+)\s*stars\s*today', art, re.DOTALL)
        stars_today = ""
        if today_match:
            stars_today = today_match.group(1).strip()
        if not stars_today:
            # Alternative pattern
            today_match2 = re.search(r'([\d,]+)\s*stars\s*(today|this month)', art, re.DOTALL)
            if today_match2:
                stars_today = today_match2.group(1).strip()

        repos.append({
            "name": full_name,
            "desc": desc,
            "lang": lang,
            "stars": stars,
            "stars_today": stars_today,
        })

    return repos


def translate_descriptions(repos):
    """Translate English descriptions to Chinese using LLM API (SiliconFlow/deepseek)"""
    import urllib.parse, json as json_mod

    api_key = os.environ.get("OPENAI_API_KEY", "")
    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.siliconflow.cn/v1")
    if not api_key:
        return repos  # no key, skip translation

    # Build prompt with all descriptions
    lines = []
    for i, r in enumerate(repos):
        if r["desc"]:
            # Strip leading emojis from raw desc
            clean_desc = re.sub(r'^[^\w\d]*', '', r["desc"]).strip()
            lines.append(f"{i+1}. {clean_desc}")

    if not lines:
        return repos

    prompt = """为以下每个GitHub项目写一段30-60字的中文简介，要求：
- 说明项目是做什么的
- 用通俗语言解释核心功能/使用场景
- 读起来自然流畅，像编辑写的推荐语

按以下格式输出：
1. 简介1
2. 简介2
...

项目列表：
""" + "\n".join(lines)

    data = json_mod.dumps({
        "model": "deepseek-ai/DeepSeek-V3",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "max_tokens": 4096,
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }
    )
    try:
        resp = urllib.request.urlopen(req, timeout=30).read().decode("utf-8")
        result = json_mod.loads(resp)
        text = result["choices"][0]["message"]["content"]

        # Parse translations back into repos
        for line in text.strip().split("\n"):
            line = line.strip()
            if not line or "." not in line:
                continue
            idx_part = line.split(".")[0].strip()
            if not idx_part.isdigit():
                continue
            idx = int(idx_part) - 1
            if 0 <= idx < len(repos):
                trans = ".".join(line.split(".")[1:]).strip()
                # Remove leading number if any
                if trans and repos[idx]["desc"]:
                    repos[idx]["desc"] = trans[:200]  # keep it concise
    except Exception as e:
        print(f"⚠️ 翻译失败: {e}，使用原始英文描述")

    return repos


def lang_emoji(lang):
    emoji_map = {
        "Python": "🐍", "JavaScript": "🟨", "TypeScript": "🔷", "Java": "☕",
        "Go": "🔵", "Rust": "🦀", "C++": "⚡", "C": "💠", "Ruby": "💎",
        "Swift": "🍎", "Kotlin": "🟣", "PHP": "🐘", "Shell": "🐚",
        "HTML": "🌐", "CSS": "🎨", "Vue": "💚", "React": "⚛️",
    }
    return emoji_map.get(lang, "📦")


def generate_markdown(repos):
    today = date.today().isoformat()
    content_dir = os.path.join(OUTPUT_DIR, "content")

    # 计算期号: 从已有 content 文件推断
    import glob
    existing = sorted(glob.glob(os.path.join(content_dir, "HelloDaily-*.md")))
    issue_num = len(existing)  # 已有文件数 = 当前期号
    if issue_num == 0:
        issue_num = 1

    issue_str = f"第 {issue_num:03d} 期"

    # Group by language
    by_lang = {}
    for r in repos:
        lang = r["lang"] or "其他"
        by_lang.setdefault(lang, []).append(r)

    # Sort languages by repo count
    sorted_langs = sorted(by_lang.keys(), key=lambda l: len(by_lang[l]), reverse=True)

    md = f"# 《HelloDaily》{issue_str}\n"
    md += f"> 兴趣是最好的老师，HelloDaily 帮你找到开源的乐趣！\n\n"
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
            today_str = f" +{r['stars_today']}/日" if r['stars_today'] else ""
            badge = f"{stars_str}{today_str}" if (stars_str or today_str) else ""
            md += f"{idx}、[{r['name']}](https://github.com/{r['name']})"
            if badge:
                md += f" {badge}"
            md += "\n"
            if r['desc']:
                desc = r['desc'][:200] + "…" if len(r['desc']) > 200 else r['desc']
                md += f"   {desc}\n"
            md += "\n"

    # 上一期/下一期 导航
    filepath = os.path.join(content_dir, f"HelloDaily-{today}.md")
    all_files = sorted(glob.glob(os.path.join(content_dir, "HelloDaily-*.md")))
    prev_link = ""
    next_link = ""
    for i, f in enumerate(all_files):
        if f == filepath:
            if i > 0:
                prev_name = os.path.basename(all_files[i-1])
                prev_num = i  # 第 {i} 期
                prev_link = f'<a href="{prev_name}">『上一期』</a>'
            if i < len(all_files) - 1:
                next_name = os.path.basename(all_files[i+1])
                next_num = i + 2  # 第 {i+2} 期
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
    md += f'<p align="center">\n'
    md += f'    👉 每天 09:00 自动更新 · GitHub Trending 精选 👈<br>\n'
    md += f'</p>\n'
    return md, issue_num, today


if __name__ == "__main__":
    print("🌐 正在获取 GitHub Trending...")
    repos = fetch_trending()
    print(f"✅ 获取到 {len(repos)} 个项目")

    print("🌏 正在翻译中文简介...")
    repos = translate_descriptions(repos)
    print(f"✅ 翻译完成")

    md, issue_num, today = generate_markdown(repos)
    issue_str = f"第 {issue_num:03d} 期"

    # Save to content dir
    content_dir = os.path.join(OUTPUT_DIR, "content")
    os.makedirs(content_dir, exist_ok=True)
    filename = f"HelloDaily-{date.today().isoformat()}.md"
    filepath = os.path.join(content_dir, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(md)
    print(f"✅ 已保存: {filepath}")

    # Update README
    readme_path = os.path.join(OUTPUT_DIR, "README.md")
    latest_link = f"[**{issue_str} · {today}**](content/{filename})"

    # 构建往期表格行
    entries_per_row = 5
    table_rows = []
    # 获取所有已有期号
    all_issues = sorted(glob.glob(os.path.join(content_dir, "HelloDaily-*.md")), reverse=True)
    issue_links = []
    for i, fpath in enumerate(all_issues):
        fname = os.path.basename(fpath)
        # 期号按文件数倒序
        issue_num = len(all_issues) - i
        issue_links.append(f"[第 {issue_num:03d} 期](content/{fname})")

    # 按 5 列分组
    for i in range(0, len(issue_links), entries_per_row):
        row = issue_links[i:i+entries_per_row]
        # 补齐空单元格
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
  🌟 每天 09:00 自动推送 GitHub Trending 精选项目<br>
  链接 + 中文解读 · 按语言分类
</p>

<p align="center">
  <a href="https://github.com/Leslie159357/HelloDaily/stargazers"><img src="https://img.shields.io/github/stars/Leslie159357/HelloDaily?style=popout-square" alt="Stars"></a>
  <a href="https://github.com/Leslie159357/HelloDaily/blob/main/LICENSE"><img src="https://img.shields.io/github/license/Leslie159357/HelloDaily?style=popout-square" alt="License"></a>
  <a href="https://github.com/Leslie159357/HelloDaily/commits/main"><img src="https://img.shields.io/github/last-commit/Leslie159357/HelloDaily?style=popout-square" alt="Last Commit"></a>
  <img src="https://img.shields.io/badge/自动更新-09:00-blue?style=popout-square" alt="Update">
</p>

---

## 最新一期

📅 **[{issue_str} · {today}](content/{filename})**

## 往期

| :card_index: | :jack_o_lantern: | :beer: | :fish_cake: | :octocat: |
| ------- | ----- | ------------ | ------ | --------- |
{table_body}

## 关于

每天 09:00 自动抓取 **GitHub Trending**，按语言分类，链接 + 🌟 总星数 + 中文解读，推送至仓库。

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
