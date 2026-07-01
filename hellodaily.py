#!/usr/bin/env python3
"""HelloDaily — 每日开源精选"""

import urllib.request
import json as json_mod
import os
import re
import glob
import sys
from datetime import date
from urllib.parse import unquote

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))


def fetch_by_volume(volume):
    """从 521xueweihan/HelloGitHub repo 抓取某期 markdown"""
    url = f"https://raw.githubusercontent.com/521xueweihan/HelloGitHub/master/content/HelloGitHub{volume}.md"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "HelloDaily/1.0"})
        text = urllib.request.urlopen(req, timeout=15).read().decode("utf-8")
    except Exception as e:
        print(f"  ⚠️ 第 {volume} 期获取失败: {e}")
        return []

    repos = []
    current_lang = "其他"

    for line in text.split("\n"):
        # 语言分类标题
        m = re.match(r'^###\s+(.+?)(?:\s+项目)?$', line.strip())
        if m:
            current_lang = m.group(1).strip()
            continue

        # 项目条目: 1、[name](link)：description
        m = re.match(r'^\d+、\[(.+?)\]\((.+?)\)[：:]\s*(.*)', line.strip())
        if m:
            name = m.group(1).strip()
            link = m.group(2).strip()
            desc = m.group(3).strip()

            # 提取真实 GitHub 链接
            if 'target=' in link:
                link = unquote(link.split('target=')[1].split('&')[0])

            # 去掉 "来自 @xxx" 后缀
            desc = re.sub(r'\s*来自\s*\[@[^\]]+\]\([^)]+\)\s*', '', desc).strip()
            desc = re.sub(r'\s*来自\s*@\S+\s*', '', desc).strip()

            # 提取 repo full_name
            full_name = ""
            gh_m = re.search(r'github\.com/([^/]+/[^/?#]+)', link)
            if gh_m:
                full_name = gh_m.group(1).rstrip('/')

            repos.append({
                "name": full_name or name,
                "desc": desc,
                "lang": current_lang,
                "stars": "",
                "stars_today": "",
            })

    return repos


def fetch_stars(repos):
    """从 GitHub API 批量获取 star 数"""
    import time
    token = os.environ.get("GITHUB_TOKEN", "")
    headers = {
        "User-Agent": "HelloDaily/1.0",
        "Accept": "application/vnd.github.v3+json",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    total = sum(1 for r in repos if not r["stars"] and r["name"])
    if not total:
        return repos

    count = 0
    for i, r in enumerate(repos):
        if r["stars"] or not r["name"]:
            continue
        try:
            # 加间隔避免限速
            time.sleep(0.2)
            url = f"https://api.github.com/repos/{r['name']}"
            req = urllib.request.Request(url, headers=headers)
            resp = urllib.request.urlopen(req, timeout=5)
            data = json_mod.loads(resp.read().decode("utf-8"))
            if "stargazers_count" in data and data["stargazers_count"] is not None:
                r["stars"] = f"{data['stargazers_count']:,}"
                count += 1
            elif "message" in data and "rate limit" in data["message"].lower():
                print(f"  ⚠️ API 限速，剩余 {total - i} 个跳过")
                break
        except Exception as e:
            if i < 3:
                print(f"  ⚠️ {r['name']}: {e}")
            pass
    if count:
        print(f"⭐ 获取到 {count}/{total} 个项目的 star 数")
    return repos


def fetch_trending():
    """从 GitHub Trending 补充热门项目"""
    url = "https://github.com/trending"
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (compatible; HelloDaily/1.0)",
        "Accept": "text/html",
    })
    try:
        html = urllib.request.urlopen(req, timeout=15).read().decode("utf-8")
    except:
        return []

    repos = []
    articles = re.split(r'<article', html)[1:]

    for art in articles:
        # Repo name
        name_match = re.search(r'h2[^>]*>.*?<a[^>]*href="/([^\"]+)"', art, re.DOTALL)
        if not name_match:
            continue
        full_name = name_match.group(1).strip()

        # Description
        desc_match = re.search(r'<p[^>]*class="[^"]*col-9[^"]*color-fg-muted[^"]*"[^>]*>(.*?)</p>', art, re.DOTALL)
        desc = ""
        if desc_match:
            desc = re.sub(r'<[^>]+>', '', desc_match.group(1)).strip()
            desc = desc.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&#39;", "'").replace("&quot;", '"')

        # Language
        lang_match = re.search(r'<span[^>]*itemprop="programmingLanguage"[^>]*>(.*?)</span>', art, re.DOTALL)
        lang = lang_match.group(1).strip() if lang_match else "其他"

        # Stars
        stars = ""
        for pattern in [
            r'<a[^>]*href="/' + re.escape(full_name) + r'/stargazers"[^>]*>.*?<strong>(.*?)</strong>',
            r'aria-label="[^"]*(\d[\d,]*)\s*star',
        ]:
            s_match = re.search(pattern, art, re.DOTALL)
            if s_match:
                s = s_match.group(1).strip().replace(",", "")
                if s.isdigit():
                    stars = f"{int(s):,}"
                    break

        repos.append({
            "name": full_name,
            "desc": desc,
            "lang": lang,
            "stars": stars,
            "stars_today": "",
        })

    return repos


