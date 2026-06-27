"""Minimal conversion pipeline: find post HTML, parse, convert to Markdown, write Hugo bundles."""

import hashlib
import re
import time
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse

import yaml
from bs4 import BeautifulSoup
from dateutil import parser as dateparser
from markdownify import markdownify as md
from slugify import slugify

# Image-handling hooks that differ per output target.
ImageNamer = Callable[[int, str, bytes], str]  # (index, ext, content) -> filename
ImageSrcer = Callable[[str], str]  # (filename) -> value written into <img src>

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
    if link:
        return link["href"].strip()
    # Medium's export has no <link rel="canonical">; the canonical URL lives in the
    # footer as <a class="p-canonical">Canonical link</a>.
    a = soup.find("a", class_="p-canonical", href=True)
    return a["href"].strip() if a else None


def _extract_date(soup: BeautifulSoup) -> str | None:
    """Publish date as an RFC 3339 string, from the Medium export footer.

    Medium puts it in <time class="dt-published" datetime="2025-10-02T11:15:52.897Z">;
    there is no date in <head>. Falls back to parsing the human-readable text.
    """
    t = soup.find("time", class_="dt-published")
    if t is None:
        return None
    iso = t.get("datetime")
    if iso:
        try:
            return dateparser.isoparse(iso.strip()).replace(microsecond=0).isoformat()
        except (ValueError, OverflowError):
            pass
    text = t.get_text(strip=True)
    if text:
        try:
            return dateparser.parse(text).date().isoformat()
        except (ValueError, OverflowError):
            pass
    return None


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


def _body_section(soup: BeautifulSoup):
    """The post body element, excluding title header and export footer.

    Medium's export puts the post body in <section data-field="body" class="e-content">
    and the author/date/canonical/"Exported from Medium" boilerplate in a separate
    sibling <footer>. So this section is the real content, minus the title (which lives
    in <header>) and minus the footer boilerplate.
    """
    return soup.find("section", attrs={"data-field": "body"})


def _body_word_count(soup: BeautifulSoup) -> int:
    """Word count of the post body, excluding title header and export footer."""
    body = _body_section(soup)
    if body is not None:
        text = body.get_text(" ", strip=True)
    else:
        # Fallback: article (or body) text with any <footer> removed.
        container = soup.find("article") or soup.find("body")
        if container is None:
            return 0
        container = BeautifulSoup(str(container), "lxml")
        for f in container.find_all("footer"):
            f.decompose()
        text = container.get_text(" ", strip=True)
    return len(text.split())


def inspect_post(html_path: Path) -> tuple[str, str | None, int]:
    """Light parse for discovery/filtering: (title, canonical_url, body_word_count).

    body_word_count counts only the post body, so Medium's comment/reply stubs
    (exported as posts) score very low and can be filtered out before conversion.
    """
    raw = html_path.read_text(encoding="utf-8", errors="replace")
    soup = BeautifulSoup(raw, "lxml")
    return _extract_title(soup), _extract_canonical(soup), _body_word_count(soup)


# High-confidence conversational openers for Medium responses (comments/replies).
# Anchored at the title start; only used together with a word ceiling so a real
# post can't be filtered on the title alone.
_REPLY_TITLE_RE = re.compile(
    r"^\s*(thanks\b|thank you\b|thx\b|hi\b|hey\b|hello\b|totally\b|agreed\b|"
    r"congrats\b|congratulations\b|well said\b|good point\b|"
    r"nice (post|article|one|work)\b|great (post|article|read|work)\b)",
    re.IGNORECASE,
)

# A reply-style title above this many words is treated as a real post, not a stub.
REPLY_MAX_WORDS = 250


