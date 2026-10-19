#!/usr/bin/env python3
"""mdimg - Localize remote images in Markdown files.

Scan Markdown for remote images, download them locally, and rewrite
the links to relative paths. Stdlib only, zero dependencies.
"""
import argparse
import hashlib
import mimetypes
import os
import re
import sys
import urllib.request
import urllib.parse

# ![alt](url) / ![alt](url "title")
MD_IMG_RE = re.compile(r'!\[[^\]]*\]\(\s*(https?://[^)\s]+)(?:\s+"[^"]*")?\s*\)')
# <img ... src="http..." ...>
HTML_IMG_RE = re.compile(
    r'<img\b[^>]*?\bsrc\s*=\s*["\'](https?://[^"\']+)["\']', re.IGNORECASE)
# fenced code blocks (``` ... ```) - skip images inside
FENCE_RE = re.compile(r'^```.*?$.*?^```$', re.MULTILINE | re.DOTALL)

UA = {"User-Agent": "mdimg/1.0 (+https://github.com/muse-ai-assistant/mdimg)"}
TIMEOUT = 30


def strip_fences(text):
    """Remove fenced code blocks so images inside code aren't touched."""
    return FENCE_RE.sub("", text)


def find_images(text):
    """Return list of (url) in order of appearance, deduped."""
    body = strip_fences(text)
    urls = []
    for m in MD_IMG_RE.finditer(body):
        urls.append(m.group(1))
    for m in HTML_IMG_RE.finditer(body):
        urls.append(m.group(1))
    seen, out = set(), []
    for u in urls:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


def ext_for(url, content_type=None):
    """Guess file extension from URL path or Content-Type."""
    path = urllib.parse.urlparse(url).path
    ext = os.path.splitext(path)[1].lower()
    if ext and len(ext) <= 5:
        return ext
    if content_type:
        e = mimetypes.guess_extension(content_type.split(";")[0].strip())
        if e:
            return e
    return ".img"


def download(url, dest_dir):
    """Download url into dest_dir, named by sha1(url). Returns filename or None."""
    os.makedirs(dest_dir, exist_ok=True)
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            data = resp.read()
            ctype = resp.headers.get("Content-Type")
    except Exception as e:
        print(f"  ! 下载失败 {url}: {e}", file=sys.stderr)
        return None
    if not data:
        print(f"  ! 空文件 {url}", file=sys.stderr)
        return None
    name = hashlib.sha1(url.encode()).hexdigest()[:16] + ext_for(url, ctype)
    path = os.path.join(dest_dir, name)
    if not os.path.exists(path):
        with open(path, "wb") as f:
            f.write(data)
    return name


def rewrite(text, mapping):
    """Replace remote urls with local relative paths."""
    def md_sub(m):
        url = m.group(1)
        if url in mapping:
            return m.group(0).replace(url, mapping[url], 1)
        return m.group(0)

    def html_sub(m):
        url = m.group(1)
        if url in mapping:
            return m.group(0).replace(url, mapping[url], 1)
        return m.group(0)

    # don't touch fenced code blocks: split and process non-code parts
    parts = FENCE_RE.split(text)
    fences = FENCE_RE.findall(text)
    out = []
    for i, part in enumerate(parts):
        part = MD_IMG_RE.sub(md_sub, part)
        part = HTML_IMG_RE.sub(html_sub, part)
        out.append(part)
        if i < len(fences):
            out.append(fences[i])
    return "".join(out)


def process_file(md_path, out_dir, dry_run):
    with open(md_path, encoding="utf-8") as f:
        text = f.read()
    urls = find_images(text)
    if not urls:
        print(f"- {md_path}: 无网络图片")
        return 0
    base = os.path.dirname(os.path.abspath(md_path))
    target = out_dir or os.path.join(base, "assets")
    mapping = {}
    print(f"- {md_path}: 发现 {len(urls)} 张网络图片")
    for url in urls:
        if dry_run:
            name = hashlib.sha1(url.encode()).hexdigest()[:16] + ext_for(url)
            rel = os.path.relpath(os.path.join(target, name), base)
            print(f"  [dry] {url} -> {rel}")
            mapping[url] = rel
            continue
        name = download(url, target)
        if name:
            rel = os.path.relpath(os.path.join(target, name), base)
            print(f"  ok {url} -> {rel}")
            mapping[url] = rel
    if not dry_run and mapping:
        new_text = rewrite(text, mapping)
        if new_text != text:
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(new_text)
            print(f"  已改写 {md_path}")
    return len(mapping)


def iter_md(paths, recursive):
    seen = set()
    for p in paths:
        if os.path.isfile(p) and p.endswith(".md"):
            rp = os.path.realpath(p)
            if rp not in seen:
                seen.add(rp)
                yield p
        elif os.path.isdir(p):
            for root, _, files in os.walk(p):
                for fn in sorted(files):
                    if fn.endswith(".md"):
                        fp = os.path.join(root, fn)
                        rp = os.path.realpath(fp)
                        if rp not in seen:
                            seen.add(rp)
                            yield fp
                if not recursive:
                    break
        else:
            print(f"跳过(不存在): {p}", file=sys.stderr)


def main():
    ap = argparse.ArgumentParser(
        prog="mdimg",
        description="下载 Markdown 中的网络图片到本地并改写链接（只用标准库）")
    ap.add_argument("inputs", nargs="+", help="md 文件或目录")
    ap.add_argument("-o", "--out", default=None,
                    help="图片输出目录（默认：md 文件同级的 assets/）")
    ap.add_argument("-r", "--recursive", action="store_true",
                    help="递归子目录")
    ap.add_argument("--dry-run", action="store_true",
                    help="只预览，不下载不改写")
    args = ap.parse_args()
    total = 0
    for md in iter_md(args.inputs, args.recursive):
        total += process_file(md, args.out, args.dry_run)
    print(f"共本地化 {total} 张图片")


if __name__ == "__main__":
    main()
