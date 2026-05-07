#!/usr/bin/env python3
"""
GitHub AI Agent Trending Top 50 数据抓取脚本
数据来源: GitHub Search API + Trending Page
"""

import json
import os
import re
import time
import hashlib
from datetime import datetime, timedelta
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from urllib.parse import urlencode, quote
import ssl

# ========== 配置 ==========
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
OUTPUT_FILE = os.path.join(DATA_DIR, "today.json")

# 搜索关键词 - 覆盖 AI Agent 生态
SEARCH_QUERIES = [
    "topic:ai-agent",
    "topic:agent",
    "topic:llm",
    "topic:mcp",
    "topic:claude",
    "topic:multi-agent",
    "topic:langchain",
    "topic:autogpt",
    "claude code skills",
    "skill claude-code extension",
    "superpowers claude code skill",
    "ai agent framework",
    "multi agent system",
    "agentic ai",
    "model context protocol",
]

# 每页数量
PER_PAGE = 30

# 目标仓库数
TARGET_COUNT = 50


def make_request(url, headers=None):
    """发送 HTTP 请求，带重试"""
    ctx = ssl.create_default_context()
    if headers is None:
        headers = {
            "User-Agent": "AgentDailyRadar/1.0",
            "Accept": "application/vnd.github.v3+json",
        }
    for attempt in range(3):
        try:
            req = Request(url, headers=headers)
            with urlopen(req, timeout=30, context=ctx) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (URLError, HTTPError) as e:
            if attempt == 2:
                print(f"  ⚠️ 请求失败: {e}")
                return None
            time.sleep(2)
    return None


def build_search_url(query, page=1):
    """构建 GitHub Search API URL"""
    params = {
        "q": query,
        "sort": "stars",
        "order": "desc",
        "per_page": PER_PAGE,
        "page": page,
    }
    return f"https://api.github.com/search/repositories?{urlencode(params)}"


def parse_trending_page():
    """
    解析 GitHub Trending 页面获取每日趋势
    返回: list of {name, author, url, description, stars_today, language}
    """
    repos = []
    try:
        ctx = ssl.create_default_context()
        req = Request("https://github.com/trending?since=daily", headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml"
        })
        with urlopen(req, timeout=30, context=ctx) as resp:
            html = resp.read().decode("utf-8")

        # 用正则提取仓库信息
        # 匹配 <h2 class="h3 lh-condensed"> 区块
        article_pattern = re.compile(
            r'<article[^>]*>(.*?)</article>', re.DOTALL
        )
        h2_pattern = re.compile(
            r'<h2[^>]*>.*?<a[^>]*href="/([^/]+)/([^"]+)"[^>]*>.*?</a>.*?</h2>', re.DOTALL
        )
        desc_pattern = re.compile(
            r'<p class="col-9 color-fg-muted[^"]*"[^>]*>(.*?)</p>', re.DOTALL
        )
        lang_pattern = re.compile(
            r'<span itemprop="programmingLanguage"[^>]*>(.*?)</span>', re.DOTALL
        )
        stars_pattern = re.compile(
            r'<span[^>]*>\s*([\d,]+)\s*stars today\s*</span>', re.DOTALL | re.IGNORECASE
        )

        articles = article_pattern.findall(html)
        for article in articles:
            h2_match = h2_pattern.search(article)
            if not h2_match:
                continue
            author, name = h2_match.group(1), h2_match.group(2)
            author = author.strip().lstrip('/')
            name = name.strip()

            desc_match = desc_pattern.search(article)
            description = desc_match.group(1).strip() if desc_match else ""
            description = re.sub(r'<[^>]+>', '', description)

            lang_match = lang_pattern.search(article)
            language = lang_match.group(1).strip() if lang_match else ""

            stars_match = stars_pattern.search(article)
            stars_today = stars_match.group(1).replace(",", "") if stars_match else "0"

            repos.append({
                "name": name,
                "full_name": f"{author}/{name}",
                "author": author,
                "url": f"https://github.com/{author}/{name}",
                "description": description,
                "language": language,
                "stars_today": int(stars_today),
            })
    except Exception as e:
        print(f"  ⚠️ Trending 页面解析失败: {e}")

    return repos