def classify_stub(title: str, words: int, min_words: int) -> str | None:
    """Return a short reason if this post looks like a comment/reply stub, else None.

    Two signals, both overridable via min_words=0 (filtering off):
      1. Body shorter than min_words.
      2. A conversational reply-style title on a short-ish post (< REPLY_MAX_WORDS).
    Medium exports your responses/comments as posts; this separates them from real posts.
    """
    if min_words <= 0:
        return None
    if words < min_words:
        return f"{words}w < {min_words}"
    if words < REPLY_MAX_WORDS and _REPLY_TITLE_RE.match(title or ""):
        return f"reply-style title ({words}w)"
    return None


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
    image_namer: "ImageNamer",
    image_srcer: "ImageSrcer",
) -> int:
    """In-place: resolve each <img> to a local file or download it into images_dir.

    image_namer(index, ext, content) chooses the saved filename; image_srcer(name)
    chooses what to write back into the <img src> (a bundle-relative path for Hugo,
    a bare filename for Obsidian). Returns the count of images localized. Images that
    can't be resolved/downloaded keep their original src (so the URL survives in the MD).
    """
    images_dir.mkdir(parents=True, exist_ok=True)
    imgs = article_soup.find_all("img", src=True)
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
            content = resolved.read_bytes()
            ext = resolved.suffix.lower() or ".png"
            dest_name = image_namer(i, ext, content)
            (images_dir / dest_name).write_bytes(content)
            img["src"] = image_srcer(dest_name)
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
                dest_name = image_namer(i, ext, r.content)
                (images_dir / dest_name).write_bytes(r.content)
                img["src"] = image_srcer(dest_name)
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


def _hugo_image_namer(index: int, ext: str, content: bytes) -> str:
    return f"{index}{ext}"


def _hugo_image_srcer(name: str) -> str:
    return f"images/{name}"


def convert_html_file(
    html_path: Path,
    tmp_dir: Path,
    images_dir: Path,
    image_namer: "ImageNamer" = _hugo_image_namer,
    image_srcer: "ImageSrcer" = _hugo_image_srcer,
) -> tuple[str, str | None, str | None, str, int]:
    """Parse one post HTML file, localize images into images_dir, return (title, canonical_url, date, markdown_body, num_images_localized).

    image_namer/image_srcer control how images are named and referenced; they default to
    the Hugo scheme (images/<n>.<ext>). Pass Obsidian variants for the Obsidian target.
    """
    raw = html_path.read_text(encoding="utf-8", errors="replace")
    soup = BeautifulSoup(raw, "lxml")
    title = _extract_title(soup)
    canonical = _extract_canonical(soup)
    date = _extract_date(soup)
    article_html = _extract_article_html(soup)
    if not article_html:
        body_md = ""
        localized = 0
    else:
        article_soup = BeautifulSoup(article_html, "lxml")
        # Drop the Medium export footer (author/date/canonical/"Exported from Medium");
        # that metadata now lives in the front matter, so it would be redundant in the body.
        for footer in article_soup.find_all("footer"):
            footer.decompose()
        # Render figure captions in italics (they become a plain paragraph otherwise).
        for fc in article_soup.find_all("figcaption"):
            if fc.get_text(strip=True):
                em = article_soup.new_tag("em")
                for child in list(fc.contents):
                    em.append(child.extract())
                fc.append(em)
        localized = _localize_images(
            article_soup, html_path, tmp_dir, images_dir, image_namer, image_srcer
        )
        body_md = md(
            str(article_soup),
            heading_style="ATX",
            strip=["script", "style"],
            escape_asterisks=False,
            escape_underscores=False,
        )
    return title, canonical, date, (body_md or "").strip(), localized


def slug_from_post(title: str, canonical: str | None) -> str:
    """Generate a Hugo-friendly slug."""
    if canonical and "/" in canonical:
        # e.g. https://medium.com/@user/some-post-slug-41ad5d2bc569
        part = canonical.rstrip("/").split("/")[-1]
        # Drop Medium's trailing post-id hash so the slug stays clean.
        part = _MEDIUM_ID_RE.sub("", part)
        if part and part != "medium.com":
            s = slugify(part, max_length=80)
            if s:
                return s
    return slugify(title, max_length=80) or "untitled"


# Trailing Medium post-id hash on a canonical slug, e.g. "-41ad5d2bc569".
_MEDIUM_ID_RE = re.compile(r"-[0-9a-f]{8,}$")


