## Goals and non-goals

### Goals

- Convert all Medium posts from a Medium export ZIP into Hugo-ready Markdown.
- Write each post as a Hugo page bundle:
  - `content/posts/<slug>/index.md`
  - `content/posts/<slug>/images/*` (downloaded/copied assets)
  - optional `featured.*`

- Generate Hugo front matter (YAML/TOML).

- Rewrite image links to local bundle paths.

- Produce a report of posts needing manual review (embeds, failed downloads, missing metadata).

- Support incremental runs via a local state file.

### Non-goals (initial v1)

- Perfect conversion of every embed type.

- Continuous sync with Medium (export-based conversion first; “crawl mode” can be v2).

## Current Status

The project is in the **scaffolding phase**. The following files currently exist under the `medium2md/` package subdirectory:

- `medium2md/cli.py`
- `medium2md/main.py`
- `medium2md/__init__.py`
- `pyproject.toml`
- `README.md`
- `project-plan.md`

No pipeline modules have been implemented yet.

Recommended output structure for Hugo

Use page bundles:

content/
  posts/
    my-post-slug/
      index.md
      featured.jpg
      images/
        img-1.jpg
        img-2.png

This avoids collisions and is Hugo-friendly.

## CLI UX design
### Commands

- `medium2md convert <export.zip>`
- `medium2md verify <content-dir>`
- (Optional) `medium2md clean`

### Core flags

`--out content/posts` (default)

`--front-matter yaml|toml` (default yaml)

`--draft` (mark posts as draft)

`--overwrite` (replace existing bundles)

`--incremental` / `--no-incremental` (default incremental on)

`--state .medium2md/state.json`

`--download-images` / `--no-download-images` (default on)

`--since 2023-01-01`

`--only slug1,slug2`

`--report medium2md-report.json`

`--log-level info|debug`

### Config file support (recommended):

`medium2md.config.yaml` or `.toml`

## Python implementation approach
### Recommended stack

- CLI: Typer (very nice UX) or Click

- HTML parsing: BeautifulSoup4 (bs4) + lxml

- HTML → Markdown: one of:

- markdownify (simple)

- html2text (often better for code blocks/links; configurable)

- OR: pandoc if available (best output but external dependency)

- ZIP: zipfile (stdlib)

- HTTP downloads: httpx (or requests)

- YAML front matter: PyYAML

- TOML front matter (optional): tomlkit

- Dates: python-dateutil

- Slugs: python-slugify

- Hashing: hashlib

- Logging: rich (optional but excellent)

### Recommendation:

- Start with BeautifulSoup + markdownify (fast MVP).

- Add optional --converter pandoc for best output when installed.

### Repo structure (GitHub-friendly)
```
medium2md/
  medium2md/
    __init__.py
    cli.py
    config.py
    export_reader.py
    post_parser.py
    html_normalize.py
    md_convert.py
    assets.py
    front_matter.py
    state.py
    verify.py
    report.py
    util.py
  tests/
    fixtures/
      export.zip
    test_convert.py
  pyproject.toml
  README.md
  LICENSE
```
### Package as an installable CLI with pyproject.toml and a console script entry point.

### Medium export ingestion
#### Stage 1: Unzip to a temp directory

`Extract export.zip to .medium2md/tmp/<run-id>/`

`Locate post HTML files by scanning for .html and filtering out non-post pages.`

#### Stage 2: Identify post HTML files

#### Heuristics:

`Has a <title> and a main <article> or content-heavy section`

`Often contains canonical link: <link rel="canonical" href="...">`

`Exclude obvious utility pages (followers, responses, etc.)`

#### Stage 3: Parse metadata + content from each HTML file

For each candidate HTML:

`Parse DOM using BeautifulSoup`

`Extract:`

`title: from <h1> or <title>`

`canonical_url: from <link rel="canonical"> if present`

### Conversion pipeline (core logic)
#### Step 1: Normalize HTML before conversion

`Medium HTML can be very “span-heavy.” Normalize first:`

`Remove junk: nav/footer/share buttons/subscribe panels`

`Convert special constructs:`

`figure + img + figcaption → keep image and store caption text`

`Ensure <pre><code> blocks stay intact`

`Convert separators to <hr>`

Convert pull quotes to <blockquote>

`Remove empty spans/divs`

`Implement as pure DOM transformations in html_normalize.py.`

