"""Minimal conversion pipeline: find post HTML, parse, convert to Markdown, write Hugo bundles."""

import shutil
import time
from enum import Enum
from pathlib import Path
from urllib.parse import urlparse

import yaml
from bs4 import BeautifulSoup
from markdownify import markdownify as md
from slugify import slugify


class OutputFormat(str, Enum):
    """Supported output formats for converted Markdown files."""

    hugo = "hugo"
    obsidian = "obsidian"

try:
    import httpx
except ImportError:
    httpx = None  # type: ignore[assignment]

# Request like a browser so Medium's CDN serves images
IMAGE_REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; rv:109.0) Gecko/20100101 Firefox/119.0",
    "Accept": "image/avif,image/webp,image/png,image/svg+xml,image/*,*/*;q=0.8",
}


# Non-post directories in Medium export (utility pages)
NON_POST_DIRS = {"blocks", "bookmarks", "claps", "highlights", "interests"}


def find_post_html_files(root: Path) -> list[Path]:
    """Return HTML files that are likely Medium posts.

    Prefer files under root/posts/ if that directory exists (standard export layout).
    Otherwise exclude known non-post directories and return the rest.
    """
    posts_dir = root / "posts"
    if posts_dir.is_dir():
        return sorted(posts_dir.rglob("*.html"))
    # No posts/ folder: exclude known utility dirs
    all_html = sorted(p for p in root.rglob("*.html") if p.is_file())
    return [
        p
        for p in all_html
        if not any(part in p.parts for part in NON_POST_DIRS)
        and p.name != "README.html"
    ]


def _extract_canonical(soup: BeautifulSoup) -> str | None:
    link = soup.find("link", rel="canonical", href=True)
    return link["href"].strip() if link else None


def _extract_title(soup: BeautifulSoup) -> str:
    h1 = soup.find("h1")
    if h1:
        return h1.get_text(strip=True)
    title_el = soup.find("title")
    if title_el:
        return title_el.get_text(strip=True)
    return "Untitled"


def _extract_article_html(soup: BeautifulSoup) -> str:
    """Extract main article content as HTML string."""
    article = soup.find("article")
    if article:
        return str(article)
    # Fallback: first main or content-heavy section
    main = soup.find("main")
    if main:
        return str(main)
    # Last resort: body
    body = soup.find("body")
    return str(body) if body else ""


def get_title_canonical(html_path: Path) -> tuple[str, str | None]:
    """Light parse to get title and canonical URL only (for slug + bundle dir)."""
    raw = html_path.read_text(encoding="utf-8", errors="replace")
    soup = BeautifulSoup(raw, "lxml")
    return _extract_title(soup), _extract_canonical(soup)


# Extension from URL path or Content-Type
_CT_EXT = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
    "image/svg+xml": ".svg",
}


def _extension_for_url(url: str, content_type: str | None = None) -> str:
    if content_type and content_type.split(";")[0].strip().lower() in _CT_EXT:
        return _CT_EXT[content_type.split(";")[0].strip().lower()]
    path = urlparse(url).path
    if path and "." in path:
        ext = path.rsplit(".", 1)[-1].lower()
        if ext in ("png", "jpg", "jpeg", "gif", "webp", "svg"):
            return f".{ext}"
    return ".png"


def _localize_images(
    article_soup: BeautifulSoup,
    html_path: Path,
    tmp_dir: Path,
    images_dir: Path,
    src_prefix: str,
) -> int:
    """In-place: resolve each img src to a local file or download, copy into images_dir, set src to src_prefix<name>. Returns count of images localized."""
    imgs = article_soup.find_all("img", src=True)
    if not imgs:
        return 0
    images_dir.mkdir(parents=True, exist_ok=True)
    localized = 0
    for i, img in enumerate(imgs, 1):
        src = img["src"].strip()
        if not src:
            continue
        # Relative or file path: resolve against the HTML file's directory
        if not src.startswith(("http://", "https://")):
            resolved = (html_path.parent / src).resolve()
            try:
                resolved.relative_to(tmp_dir)
            except ValueError:
                continue  # outside export, skip
            if not resolved.is_file():
                continue
            ext = resolved.suffix.lower() or ".png"
            dest_name = f"{i}{ext}"
            dest = images_dir / dest_name
            shutil.copy2(resolved, dest)
            img["src"] = f"{src_prefix}{dest_name}"
            localized += 1
            continue
        # Remote URL: download (with User-Agent and retry so CDNs don't block)
        if not httpx:
            continue
        last_error: Exception | None = None
        for attempt in range(2):
            try:
                r = httpx.get(
                    src,
                    follow_redirects=True,
                    timeout=45,
                    headers=IMAGE_REQUEST_HEADERS,
                )
                r.raise_for_status()
                if len(r.content) == 0:
                    raise ValueError("empty response")
                ct = r.headers.get("content-type", "")
                ext = _extension_for_url(src, ct)
                dest_name = f"{i}{ext}"
                dest = images_dir / dest_name
                dest.write_bytes(r.content)
                img["src"] = f"{src_prefix}{dest_name}"
                localized += 1
                last_error = None
                break
            except Exception as e:
                last_error = e
                if attempt < 1:
                    time.sleep(0.5 + attempt)
        if last_error is not None:
            # Leave src unchanged so the MD still has the URL; user can fix manually
            pass
    return localized