def search_agent_repos():
    """通过 Search API 搜索 AI Agent 相关仓库"""
    all_repos = {}
    seen = set()

    for query in SEARCH_QUERIES:
        print(f"  🔍 搜索: {query}")
        for page in [1, 2]:
            url = build_search_url(query, page)
            data = make_request(url)
            if not data or "items" not in data:
                continue

            for item in data["items"]:
                full_name = item["full_name"]
                if full_name in seen:
                    continue
                seen.add(full_name)

                # 计算得分：星数 + forks 权重
                score = item["stargazers_count"] + item["forks_count"] * 0.5

                all_repos[full_name] = {
                    "name": item["name"],
                    "full_name": full_name,
                    "author": item["owner"]["login"],
                    "url": item["html_url"],
                    "description": (item.get("description") or "").strip(),
                    "language": item.get("language") or "",
                    "stars": item["stargazers_count"],
                    "forks": item["forks_count"],
                    "stars_today": 0,
                    "score": score,
                    "topics": item.get("topics", []),
                    "created_at": item["created_at"],
                    "updated_at": item["updated_at"],
                    "pushed_at": item["pushed_at"],
                    "open_issues": item["open_issues_count"],
                    "license": item.get("license", {}).get("spdx_id", "") if item.get("license") else "",
                }
            time.sleep(0.5)  # 避免触发频率限制

    return list(all_repos.values())


def merge_with_trending(search_repos, trending_repos):
    """合并 Search API 和 Trending 数据"""
    trending_map = {r["full_name"]: r for r in trending_repos}

    for repo in search_repos:
        if repo["full_name"] in trending_map:
            repo["stars_today"] = trending_map[repo["full_name"]]["stars_today"]
            repo["is_trending"] = True
        else:
            repo["is_trending"] = False

    # 添加仅在 Trending 中出现但未在搜索中找到的仓库
    search_names = {r["full_name"] for r in search_repos}
    for full_name, tr in trending_map.items():
        if full_name not in search_names:
            search_repos.append({
                "name": tr["name"],
                "full_name": full_name,
                "author": tr["author"],
                "url": tr["url"],
                "description": tr["description"],
                "language": tr["language"],
                "stars": 0,
                "forks": 0,
                "stars_today": tr["stars_today"],
                "score": tr["stars_today"] * 10,
                "topics": [],
                "created_at": "",
                "updated_at": "",
                "pushed_at": "",
                "open_issues": 0,
                "license": "",
                "is_trending": True,
            })

    return search_repos


def is_agent_related(repo):
    """判断仓库是否真正与 AI Agent 相关"""
    agent_keywords = [
        "agent", "ai", "llm", "gpt", "claude", "chatgpt", "langchain",
        "autogpt", "mcp", "model context protocol", "rag", "prompt",
        "copilot", "assistant", "chatbot", "multi-agent", "swarm",
        "tool ", "tool-call", "function-call", "orchestrat",
        "autonomous", "agentic", "reasoning", "planning",
        "memory", "embedding", "vector", "semantic",
        "openai", "anthropic", "deepseek", "transformer",
        "workflow", "chain", "pipeline", "automation",
        "conversation", "dialogue", "nlp", "natural language",
        "skill", "superpowers",
    ]

    text = (
        f"{repo.get('description', '')} "
        f"{' '.join(repo.get('topics', []))} "
        f"{repo.get('name', '')} "
        f"{repo.get('full_name', '')}"
    ).lower()

    score = sum(1 for kw in agent_keywords if kw in text)
    return score >= 2


def generate_summary(repo):
    """基于仓库信息生成中文摘要"""
    desc = repo.get("description", "")
    topics = repo.get("topics", [])
    language = repo.get("language", "")
    name = repo.get("name", "")
    stars = repo.get("stars", 0)

    if not desc:
        desc = ""

    # 根据 topics 识别类别
    category = "AI Agent 工具"
    topic_lower = " ".join(topics).lower() + " " + desc.lower()

    if any(kw in topic_lower for kw in ["multi-agent", "swarm", "multi agent"]):
        category = "多智能体系统"
    elif any(kw in topic_lower for kw in ["mcp", "model context protocol"]):
        category = "MCP 协议/工具集成"
    elif any(kw in topic_lower for kw in ["skill", "superpowers", "claude-code-template", "claude code skill"]):
        category = "Claude Code Skills"
    elif any(kw in topic_lower for kw in ["memory", "remember", "persist"]):
        category = "AI 记忆/持久化"
    elif any(kw in topic_lower for kw in ["workflow", "pipeline", "orchestrat"]):
        category = "AI 工作流编排"
    elif any(kw in topic_lower for kw in ["code", "cli", "terminal", "copilot", "programming"]):
        category = "AI 编程助手"
    elif any(kw in topic_lower for kw in ["rag", "retrieval", "search"]):
        category = "RAG/检索增强"
    elif any(kw in topic_lower for kw in ["chatbot", "conversation", "assistant"]):
        category = "AI 对话/助手"
    elif any(kw in topic_lower for kw in ["framework", "langchain", "sdk"]):
        category = "Agent 开发框架"
    elif any(kw in topic_lower for kw in ["tool", "function-call", "plugin"]):
        category = "Agent 工具调用"
    elif any(kw in topic_lower for kw in ["autonomous", "autogpt", "self"]):
        category = "自主 Agent"
    elif any(kw in topic_lower for kw in ["reasoning", "planning", "think"]):
        category = "推理/规划引擎"
    elif any(kw in topic_lower for kw in ["embedding", "vector", "database"]):
        category = "向量数据库/嵌入"
    elif any(kw in topic_lower for kw in ["evaluation", "benchmark", "testing"]):
        category = "Agent 评测/测试"
    elif any(kw in topic_lower for kw in ["ui", "frontend", "web", "browser"]):
        category = "Agent 浏览器/UI自动化"
    elif any(kw in topic_lower for kw in ["monitor", "observ", "track"]):
        category = "Agent 监控/可观测"

    # 构建描述
    name_part = name.replace("-", " ").replace("_", " ").title()

    star_desc = "超高热度" if stars > 50000 else ("热门" if stars > 10000 else "新兴" if stars > 1000 else "新锐")

    if language:
        tech_info = f"基于{language}开发"
    else:
        tech_info = ""

    if len(desc) > 150:
        short_desc = desc[:147] + "..."
    elif desc:
        short_desc = desc
    else:
        short_desc = "暂无描述"

    summary = f"【{category}】{star_desc}{tech_info}项目。{short_desc}"

    if len(summary) > 200:
        summary = summary[:197] + "..."

    return summary


