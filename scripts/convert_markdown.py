"""Helper script to convert Markdown files to interactive, collapsible HTML pages.

Usage:
    uv run --with markdown --with beautifulsoup4 python scripts/convert_markdown.py [input.md] [output.html]

Defaults:
    input.md  : review.md
    output.html: review.html
"""

import sys
from pathlib import Path
import markdown
from bs4 import BeautifulSoup


def convert_md_to_html(md_path: Path, html_path: Path, title: str = "Immich-Go GUI Document"):
    if not md_path.exists():
        print(f"Error: Input file {md_path} does not exist.")
        sys.exit(1)

    md_text = md_path.read_text(encoding="utf-8")

    extensions = [
        "extra",
        "fenced_code",
        "tables",
        "toc",
        "sane_lists",
        "nl2br",
        "codehilite",
    ]

    raw_html = markdown.markdown(md_text, extensions=extensions)
    soup = BeautifulSoup(raw_html, "html.parser")

    doc_root = BeautifulSoup('<div class="document-root"></div>', "html.parser").div
    stack = [(0, doc_root, doc_root)]

    top_elements = [el for el in soup.contents]

    for el in top_elements:
        el_extracted = el.extract() if hasattr(el, "extract") else el

        if isinstance(el_extracted, str) and not el_extracted.strip():
            continue

        if hasattr(el_extracted, "name") and el_extracted.name in ["h1", "h2", "h3", "h4", "h5", "h6"]:
            level = int(el_extracted.name[1])

            while stack and stack[-1][0] >= level:
                stack.pop()

            parent_body = stack[-1][2]

            details = soup.new_tag("details", attrs={
                "open": "",
                "class": f"sec-details level-h{level}"
            })

            summary = soup.new_tag("summary", attrs={
                "class": f"sec-summary level-h{level}"
            })

            summary_inner = soup.new_tag("div", attrs={"class": "summary-content"})

            chevron = soup.new_tag("span", attrs={"class": "chevron"})
            chevron.string = "❯"
            summary_inner.append(chevron)

            badge = soup.new_tag("span", attrs={"class": f"badge badge-h{level}"})
            badge.string = f"H{level}"
            summary_inner.append(badge)

            heading_span = soup.new_tag("span", attrs={"class": "heading-text"})
            if el_extracted.get("id"):
                heading_span["id"] = el_extracted["id"]

            for child in list(el_extracted.contents):
                heading_span.append(child)

            summary_inner.append(heading_span)
            summary.append(summary_inner)
            details.append(summary)

            sec_body = soup.new_tag("div", attrs={"class": f"sec-body level-h{level}"})
            details.append(sec_body)

            parent_body.append(details)
            stack.append((level, details, sec_body))
        else:
            stack[-1][2].append(el_extracted)

    document_content = doc_root.decode_contents()

    full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        :root {{
            --bg-primary: #0f172a;
            --bg-secondary: #1e293b;
            --bg-card: #1e293b;
            --bg-card-hover: #334155;
            --border-color: #334155;
            --text-primary: #f8fafc;
            --text-secondary: #cbd5e1;
            --text-muted: #64748b;
            --accent-color: #38bdf8;
            --accent-hover: #0284c7;
            --accent-bg: rgba(56, 189, 248, 0.12);
            --code-bg: #090d16;
            --code-border: #1e293b;
            --badge-h1-bg: #2563eb;
            --badge-h2-bg: #7c3aed;
            --badge-h3-bg: #db2777;
            --badge-h4-bg: #059669;
            --shadow-color: rgba(0, 0, 0, 0.4);
            --font-main: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            --font-code: "JetBrains Mono", "Fira Code", Consolas, Monaco, monospace;
        }}

        [data-theme="light"] {{
            --bg-primary: #f8fafc;
            --bg-secondary: #ffffff;
            --bg-card: #ffffff;
            --bg-card-hover: #f1f5f9;
            --border-color: #e2e8f0;
            --text-primary: #0f172a;
            --text-secondary: #334155;
            --text-muted: #64748b;
            --accent-color: #0284c7;
            --accent-hover: #0369a1;
            --accent-bg: rgba(2, 132, 199, 0.1);
            --code-bg: #0f172a;
            --code-border: #cbd5e1;
            --badge-h1-bg: #2563eb;
            --badge-h2-bg: #7c3aed;
            --badge-h3-bg: #db2777;
            --badge-h4-bg: #059669;
            --shadow-color: rgba(0, 0, 0, 0.06);
        }}

        * {{ box-sizing: border-box; margin: 0; padding: 0; }}

        body {{
            font-family: var(--font-main);
            background-color: var(--bg-primary);
            color: var(--text-primary);
            line-height: 1.6;
            font-size: 15px;
            display: flex;
            flex-direction: column;
            min-height: 100vh;
        }}

        .top-nav {{
            position: sticky;
            top: 0;
            z-index: 1000;
            background: var(--bg-secondary);
            border-bottom: 1px solid var(--border-color);
            padding: 0.75rem 1.5rem;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 1rem;
            box-shadow: 0 4px 6px -1px var(--shadow-color);
            backdrop-filter: blur(8px);
        }}

        .nav-title {{
            display: flex;
            align-items: center;
            gap: 0.75rem;
            font-weight: 700;
            font-size: 1.15rem;
            color: var(--text-primary);
        }}

        .nav-title svg {{ width: 24px; height: 24px; fill: var(--accent-color); }}
        .nav-controls {{ display: flex; align-items: center; gap: 0.75rem; }}
        .search-box {{ position: relative; }}

        .search-input {{
            background: var(--bg-primary);
            border: 1px solid var(--border-color);
            color: var(--text-primary);
            padding: 0.45rem 0.8rem 0.45rem 2.2rem;
            border-radius: 6px;
            font-size: 0.88rem;
            outline: none;
            width: 240px;
            transition: all 0.2s ease;
        }}

        .search-input:focus {{
            border-color: var(--accent-color);
            width: 300px;
            box-shadow: 0 0 0 3px var(--accent-bg);
        }}

        .search-icon {{
            position: absolute;
            left: 0.7rem;
            top: 50%;
            transform: translateY(-50%);
            width: 15px;
            height: 15px;
            fill: var(--text-muted);
            pointer-events: none;
        }}

        .btn {{
            background: var(--bg-primary);
            border: 1px solid var(--border-color);
            color: var(--text-primary);
            padding: 0.45rem 0.85rem;
            border-radius: 6px;
            font-size: 0.85rem;
            font-weight: 500;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            gap: 0.4rem;
            transition: all 0.15s ease;
        }}

        .btn:hover {{
            background: var(--bg-card-hover);
            border-color: var(--accent-color);
            color: var(--accent-color);
        }}

        .layout-container {{
            display: flex;
            flex: 1;
            max-width: 1600px;
            width: 100%;
            margin: 0 auto;
        }}

        .sidebar {{
            width: 320px;
            position: sticky;
            top: 57px;
            height: calc(100vh - 57px);
            overflow-y: auto;
            border-right: 1px solid var(--border-color);
            padding: 1.25rem 1rem;
            background: var(--bg-secondary);
            flex-shrink: 0;
        }}

        .sidebar h3 {{
            font-size: 0.78rem;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            color: var(--text-muted);
            margin-bottom: 0.75rem;
            padding-left: 0.5rem;
        }}

        .toc-list {{ list-style: none; }}
        .toc-item {{ margin-bottom: 0.2rem; }}

        .toc-link {{
            display: block;
            padding: 0.35rem 0.6rem;
            color: var(--text-secondary);
            text-decoration: none;
            border-radius: 4px;
            font-size: 0.88rem;
            line-height: 1.35;
            transition: all 0.15s ease;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}

        .toc-link:hover {{ background: var(--accent-bg); color: var(--accent-color); }}
        .toc-item.level-2 {{ padding-left: 0.9rem; font-size: 0.84rem; }}
        .toc-item.level-3 {{ padding-left: 1.7rem; font-size: 0.8rem; opacity: 0.9; }}

        .main-content {{ flex: 1; padding: 2rem 3rem; min-width: 0; }}
        .document-root {{ display: flex; flex-direction: column; gap: 1.25rem; }}

        details.sec-details {{
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            overflow: hidden;
            transition: border-color 0.2s ease, box-shadow 0.2s ease;
        }}

        details.sec-details[open] {{ box-shadow: 0 4px 12px var(--shadow-color); }}
        details.level-h1 {{ border-left: 4px solid var(--badge-h1-bg); margin-bottom: 1.25rem; }}
        details.level-h2 {{ border-left: 4px solid var(--badge-h2-bg); margin: 0.85rem 0; background: rgba(255, 255, 255, 0.015); }}
        details.level-h3 {{ border-left: 4px solid var(--badge-h3-bg); margin: 0.6rem 0; background: rgba(255, 255, 255, 0.01); }}
        details.level-h4 {{ border-left: 4px solid var(--badge-h4-bg); margin: 0.4rem 0; }}

        summary.sec-summary {{
            padding: 0.85rem 1.25rem;
            cursor: pointer;
            user-select: none;
            background: var(--bg-card);
            transition: background 0.15s ease;
            list-style: none;
        }}

        summary.sec-summary::-webkit-details-marker {{ display: none; }}
        summary.sec-summary:hover {{ background: var(--bg-card-hover); }}

        .summary-content {{ display: flex; align-items: center; gap: 0.75rem; }}

        .chevron {{
            font-size: 0.8rem;
            color: var(--text-muted);
            transition: transform 0.2s ease;
            display: inline-block;
            width: 14px;
            text-align: center;
            flex-shrink: 0;
        }}

        details[open] > summary .chevron {{ transform: rotate(90deg); color: var(--accent-color); }}

        .badge {{
            font-size: 0.7rem;
            font-weight: 700;
            padding: 0.15rem 0.45rem;
            border-radius: 4px;
            color: #ffffff;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            flex-shrink: 0;
        }}

        .badge-h1 {{ background-color: var(--badge-h1-bg); }}
        .badge-h2 {{ background-color: var(--badge-h2-bg); }}
        .badge-h3 {{ background-color: var(--badge-h3-bg); }}
        .badge-h4 {{ background-color: var(--badge-h4-bg); }}

        .heading-text {{ font-weight: 600; color: var(--text-primary); flex: 1; }}
        .level-h1 .heading-text {{ font-size: 1.2rem; }}
        .level-h2 .heading-text {{ font-size: 1.08rem; }}
        .level-h3 .heading-text {{ font-size: 1.0rem; }}
        .level-h4 .heading-text {{ font-size: 0.95rem; }}

        .sec-body {{
            padding: 1.25rem 1.5rem;
            border-top: 1px solid var(--border-color);
            background: var(--bg-secondary);
            display: flex;
            flex-direction: column;
            gap: 0.85rem;
        }}

        p {{ color: var(--text-primary); margin-bottom: 0.4rem; line-height: 1.7; }}
        ul, ol {{ padding-left: 1.5rem; margin-bottom: 0.75rem; color: var(--text-primary); }}
        li {{ margin-bottom: 0.35rem; }}
        strong {{ color: var(--text-primary); font-weight: 600; }}
        a {{ color: var(--accent-color); text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
        blockquote {{
            border-left: 4px solid var(--accent-color);
            background: var(--accent-bg);
            padding: 0.75rem 1.25rem;
            border-radius: 0 6px 6px 0;
            color: var(--text-secondary);
            margin: 0.75rem 0;
        }}
        hr {{ border: 0; height: 1px; background: var(--border-color); margin: 1.5rem 0; }}

        pre {{
            position: relative;
            background: var(--code-bg);
            border: 1px solid var(--code-border);
            border-radius: 8px;
            padding: 1.1rem;
            overflow-x: auto;
            font-family: var(--font-code);
            font-size: 0.88rem;
            color: #f1f5f9;
            line-height: 1.55;
            margin: 0.75rem 0;
        }}

        code {{
            font-family: var(--font-code);
            font-size: 0.88rem;
            background: rgba(255, 255, 255, 0.08);
            color: var(--accent-color);
            padding: 0.15rem 0.4rem;
            border-radius: 4px;
        }}

        pre code {{ background: transparent; color: inherit; padding: 0; }}

        .copy-code-btn {{
            position: absolute;
            top: 0.6rem;
            right: 0.6rem;
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            color: var(--text-secondary);
            padding: 0.25rem 0.55rem;
            border-radius: 4px;
            font-size: 0.75rem;
            cursor: pointer;
            opacity: 0.7;
            transition: opacity 0.2s ease;
        }}

        pre:hover .copy-code-btn {{ opacity: 1; }}
        .copy-code-btn:hover {{ color: var(--accent-color); border-color: var(--accent-color); }}

        .search-hidden {{ display: none !important; }}

        @media (max-width: 1024px) {{
            .sidebar {{ display: none; }}
            .main-content {{ padding: 1.5rem; }}
        }}
    </style>
</head>
<body data-theme="dark">

    <header class="top-nav">
        <div class="nav-title">
            <svg viewBox="0 0 24 24">
                <path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-5 14H7v-2h7v2zm3-4H7v-2h10v2zm0-4H7V7h10v2z"/>
            </svg>
            <span>{title}</span>
        </div>
        <div class="nav-controls">
            <div class="search-box">
                <svg class="search-icon" viewBox="0 0 24 24">
                    <path d="M15.5 14h-.79l-.28-.27C15.41 12.59 16 11.11 16 9.5 16 5.91 13.09 3 9.5 3S3 5.91 3 9.5 5.91 16 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"/>
                </svg>
                <input type="text" id="searchInput" class="search-input" placeholder="Search..." onkeyup="filterContent()">
            </div>
            <button class="btn" onclick="expandAll()"><span>👇</span> Expand All</button>
            <button class="btn" onclick="collapseAll()"><span>👆</span> Collapse All</button>
            <button class="btn" onclick="toggleTheme()" id="themeBtn"><span>🌙</span> Dark Mode</button>
        </div>
    </header>

    <div class="layout-container">
        <aside class="sidebar">
            <h3>Table of Contents</h3>
            <ul class="toc-list" id="tocList"></ul>
        </aside>

        <main class="main-content">
            {document_content}
        </main>
    </div>

    <script>
        document.addEventListener('DOMContentLoaded', () => {{
            const tocList = document.getElementById('tocList');
            const headings = document.querySelectorAll('.sec-summary');

            headings.forEach((sum, idx) => {{
                const headingText = sum.querySelector('.heading-text');
                const badge = sum.querySelector('.badge');
                if (!headingText || !badge) return;

                const text = headingText.innerText.trim();
                const level = badge.innerText.toLowerCase();
                
                const anchorId = 'sec-heading-' + idx;
                headingText.id = anchorId;

                const li = document.createElement('li');
                li.className = `toc-item level-${{level.replace('h', '')}}`;

                const a = document.createElement('a');
                a.className = 'toc-link';
                a.href = '#' + anchorId;
                a.innerText = text;
                a.onclick = (e) => {{
                    e.preventDefault();
                    let details = sum.closest('details');
                    while (details) {{
                        details.open = true;
                        details = details.parentElement.closest('details');
                    }}
                    headingText.scrollIntoView({{ behavior: 'smooth', block: 'start' }});
                }};

                li.appendChild(a);
                tocList.appendChild(li);
            }});

            document.querySelectorAll('pre').forEach(pre => {{
                const btn = document.createElement('button');
                btn.className = 'copy-code-btn';
                btn.innerText = 'Copy';
                btn.onclick = () => {{
                    const code = pre.querySelector('code');
                    const text = code ? code.innerText : pre.innerText;
                    navigator.clipboard.writeText(text).then(() => {{
                        btn.innerText = 'Copied!';
                        setTimeout(() => btn.innerText = 'Copy', 2000);
                    }});
                }};
                pre.appendChild(btn);
            }});
        }});

        function expandAll() {{ document.querySelectorAll('details').forEach(d => d.open = true); }}
        function collapseAll() {{ document.querySelectorAll('details').forEach(d => d.open = false); }}

        function toggleTheme() {{
            const body = document.body;
            const themeBtn = document.getElementById('themeBtn');
            if (body.getAttribute('data-theme') === 'dark') {{
                body.setAttribute('data-theme', 'light');
                themeBtn.innerHTML = '<span>☀️</span> Light Mode';
            }} else {{
                body.setAttribute('data-theme', 'dark');
                themeBtn.innerHTML = '<span>🌙</span> Dark Mode';
            }}
        }}

        function filterContent() {{
            const query = document.getElementById('searchInput').value.toLowerCase().trim();
            const detailsList = document.querySelectorAll('details');

            if (!query) {{
                detailsList.forEach(d => d.classList.remove('search-hidden'));
                return;
            }}

            detailsList.forEach(d => {{
                const text = d.innerText.toLowerCase();
                if (text.includes(query)) {{
                    d.classList.remove('search-hidden');
                    d.open = true;
                }} else {{
                    d.classList.add('search-hidden');
                }}
            }});
        }}
    </script>
</body>
</html>
"""

    html_path.write_text(full_html, encoding="utf-8")
    print(f"Successfully converted {md_path} -> {html_path}")


if __name__ == "__main__":
    repo_root = Path(__file__).resolve().parent.parent
    in_file = Path(sys.argv[1]) if len(sys.argv) > 1 else repo_root / "review.md"
    out_file = Path(sys.argv[2]) if len(sys.argv) > 2 else repo_root / "review.html"

    doc_title = f"Immich-Go GUI — {in_file.stem.replace('_', ' ').replace('-', ' ').title()}"
    convert_md_to_html(in_file, out_file, title=doc_title)