def convert_html_file(
    html_path: Path,
    tmp_dir: Path,
    bundle_dir: Path,
    *,
    images_dir: Path | None = None,
    src_prefix: str = "images/",
) -> tuple[str, str | None, str, int]:
    """Parse one post HTML file, localize images, return (title, canonical_url, markdown_body, num_images_localized).

    Images are saved into *images_dir* (defaults to bundle_dir/images) and referenced with *src_prefix* in the Markdown.
    """
    raw = html_path.read_text(encoding="utf-8", errors="replace")
    soup = BeautifulSoup(raw, "lxml")
    title = _extract_title(soup)
    canonical = _extract_canonical(soup)
    article_html = _extract_article_html(soup)
    if not article_html:
        body_md = ""
        localized = 0
    else:
        resolved_images_dir = images_dir if images_dir is not None else bundle_dir / "images"
        article_soup = BeautifulSoup(article_html, "lxml")
        localized = _localize_images(article_soup, html_path, tmp_dir, resolved_images_dir, src_prefix)
        body_md = md(
            str(article_soup),
            heading_style="ATX",
            strip=["script", "style"],
            escape_asterisks=False,
            escape_underscores=False,
        )
    return title, canonical, (body_md or "").strip(), localized


def slug_from_post(title: str, canonical: str | None) -> str:
    """Generate a Hugo-friendly slug."""
    if canonical and "/" in canonical:
        # e.g. https://medium.com/@user/some-post-slug-123
        part = canonical.rstrip("/").split("/")[-1]
        if part and part != "medium.com":
            s = slugify(part, max_length=80)
            if s:
                return s
    return slugify(title, max_length=80) or "untitled"


def write_bundle(out_root: Path, slug: str, title: str, canonical: str | None, body_md: str) -> Path:
    """Write one Hugo page bundle: out_root/<slug>/index.md. Returns path to index.md."""
    bundle_dir = out_root / slug
    bundle_dir.mkdir(parents=True, exist_ok=True)
    front: dict = {
        "title": title,
        "draft": True,
        "slug": slug,
    }
    if canonical:
        front["medium"] = {"canonical": canonical}
    index_md = bundle_dir / "index.md"
    with index_md.open("w", encoding="utf-8") as f:
        f.write("---\n")
        f.write(yaml.dump(front, default_flow_style=False, allow_unicode=True, sort_keys=False))
        f.write("---\n\n")
        f.write(body_md)
        if body_md and not body_md.endswith("\n"):
            f.write("\n")
    return index_md


def write_note(out_root: Path, slug: str, title: str, canonical: str | None, body_md: str) -> Path:
    """Write one Obsidian note: out_root/<slug>.md. Returns path to the note.

    Front matter uses Obsidian conventions: ``title`` and ``source`` (canonical URL).
    Images are expected to reside in ``out_root/assets/<slug>/`` and are referenced
    as ``assets/<slug>/<name>`` in the Markdown body.
    """
    front: dict = {"title": title}
    if canonical:
        front["source"] = canonical
    note_path = out_root / f"{slug}.md"
    with note_path.open("w", encoding="utf-8") as f:
        f.write("---\n")
        f.write(yaml.dump(front, default_flow_style=False, allow_unicode=True, sort_keys=False))
        f.write("---\n\n")
        f.write(body_md)
        if body_md and not body_md.endswith("\n"):
            f.write("\n")
    return note_path