def main():
    print("=" * 60)
    print("🤖 GitHub AI Agent 趋势雷达 - 数据抓取")
    print(f"   时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # Step 1: Search API
    print("\n📡 Step 1: 搜索 AI Agent 仓库...")
    search_repos = search_agent_repos()
    print(f"   ✅ 从 Search API 获取 {len(search_repos)} 个仓库")

    # Step 2: Trending Page
    print("\n📈 Step 2: 解析 Trending 页面...")
    trending_repos = parse_trending_page()
    print(f"   ✅ 从 Trending 页面获取 {len(trending_repos)} 个仓库")

    # Step 3: Merge
    print("\n🔄 Step 3: 合并数据...")
    all_repos = merge_with_trending(search_repos, trending_repos)

    # Step 4: Filter agent-related
    print("\n🎯 Step 4: 筛选 Agent 相关仓库...")
    agent_repos = [r for r in all_repos if is_agent_related(r)]
    print(f"   ✅ 筛选出 {len(agent_repos)} 个 Agent 相关仓库")

    # Step 5: Sort and rank
    print("\n📊 Step 5: 综合排序...")
    # 排序：trending 优先 > stars 数量 > forks
    for r in agent_repos:
        r["rank_score"] = (
            r.get("stars_today", 0) * 100
            + r.get("stars", 0) * 1
            + r.get("forks", 0) * 0.5
        )

    agent_repos.sort(key=lambda r: r["rank_score"], reverse=True)
    top50 = agent_repos[:TARGET_COUNT]

    # Step 6: Generate summaries
    print("\n✍️ Step 6: 生成中文摘要...")
    for i, repo in enumerate(top50):
        repo["rank"] = i + 1
        repo["summary"] = generate_summary(repo)
        if i < 5:
            print(f"   #{i+1} {repo['full_name']}: {repo['summary'][:60]}...")

    # Step 7: Build output (slim down fields for smaller file)
    today_str = datetime.now().strftime("%Y-%m-%d")
    slim_repos = []
    for r in top50:
        slim_repos.append({
            "name": r.get("name", ""),
            "full_name": r.get("full_name", ""),
            "url": r.get("url", ""),
            "html_url": r.get("url", ""),
            "description": r.get("description", ""),
            "language": r.get("language", ""),
            "stargazers_count": r.get("stars", 0),
            "forks_count": r.get("forks", 0),
            "open_issues_count": r.get("open_issues", 0),
            "topics": r.get("topics", []),
            "pushed_at": r.get("pushed_at", ""),
            "created_at": r.get("created_at", ""),
            "updated_at": r.get("updated_at", ""),
            "license": {"spdx_id": r.get("license", "")} if r.get("license") else None,
            "stars_today": r.get("stars_today", 0),
            "owner": {"login": r.get("author", "")},
        })

    output = {
        "meta": {
            "generated_at": datetime.now().isoformat(),
            "date": today_str,
            "total_found": len(agent_repos),
            "top_count": len(slim_repos),
            "version": "1.1",
        },
        "repositories": slim_repos,
    }

    # Step 8: Save
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    # Save history
    history_dir = os.path.join(DATA_DIR, "history")
    os.makedirs(history_dir, exist_ok=True)
    history_file = os.path.join(history_dir, f"{today_str}.json")
    with open(history_file, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n{'=' * 60}")
    print(f"🎉 完成! 数据已保存至: {OUTPUT_FILE}")
    print(f"   历史存档: {history_file}")
    print(f"   Top 3:")
    for i, r in enumerate(top50[:3]):
        print(f"     #{i+1} ⭐{r['stars']:,} {r['full_name']} - {r['description'][:50]}")
    print(f"{'=' * 60}")

    return output


if __name__ == "__main__":
    main()