def translate_descriptions(repos):
    """翻译英文简介为中文（免费版，不需要 API key）"""
    # 只翻译还没中文的
    to_translate = [(i, r) for i, r in enumerate(repos) if r["desc"] and not any('\u4e00' <= c <= '\u9fff' for c in r["desc"])]
    if not to_translate:
        return repos

    # 尝试用 LLM API 翻译（如果有 key）
    api_key = os.environ.get("OPENAI_API_KEY", "") or os.environ.get("OPENROUTER_API_KEY", "")
    if api_key:
        base_url = os.environ.get("OPENAI_BASE_URL", "https://api.siliconflow.cn/v1")
        model = os.environ.get("TRANSLATE_MODEL", "deepseek-ai/DeepSeek-V3")
        print(f"  🤖 使用 LLM 翻译 ({model})...")
        return _translate_via_llm(repos, to_translate, api_key, base_url, model)

    # 没有 API key → 用免费 Google Translate
    print("  🌐 使用免费 Google Translate 翻译...")
    return _translate_via_google(repos, to_translate)


def _translate_via_llm(repos, to_translate, api_key, base_url, model):
    """用 LLM API 批量翻译"""
    import json as json_mod
    batch_size = 10
    for batch_start in range(0, len(to_translate), batch_size):
        batch = to_translate[batch_start:batch_start + batch_size]
        lines = [f"{j+1}. {r['desc']}" for j, (_, r) in enumerate(batch)]
        prompt = "将以下英文项目简介翻译成简洁的中文（20-40字），直接给出译文，不要编号和项目名：\n\n" + "\n".join(lines)

        data = json_mod.dumps({
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
            "max_tokens": 1024,
        }).encode("utf-8")

        req = urllib.request.Request(
            f"{base_url}/chat/completions",
            data=data,
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
        )
        try:
            resp = urllib.request.urlopen(req, timeout=30).read().decode("utf-8")
            result = json_mod.loads(resp)
            text = result["choices"][0]["message"]["content"]
            for j, line in enumerate(text.strip().split("\n")):
                line = line.strip()
                if not line:
                    continue
                line = re.sub(r'^\d+[.、\s]*', '', line)
                if j < len(batch) and line:
                    idx = batch[j][0]
                    repos[idx]["desc"] = line[:200]
        except Exception as e:
            print(f"  ⚠️ LLM 翻译失败: {e}")
            break
    return repos


def _translate_via_google(repos, to_translate):
    """用免费 Google Translate 逐条翻译（不需要 API key）"""
    import urllib.parse
    for idx, r in to_translate:
        desc = r["desc"].strip()
        if not desc:
            continue
        try:
            # 用 Google Translate 免费接口
            url = "https://translate.googleapis.com/translate_a/single"
            params = {
                "client": "gtx",
                "sl": "en",
                "tl": "zh-CN",
                "dt": "t",
                "q": desc[:800],  # 截断超长文本
            }
            full_url = f"{url}?{urllib.parse.urlencode(params)}"
            req = urllib.request.Request(full_url, headers={"User-Agent": "Mozilla/5.0"})
            resp = urllib.request.urlopen(req, timeout=10).read().decode("utf-8")
            # 解析返回的 JSON 数组
            translated = json_mod.loads(resp)[0][0][0]
            repos[idx]["desc"] = translated[:200]
        except Exception as e:
            print(f"  ⚠️ Google 翻译失败: {desc[:30]}... → {e}")
            # 保留原文
    return repos


