# mdimg 🖼️→📁

Localize remote images in Markdown files: download every `http(s)` image to a local
folder and rewrite the links to relative paths. Never lose images to a dead image host again.

把 Markdown 里的网络图片下载到本地并改写为相对路径，图床跑路也不怕。**只用 Python 标准库，零依赖。**

## Install

```bash
pip install -r requirements.txt
```

```bash
pip install .
# or just run the single file:
python mdimg.py README.md
```

Requires Python 3.8+, no third-party packages.

## Usage

```bash
# one file (images -> ./assets/ next to the md file)
mdimg README.md

# a directory, recursive
mdimg docs/ -r

# custom output dir
mdimg README.md -o static/img

# preview only: list what would be downloaded / rewritten
mdimg README.md --dry-run
```

Both syntaxes are handled:

```markdown
![alt](https://example.com/pic.png)
<img src="https://example.com/pic.png" width="300">
```

Images inside fenced code blocks are ignored. Files are named by the SHA1 of the
URL, so the same image referenced many times is downloaded only once. Failed
downloads keep the original link and print a warning instead of aborting.

## Example

```bash
$ mdimg post.md
- post.md: 发现 3 张网络图片
  ok https://picsum.photos/seed/a/600/400 -> assets/9f2c1a4b7d3e8f01.jpg
  ok https://picsum.photos/seed/b/600/400 -> assets/41bd92c7f0a55e3d.jpg
  ! 下载失败 https://example.com/404.png: HTTP Error 404: Not Found
  已改写 post.md
共本地化 2 张图片
```

## License

MIT
