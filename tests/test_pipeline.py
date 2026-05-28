"""Tests for medium2md pipeline: Hugo and Obsidian output formats."""

import textwrap
import zipfile
from pathlib import Path

import pytest
import yaml

from medium2md.pipeline import (
    OutputFormat,
    convert_html_file,
    find_post_html_files,
    slug_from_post,
    write_bundle,
    write_note,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

MINIMAL_HTML = textwrap.dedent("""\
    <!DOCTYPE html>
    <html>
    <head>
      <title>Hello World</title>
      <link rel="canonical" href="https://medium.com/@user/hello-world-abc123"/>
    </head>
    <body>
      <article>
        <h1>Hello World</h1>
        <p>This is the post body.</p>
      </article>
    </body>
    </html>
""")

MINIMAL_HTML_NO_CANONICAL = textwrap.dedent("""\
    <!DOCTYPE html>
    <html>
    <head><title>No Canonical Post</title></head>
    <body><article><h1>No Canonical Post</h1><p>Body.</p></article></body>
    </html>
""")


def _make_post_html(tmp_path: Path, content: str = MINIMAL_HTML, name: str = "post.html") -> Path:
    """Write HTML to tmp_path/posts/<name> and return the file path."""
    posts_dir = tmp_path / "posts"
    posts_dir.mkdir(parents=True, exist_ok=True)
    html_file = posts_dir / name
    html_file.write_text(content, encoding="utf-8")
    return html_file


def _read_front_matter(md_path: Path) -> dict:
    """Parse YAML front matter from a Markdown file."""
    text = md_path.read_text(encoding="utf-8")
    assert text.startswith("---\n"), f"No front matter in {md_path}"
    end = text.index("---\n", 4)
    return yaml.safe_load(text[4:end])


# ---------------------------------------------------------------------------
# slug_from_post
# ---------------------------------------------------------------------------


def test_slug_from_canonical():
    slug = slug_from_post("Hello World", "https://medium.com/@user/hello-world-abc123")
    assert slug == "hello-world-abc123"


def test_slug_from_title_fallback():
    slug = slug_from_post("Hello World", None)
    assert slug == "hello-world"


def test_slug_untitled_fallback():
    slug = slug_from_post("", None)
    assert slug == "untitled"


# ---------------------------------------------------------------------------
# write_bundle (Hugo format)
# ---------------------------------------------------------------------------


def test_write_bundle_creates_index_md(tmp_path):
    out = tmp_path / "posts"
    out.mkdir()
    result = write_bundle(out, "my-post", "My Post", "https://medium.com/@u/my-post", "Body text.")
    assert result == out / "my-post" / "index.md"
    assert result.exists()


def test_write_bundle_front_matter(tmp_path):
    out = tmp_path / "posts"
    out.mkdir()
    write_bundle(out, "my-post", "My Post", "https://medium.com/@u/my-post", "Body.")
    fm = _read_front_matter(out / "my-post" / "index.md")
    assert fm["title"] == "My Post"
    assert fm["slug"] == "my-post"
    assert fm["draft"] is True
    assert fm["medium"]["canonical"] == "https://medium.com/@u/my-post"


def test_write_bundle_no_canonical(tmp_path):
    out = tmp_path / "posts"
    out.mkdir()
    write_bundle(out, "my-post", "My Post", None, "Body.")
    fm = _read_front_matter(out / "my-post" / "index.md")
    assert "medium" not in fm


def test_write_bundle_body_content(tmp_path):
    out = tmp_path / "posts"
    out.mkdir()
    write_bundle(out, "slug", "Title", None, "Some **bold** text.")
    content = (out / "slug" / "index.md").read_text(encoding="utf-8")
    assert "Some **bold** text." in content


# ---------------------------------------------------------------------------
# write_note (Obsidian format)
# ---------------------------------------------------------------------------


def test_write_note_creates_flat_md(tmp_path):
    result = write_note(tmp_path, "my-note", "My Note", "https://medium.com/@u/my-note", "Body.")
    assert result == tmp_path / "my-note.md"
    assert result.exists()


def test_write_note_front_matter(tmp_path):
    write_note(tmp_path, "my-note", "My Note", "https://medium.com/@u/my-note", "Body.")
    fm = _read_front_matter(tmp_path / "my-note.md")
    assert fm["title"] == "My Note"
    assert fm["source"] == "https://medium.com/@u/my-note"
    # Obsidian notes should NOT include Hugo-specific keys
    assert "slug" not in fm
    assert "draft" not in fm
    assert "medium" not in fm


def test_write_note_no_canonical(tmp_path):
    write_note(tmp_path, "my-note", "My Note", None, "Body.")
    fm = _read_front_matter(tmp_path / "my-note.md")
    assert "source" not in fm


def test_write_note_body_content(tmp_path):
    write_note(tmp_path, "slug", "Title", None, "Some **bold** text.")
    content = (tmp_path / "slug.md").read_text(encoding="utf-8")
    assert "Some **bold** text." in content


# ---------------------------------------------------------------------------
# convert_html_file — Hugo layout
# ---------------------------------------------------------------------------


def test_convert_html_file_hugo_returns_title_and_body(tmp_path):
    html_file = _make_post_html(tmp_path)
    bundle_dir = tmp_path / "out" / "hello-world-abc123"
    bundle_dir.mkdir(parents=True)
    title, canonical, body_md, num_images = convert_html_file(html_file, tmp_path, bundle_dir)
    assert title == "Hello World"
    assert canonical == "https://medium.com/@user/hello-world-abc123"
    assert "Hello World" in body_md
    assert "post body" in body_md
    assert num_images == 0


def test_convert_html_file_hugo_images_dir(tmp_path):
    """Hugo: images should land in bundle_dir/images/ by default."""
    html_file = _make_post_html(tmp_path)
    bundle_dir = tmp_path / "out" / "slug"
    bundle_dir.mkdir(parents=True)
    convert_html_file(html_file, tmp_path, bundle_dir)
    # No remote images in the test HTML; images dir may or may not be created
    # (it is only created when there are actual <img> tags to localise).
    # The important thing is that the function doesn't crash.


# ---------------------------------------------------------------------------
# convert_html_file — Obsidian layout
# ---------------------------------------------------------------------------


def test_convert_html_file_obsidian_custom_images_dir(tmp_path):
    """Obsidian: pass explicit images_dir and src_prefix."""
    html_file = _make_post_html(tmp_path)
    assets_dir = tmp_path / "vault" / "assets" / "hello-world"
    title, canonical, body_md, num_images = convert_html_file(
        html_file,
        tmp_path,
        tmp_path / "vault",
        images_dir=assets_dir,
        src_prefix="assets/hello-world/",
    )
    assert title == "Hello World"
    assert "Hello World" in body_md
    assert num_images == 0


# ---------------------------------------------------------------------------
# find_post_html_files
# ---------------------------------------------------------------------------


def test_find_post_html_files_with_posts_dir(tmp_path):
    (tmp_path / "posts").mkdir()
    (tmp_path / "posts" / "a.html").write_text("<html/>", encoding="utf-8")
    (tmp_path / "posts" / "b.html").write_text("<html/>", encoding="utf-8")
    (tmp_path / "blocks").mkdir()
    (tmp_path / "blocks" / "x.html").write_text("<html/>", encoding="utf-8")  # should be ignored
    result = find_post_html_files(tmp_path)
    names = {p.name for p in result}
    assert "a.html" in names
    assert "b.html" in names


def test_find_post_html_files_excludes_non_post_dirs(tmp_path):
    for d in ("blocks", "bookmarks", "claps"):
        (tmp_path / d).mkdir()
        (tmp_path / d / "x.html").write_text("<html/>")
    (tmp_path / "README.html").write_text("<html/>")
    (tmp_path / "my-post.html").write_text("<html/>")
    result = find_post_html_files(tmp_path)
    names = [p.name for p in result]
    assert "my-post.html" in names
    assert "x.html" not in names
    assert "README.html" not in names


# ---------------------------------------------------------------------------
# OutputFormat enum
# ---------------------------------------------------------------------------


def test_output_format_values():
    assert OutputFormat.hugo == "hugo"
    assert OutputFormat.obsidian == "obsidian"


def test_output_format_from_string():
    assert OutputFormat("hugo") is OutputFormat.hugo
    assert OutputFormat("obsidian") is OutputFormat.obsidian


# ---------------------------------------------------------------------------
# End-to-end: ZIP → Hugo bundle
# ---------------------------------------------------------------------------


def _make_zip(tmp_path: Path, posts: dict[str, str]) -> Path:
    """Create a minimal Medium-style export ZIP from a dict of {filename: html_content}."""
    zip_path = tmp_path / "export.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        for name, content in posts.items():
            zf.writestr(f"posts/{name}", content)
    return zip_path


def test_e2e_hugo(tmp_path):
    """End-to-end test: ZIP → Hugo bundle via CLI runner."""
    from typer.testing import CliRunner
    from medium2md.cli import app

    zip_path = _make_zip(tmp_path, {"hello-world.html": MINIMAL_HTML})
    out_dir = tmp_path / "out"
    out_dir.mkdir()

    runner = CliRunner()
    result = runner.invoke(app, [str(zip_path), "--out", str(out_dir), "--format", "hugo"])
    assert result.exit_code == 0, result.output
    index_md = out_dir / "hello-world-abc123" / "index.md"
    assert index_md.exists()
    fm = _read_front_matter(index_md)
    assert fm["title"] == "Hello World"
    assert fm["slug"] == "hello-world-abc123"
    assert fm["draft"] is True


def test_e2e_obsidian(tmp_path):
    """End-to-end test: ZIP → Obsidian note via CLI runner."""
    from typer.testing import CliRunner
    from medium2md.cli import app

    zip_path = _make_zip(tmp_path, {"hello-world.html": MINIMAL_HTML})
    out_dir = tmp_path / "vault"
    out_dir.mkdir()

    runner = CliRunner()
    result = runner.invoke(app, [str(zip_path), "--out", str(out_dir), "--format", "obsidian"])
    assert result.exit_code == 0, result.output
    note_md = out_dir / "hello-world-abc123.md"
    assert note_md.exists()
    fm = _read_front_matter(note_md)
    assert fm["title"] == "Hello World"
    assert fm["source"] == "https://medium.com/@user/hello-world-abc123"
    assert "slug" not in fm
    assert "draft" not in fm


def test_e2e_obsidian_no_bundle_dir(tmp_path):
    """Obsidian output must NOT create a <slug>/ subdirectory for the note itself."""
    from typer.testing import CliRunner
    from medium2md.cli import app

    zip_path = _make_zip(tmp_path, {"hello-world.html": MINIMAL_HTML})
    out_dir = tmp_path / "vault"
    out_dir.mkdir()

    runner = CliRunner()
    runner.invoke(app, [str(zip_path), "--out", str(out_dir), "--format", "obsidian"])
    # A slug directory should only exist if there were images (assets/<slug>/)
    # The note must be a flat file, not a bundle directory.
    assert (out_dir / "hello-world-abc123.md").is_file()
    assert not (out_dir / "hello-world-abc123" / "index.md").exists()