def lang_emoji(lang):
    name = lang.replace(" 项目", "").replace("项目", "")
    emoji_map = {
        "Python": "🐍", "JavaScript": "🟨", "TypeScript": "🔷", "Java": "☕",
        "Go": "🔵", "Rust": "🦀", "C++": "⚡", "C": "💠", "Ruby": "💎",
        "Swift": "🍎", "Kotlin": "🟣", "PHP": "🐘", "Shell": "🐚",
        "HTML": "🌐", "CSS": "🎨", "Vue": "💚", "React": "⚛️",
        "人工智能": "🤖", "Skills": "🛠", "其他": "📦", "其它": "📦",
        "C#": "🎯",
    }
    return emoji_map.get(name, "📦")


def get_used_volumes(content_dir):
    """从已有 content 文件推断已用过的 HelloGitHub 期数"""
    used = set()
    for f in glob.glob(os.path.join(OUTPUT_DIR, "gen_issue*.py")):
        with open(f, "r", errors="ignore") as fh:
            text = fh.read()
            for m in re.finditer(r'volume/(\d+)', text):
                used.add(int(m.group(1)))
    for f in glob.glob(os.path.join(content_dir, "HelloDaily-*.md")):
        with open(f, "r", errors="ignore") as fh:
            text = fh.read()
            # 新格式: 隐藏注释
            for m in re.finditer(r'<!--\s*source_volume:\s*(\d+)', text):
                used.add(int(m.group(1)))
            # 旧格式兼容: "来自第 123 期"
            for m in re.finditer(r'来自.*?第\s*(\d{3,})\s*期', text):
                used.add(int(m.group(1)))
    return used


def generate_markdown(repos, volume):
    today_dt = date.today()
    today = today_dt.isoformat()
    content_dir = os.path.join(OUTPUT_DIR, "content")

    # 计算期号
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
    md += f"> 本期内容精选自第 {issue_num} 期\n"
    md += f"<!-- source_volume: {volume} -->\n\n"
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
    md += '    👉 每天 09:00 自动更新 · 开源精选 👈<br>\n'
    md += '</p>\n'
    return md, issue_num, today


if __name__ == "__main__":
    content_dir = os.path.join(OUTPUT_DIR, "content")
    os.makedirs(content_dir, exist_ok=True)

    # 1. 从 HelloGitHub repo 抓一期
    used = get_used_volumes(content_dir)
    print(f"📚 已用期数: {sorted(used) or '无'}")

    volume = 123  # 从最新一期开始
    while volume in used:
        volume -= 1
    if volume < 1:
        volume = 123
        while volume in used:
            volume -= 1

    print(f"📖 正在获取第 {volume} 期...")
    repos = fetch_by_volume(volume)
    if not repos:
        print(f"⚠️ 第 {volume} 期获取失败")
        sys.exit(1)
    print(f"✅ 从 HelloGitHub 获取到 {len(repos)} 个项目")

    # 2. 从 GitHub Trending 补充
    print("📈 正在获取 GitHub Trending...")
    trending = fetch_trending()
    print(f"✅ 获取到 {len(trending)} 个 Trending 项目")

    # 翻译 Trending 项目的英文简介
    if trending:
        print("🌏 正在翻译 Trending 简介...")
        trending = translate_descriptions(trending)
        print("✅ 翻译完成")

    # 合并：去掉重复的（Trending 里已经在 HelloGitHub 有的跳过）
    existing_names = {r["name"] for r in repos if r["name"]}
    new_count = 0
    for r in trending:
        if r["name"] and r["name"] not in existing_names:
            repos.append(r)
            existing_names.add(r["name"])
            new_count += 1
    print(f"✅ Trending 补充了 {new_count} 个新项目")

    # 3. 获取 star 数
    print("⭐ 正在查询项目 star 数...")
    repos = fetch_stars(repos)

    # 生成
    md, issue_num, today = generate_markdown(repos, volume)
    issue_str = f"第 {issue_num:03d} 期"

    filename = f"HelloDaily-{today}.md"
    filepath = os.path.join(content_dir, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(md)
    print(f"✅ 已保存: {filepath}")

    # 更新 README（不提 HelloGitHub）
    readme_path = os.path.join(OUTPUT_DIR, "README.md")
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
  🌟 每天 09:00 自动推送精选项目<br>
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

每天 09:00 自动抓取 **GitHub Trending + 热门项目**，按语言分类，链接 + 🌟 总星数 + 中文解读，推送至仓库。

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
    print(f"\n📦 来源: 精选第 {volume} 期 + GitHub Trending (+{new_count})")