#### Step 2: HTML → Markdown conversion

In md_convert.py:

Provide converter backends:

markdownify backend (pure python)

optional pandoc backend (subprocess.run) if user chooses --converter pandoc and pandoc is installed.

Post-conversion cleanup:

Normalize consecutive blank lines

Fix fenced code blocks if converter produced indented code

Ensure heading levels are sane (optional)

####Step 3: Asset localization (images)

In `assets.py`:

Find image references before/after conversion:

Prefer parsing from HTML first: <img src=...>

For each image:

- If local in export: copy into bundle

- If remote (e.g. https://miro.medium.com/...): download to bundle

Choose filename strategy:

images/<n>-<shorthash>.<ext> to avoid collisions

Rewrite markdown image links to local:

![alt](images/filename.jpg)

Optional featured image:

Select first image or largest (v2)

Copy or symlink to featured.jpg and set front matter key (theme-dependent)

### Step 4: Hugo front matter generation

In front_matter.py:

YAML default (widely used):

```
---
title: "My Post Title"
date: 2022-04-18T10:03:00Z
lastmod: 2022-06-01T15:10:00Z
draft: true
tags: ["tag1", "tag2"]
categories: []
slug: "my-post-slug"
medium:
  canonical: "https://medium.com/@you/slug"
  source_file: "posts/myfile.html"
---
```

### Make keys configurable (theme mapping), via config file.

#### Step 5: Write Hugo page bundle

In `export_writer` (or inside `post_parser`):

Create directory: content/posts/<slug>/

Write index.md with front matter + markdown body

Create images/ and store assets

If overwrite disabled and folder exists:

if same canonical URL in state → update allowed

else create slug-2

Incremental mode (repeatable runs)

Keep .medium2md/state.json:

Per post:

canonical_url

slug

source_path

content_hash (hash of normalized HTML or final markdown)

published_at

last_run_at

On run:

If content_hash unchanged and output exists → skip

If changed → regenerate post bundle (or update index.md + assets)

Hashing:

Use sha256(normalized_html_bytes) or sha256(markdown_bytes)

“Needs review” reporting

Write medium2md-report.json containing:

Posts with missing title/date/canonical

Embed detections:

iframes

twitter blockquotes/scripts

gist embeds

Image download failures

Conversion warnings (tables, footnotes, etc.)

Slug collisions and resolutions

Also print a human summary at end.

Embed handling (pragmatic v1)

Detect embeds in HTML normalization stage:

YouTube iframe → replace with Hugo shortcode:

{{< youtube VIDEO_ID >}}

Twitter → keep a link + report entry

Unknown iframes → keep link + report entry

Don’t block conversion; just flag in report.

Verify command (quality gates)

medium2md verify content/posts:

Ensure each post folder has index.md

Validate front matter parses correctly

Check that every local image reference exists

Optional: markdownlint or simple heuristics checks

Exit with non-zero code if critical errors (good for CI)

### GitHub setup and CI
#### Packaging

Use `pyproject.toml` with Poetry or Hatch:

Defines medium2md console script entry point

#### GitHub Actions (CI)

On PR:

set up python

install dependencies

run tests

run ruff/black (optional)

run a fixture conversion test and compare snapshots

#### Suggested workflows:

ci.yml: lint + tests

release.yml (optional): build & publish to PyPI (if you want)

For your Hugo blog repo, most people:

run conversion locally

commit generated content/posts/*

Hugo builds site on GitHub Pages / Netlify / Cloudflare Pages

## Milestones (build order)

### Milestone 1 (MVP)

- [ ] convert command works for export.zip
- [ ] Extract title/date/canonical reliably for most posts
- [ ] HTML normalize minimal
- [ ] Convert HTML → MD
- [ ] Write Hugo bundles
- [ ] Basic image download + rewrite
- [ ] Generate report

### Milestone 2 (content fidelity + verification)

- [x] Filter out comment/reply stubs — DONE (2026-06-26). `pipeline.inspect_post()` counts only `<section data-field="body">` words (excludes title header + `<footer>` boilerplate); `pipeline.classify_stub()` flags a stub when words < `--min-words` (default 100) OR a reply-style title (thanks/thank you/hi/hey/hello/totally/great post/…) under 250 words. CLI reports each skip + a summary; `--min-words 0` disables. Verified on the real export: 133 → 117 written + 16 filtered, no false positives. Post-discovery step → benefits both targets. (Did NOT gate on canonical: this export has no `<link rel=canonical>`.)
- [ ] Better metadata extraction fallback paths — parse the body footer (`By … on <date>`) for the publish date and the `[Canonical link](…)` anchor for canonical, since this export has neither in `<head>`. Extract tags into front matter.
- [ ] Fix `_extract_canonical` to fall back to the body footer anchor (currently only checks `<link rel=canonical>`, so canonical is empty for every post in this export).
- [ ] Machine-readable conversion report (`medium2md-report.json`) — include skipped stubs, missing metadata, download failures.
- [ ] verify command
- [ ] Clearer failure reporting

NOTE (test run 2026-06-26): export has no `<link rel=canonical>` and no `<head>` date; the real canonical + publish date live only in the body footer (`By <author> on <date>` · `[Canonical link](url)` · `Exported from Medium on <date>`). The footer is ~20 words of boilerplate the stub word-count must strip before thresholding.

### Milestone 3 (Obsidian output mode)

Emit Obsidian-flavored Markdown notes per post as a co-equal output target to Hugo, selectable via `--target hugo|obsidian`. Builds on M2's richer metadata; consolidates the Obsidian work previously implied by "output-profile mapping".

**Decided conventions (2026-06-26, from a real test run):**

- **Note files:** one `<Title>.md` per post, flat into `--out` (no per-post folder / no `index.md`). Filename = title sanitized of filesystem-illegal AND Obsidian-reserved chars (`/ \ : * ? " < > | # ^ [ ]`); title collisions → numeric suffix or slug fallback.
- **Attachments:** single shared folder at `--out` root (default `_attachments/`, via `--attachments-dir`). `![[name]]` resolves by filename vault-wide, so image names must be globally unique → `<slug>-<n>-<shorthash>.<ext>` (mandatory; current per-folder `<n>.<ext>` collides once flattened).
- **Image links:** Obsidian embed `![[<filename>]]` (not standard markdown).
- **Figcaptions:** Medium `<figcaption>` → italic caption line under the embed (currently dropped to a loose paragraph).
- **Front matter:** `title`, `tags` (list), `created`/`date`, `source` (canonical), optional `aliases`; NO `draft`/`slug` keys.
- **Wikilinks:** rewrite links between converted posts to `[[Note Title]]`.

Tasks:

- [ ] Output-profile abstraction: factor the write step into a profile interface (Hugo bundle / Obsidian note share parse+convert+localize, differ in layout + front matter + image emission)
- [ ] `--target hugo|obsidian` flag (default hugo); `--attachments-dir` (default `_attachments`)
- [ ] Title → filename sanitizer + collision handling (flat into `--out`)
- [ ] Collision-safe image naming `<slug>-<n>-<shorthash>.<ext>` into the shared attachments folder
- [ ] `![[...]]` embed emission for localized images
- [ ] Figcaption → italic caption / embed alt text
- [ ] Obsidian front matter (`title`/`tags`/`created`/`source`/`aliases`; no `draft`/`slug`)
- [ ] `[[wikilink]]` rewriting between converted posts

### Milestone 4 (incremental + extensibility / polish)

- [ ] Incremental state (`.medium2md/state.json`, content-hash skip)
- [ ] Better embed conversions (YouTube/Twitter/Gist)
- [ ] Theme mapping config / config file support
- [ ] Optional pandoc backend
- [ ] Link rewriting among your posts — Hugo target (Obsidian wikilinks handled in M3)

## Concrete “first sprint” checklist (what to implement first)

- [ ] Scaffold typer CLI with convert <zip> --out ...
- [ ] Unzip and list candidate HTML files
- [ ] Parse each HTML:
  - [ ] find canonical url, title, date, main content node
- [ ] Normalize HTML (strip junk)
- [ ] Convert to Markdown (markdownify)
- [ ] Download images + rewrite links
- [ ] Write page bundle + front matter
- [ ] Save state.json + report.json

If you tell me:

`your Hugo theme name (or whether it expects featuredImage, cover, etc.)`

whether you want all posts set to draft initially

whether you want to preserve Medium canonical URLs for SEO
`…I can propose the exact front matter fields + a default medium2md.config.yaml that will drop straight into your blog repo.`