def _render_note(front: dict, body_md: str) -> str:
    """YAML front matter + body, as a single Markdown string."""
    fm = yaml.dump(front, default_flow_style=False, allow_unicode=True, sort_keys=False)
    out = f"---\n{fm}---\n\n{body_md}"
    if body_md and not body_md.endswith("\n"):
        out += "\n"
    return out


def write_bundle(
    out_root: Path,
    slug: str,
    title: str,
    canonical: str | None,
    body_md: str,
    date: str | None = None,
) -> Path:
    """Write one Hugo page bundle: out_root/<slug>/index.md. Returns path to index.md."""
    bundle_dir = out_root / slug
    bundle_dir.mkdir(parents=True, exist_ok=True)
    front: dict = {"title": title}
    if date:
        front["date"] = date
    front["draft"] = True
    front["slug"] = slug
    if canonical:
        front["medium"] = {"canonical": canonical}
    index_md = bundle_dir / "index.md"
    index_md.write_text(_render_note(front, body_md), encoding="utf-8")
    return index_md


# ---------------------------------------------------------------------------
# Obsidian output target
# ---------------------------------------------------------------------------

DEFAULT_ATTACHMENTS_DIR = "_attachments"

# Characters illegal in filenames (filesystem) or special to Obsidian (#, ^, [, ]).
_ILLEGAL_FILENAME_RE = re.compile(r'[\\/:*?"<>|#^\[\]]+')

# A bare local image filename in Markdown image syntax: ![alt](name.ext) with no
# slashes or scheme (so remote/failed-download URLs are left as standard Markdown).
_BARE_IMAGE_MD_RE = re.compile(r"!\[[^\]]*\]\(([^()\s/]+\.[A-Za-z0-9]+)\)")


def sanitize_note_filename(title: str) -> str:
    """Turn a post title into a safe, human-readable Obsidian note filename (no extension)."""
    name = _ILLEGAL_FILENAME_RE.sub(" ", title or "")
    name = re.sub(r"\s+", " ", name).strip().strip(". ")
    return name[:120].strip() or "Untitled"


def dedupe_name(name: str, used: set[str], sep: str = " ") -> str:
    """Return name (or name+sep+N) not already in used; records the result in used.

    Compared case-insensitively so collisions match Obsidian's filename resolution.
    """
    if name.lower() not in used:
        used.add(name.lower())
        return name
    i = 2
    while f"{name}{sep}{i}".lower() in used:
        i += 1
    final = f"{name}{sep}{i}"
    used.add(final.lower())
    return final


def make_obsidian_image_namer(slug: str) -> ImageNamer:
    """Image filenames unique across the whole vault: <slug>-<n>-<shorthash>.<ext>.

    Obsidian resolves ![[name]] embeds by filename vault-wide (ignoring folders), so
    names must be globally unique; slug + index + content hash guarantees that.
    """

    def namer(index: int, ext: str, content: bytes) -> str:
        short = hashlib.sha256(content).hexdigest()[:8]
        return f"{slug}-{index}-{short}{ext}"

    return namer


def obsidian_image_srcer(name: str) -> str:
    """Obsidian uses a bare filename (resolved vault-wide), not a path."""
    return name


def to_obsidian_embeds(body_md: str) -> str:
    """Rewrite localized images from Markdown ![alt](file.ext) to Obsidian embeds ![[file.ext]]."""
    return _BARE_IMAGE_MD_RE.sub(r"![[\1]]", body_md)


def write_obsidian_note(
    out_root: Path,
    filename: str,
    title: str,
    canonical: str | None,
    body_md: str,
    slug: str,
    date: str | None = None,
    tags: list[str] | None = None,
) -> Path:
    """Write one flat Obsidian note: out_root/<filename>.md. Returns the note path."""
    out_root.mkdir(parents=True, exist_ok=True)
    front: dict = {"title": title}
    if date:
        front["date"] = date
    if tags:
        front["tags"] = tags
    if canonical:
        front["source"] = canonical
    if slug:
        front["aliases"] = [slug]
    note_path = out_root / f"{filename}.md"
    note_path.write_text(_render_note(front, body_md), encoding="utf-8")
    return note_path
