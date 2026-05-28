# medium2md

[![PyPI version](https://img.shields.io/pypi/v/medium2md-cli.svg)](https://pypi.org/project/medium2md-cli/)
[![Python Versions](https://img.shields.io/pypi/pyversions/medium2md-cli.svg)](https://pypi.org/project/medium2md-cli/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> Convert a Medium export ZIP into clean Markdown with localized images, optimized for Hugo and Obsidian.

**medium2md** is a CLI tool that transforms Medium's HTML export into properly structured Markdown with localized assets. Output can be generated as [Hugo](https://gohugo.io/) page bundles (default) or as flat [Obsidian](https://obsidian.md/) vault notes, selectable with the `--format` flag.

---

## Table of Contents

- [Why This Exists](#why-this-exists)
- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)
- [Output Structure](#output-structure)
- [Project Structure](#project-structure)
- [Development Roadmap](#development-roadmap)
- [Contributing](#contributing)
- [License](#license)

---

## Why This Exists

Medium allows you to export your account data as a ZIP archive, but the raw export:

- Contains unstructured HTML
- Includes inconsistent metadata
- References remote image URLs

**medium2md** solves this by providing:

| Feature | Description |
|---|---|
| HTML → Markdown | Converts Medium HTML posts to clean Markdown |
| Hugo front matter | Generates YAML front matter from post metadata |
| Image localization | Downloads remote images into each bundle; copies local images when present in the export |
| Canonical URL | Preserves the original Medium URL |
| Conversion reports | Summarizes what was converted and what was skipped |
| Incremental re-runs | *(planned)* Re-run only changed posts |
| Obsidian compatibility | Flat `.md` notes with Obsidian-style front matter (`title`, `source`); assets in a shared `assets/` folder |

This tool is designed to be **deterministic**, **reproducible**, and **CI-friendly**.

### Primary objective

Generate correctly formatted Markdown files from Medium posts, with images localized into each post bundle, so the output can be used as a durable personal/team knowledge base in Hugo (or other Markdown-first workflows).

---

## Features

### MVP (current)

- Convert Medium export ZIP (posts under `posts/` in the export)
- Extract title and canonical URL; generate slug
- Convert HTML to Markdown
- **Hugo format** (default): Hugo page bundles with `index.md` and optional `images/`
- **Obsidian format**: flat `.md` notes with Obsidian-style front matter (`title`, `source`); images in shared `assets/<slug>/`
- Image localization: download remote images into the bundle; copy local images when present in the export
- Basic slug collision handling (`slug-2`, `slug-3`, …)
- Terminal progress and summary; per-post image count; prompt to create missing output dir

### Planned

- Extract date and optional metadata (tags, etc.) into front matter
- Incremental runs via state file
- Embed detection and shortcode conversion (YouTube, Twitter, Gist)
- Pandoc backend option
- Verification command
- Theme-specific front matter mapping
- Conversion report (e.g. JSON/file)

### Known limitations (current)

- Front matter currently includes `title`, `slug`, `draft`, and optional `medium.canonical` (Hugo) or `title` and `source` (Obsidian); date/tags are not extracted yet.
- Embedded content is not converted to Hugo shortcodes yet.
- Incremental conversion/state tracking is not implemented yet.

---

## Installation

This project uses [uv](https://github.com/astral-sh/uv) for dependency management.

```bash
git clone https://github.com/edgarbc/medium2md.git
cd medium2md
uv sync
```

Once published to PyPI, install with:

```bash
pip install medium2md-cli
# or with uv:
uv tool install medium2md-cli
```

The CLI command is still `medium2md`.

---

## Usage

Copy your Medium export ZIP into the `input/` directory (already set up and git-ignored):

```bash
cp ~/Downloads/medium-export.zip input/
uv run medium2md input/medium-export.zip --out ../blog/content/posts
```

> **Note:** The `input/` directory is tracked by git (via `.gitkeep`) so it exists after a fresh clone, but its contents are ignored — your ZIP files will never be accidentally committed.

### Choosing an output format

Use `--format` (or `-f`) to select the output format:

- **`hugo`** (default): each post becomes a Hugo page bundle at `<out>/<slug>/index.md` with images at `<out>/<slug>/images/`.
- **`obsidian`**: each post becomes a flat note at `<out>/<slug>.md` with images at `<out>/assets/<slug>/`. Obsidian-style front matter (`title`, `source`) is used instead of Hugo keys.

```bash
# Hugo format (default)
uv run medium2md input/medium-export.zip --out content/posts

# Obsidian format
uv run medium2md input/medium-export.zip --out my-vault/posts --format obsidian
```

### Front Matter Examples

**Hugo format** (`--format hugo`, default):

```yaml
---
title: "My Post Title"
draft: true
slug: "my-post-slug"
medium:
  canonical: "https://medium.com/@you/post-slug"
---
```

**Obsidian format** (`--format obsidian`):

```yaml
---
title: "My Post Title"
source: "https://medium.com/@you/post-slug"
---
```

Additional keys (e.g. `date`, `lastmod`, `tags`) are planned for both formats.

---

## Output Structure

### Hugo format (default)

Each Medium post becomes a Hugo page bundle. Image links in the Markdown point into the bundle's `images/` folder (remote images are downloaded; local images from the export are copied):

```
content/posts/
└── my-post-slug/
    ├── index.md
    └── images/
        ├── 1.png
        ├── 2.jpg
        └── …
```

### Obsidian format (`--format obsidian`)

Each Medium post becomes a flat Markdown note. Images are placed in a shared `assets/` folder:

```
my-vault/posts/
├── my-post-slug.md
├── another-post.md
└── assets/
    ├── my-post-slug/
    │   ├── 1.png
    │   └── 2.jpg
    └── another-post/
        └── 1.png
```

---

## Project Structure

```
medium2md/
├── medium2md/
│   ├── __init__.py
│   ├── cli.py
│   ├── pipeline.py
│   └── main.py
├── pyproject.toml
├── README.md
├── project-plan.md
└── input/
    └── medium-export.zip
```

### Pipeline Architecture

medium2md follows a layered pipeline:

```
ZIP → extract → find posts → parse HTML → localize images (copy/download) → Markdown conversion → front matter + Hugo bundle write
```

> **Philosophy:** Correctness first, cleverness later.

---

## Development Roadmap

| Milestone | Focus | Status |
|---|---|---|
| 1 — Core conversion | ZIP ingestion, post discovery, HTML→Markdown conversion, Hugo bundle writing, local/remote image localization, slug collision handling | ✅ Implemented |
| 2 — Content fidelity + verification | Better metadata extraction (`date`, tags), machine-readable conversion report, `verify` command, clearer failure reporting, Obsidian output format (`--format obsidian`) | ✅ Implemented (Obsidian format); 📋 Planned (date/tags, verification) |
| 3 — Incremental + extensibility | Incremental state tracking, embed conversion, optional Pandoc backend, internal link rewriting | 📋 Planned |

### Roadmap status snapshot (code-verified)

- The repository has implemented the core `convert` flow end-to-end for both Hugo and Obsidian output formats.
- Milestone 2 next steps: `date`/tags extraction and a `verify` command are the highest-impact remaining items.
- Milestone 3 remains optional/polish after fidelity and verification are stable.

---

## Contributing

Contributions are welcome! To get started:

1. Fork the repository
2. Create a feature branch (`git checkout -b feat/my-feature`)
3. Make your changes
4. Open a pull request (run `uv run medium2md --help` to confirm the CLI works)

---

## Publishing to PyPI (maintainers)

1. Bump `version` in `pyproject.toml`.
2. Build: `uv build` (creates `dist/`).
3. Install dev deps and upload: `uv sync --extra dev` then `uv run twine upload dist/*` (requires a [PyPI API token](https://pypi.org/help/#apitoken); use `__token__` as username).
4. Optionally tag the release: `git tag v0.1.0 && git push --tags`.

## License

This project is licensed under the [MIT License](LICENSE).

---

> Built by [Edgar Bermudez](https://github.com/edgarbc) and [GitHub Copilot](https://github.com/features/copilot) with 💖 to enable long-term content ownership and reproducible publishing workflows.
>
> Not affiliated with Medium or any of its subsidiaries.
