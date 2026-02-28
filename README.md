# medium2md

[![PyPI version](https://img.shields.io/pypi/v/medium2md.svg)](https://pypi.org/project/medium2md/)
[![Python Versions](https://img.shields.io/pypi/pyversions/medium2md.svg)](https://pypi.org/project/medium2md/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> Convert a Medium export ZIP into clean, Hugo-ready Markdown page bundles.

**medium2md** is a CLI tool that transforms Medium's HTML export into properly structured [Hugo](https://gohugo.io/) content using page bundles — enabling full ownership of your content and a clean, reproducible migration from Medium to Hugo.

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

This tool is designed to be **deterministic**, **reproducible**, and **CI-friendly**.

---

## Features

### MVP (current)

- Convert Medium export ZIP (posts under `posts/` in the export)
- Extract title and canonical URL; generate slug
- Convert HTML to Markdown
- Create Hugo page bundles with `index.md` and optional `images/`
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
pip install medium2md
# or with uv:
uv tool install medium2md
```

---

## Usage

Copy your Medium export ZIP into the `input/` directory (already set up and git-ignored):

```bash
cp ~/Downloads/medium-export.zip input/
uv run medium2md input/medium-export.zip --out ../blog/content/posts
```

> **Note:** The `input/` directory is tracked by git (via `.gitkeep`) so it exists after a fresh clone, but its contents are ignored — your ZIP files will never be accidentally committed.

### Front Matter Example

Each converted post produces an `index.md` with Hugo-compatible YAML front matter. Current output:

```yaml
---
title: "My Post Title"
draft: true
slug: "my-post-slug"
medium:
  canonical: "https://medium.com/@you/post-slug"
---
```

Additional keys (e.g. `date`, `lastmod`, `tags`) are planned.

---

## Output Structure

Each Medium post becomes a Hugo page bundle. Image links in the Markdown point into the bundle’s `images/` folder (remote images are downloaded; local images from the export are copied):

```
content/posts/
└── my-post-slug/
    ├── index.md
    └── images/
        ├── 1.png
        ├── 2.jpg
        └── …
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
| 1 — MVP | ZIP ingestion, HTML→Markdown, Hugo bundle writing, image localization | ✅ Done |
| 2 — Robustness | Incremental state tracking, metadata fallback, verify command | 📋 Planned |
| 3 — Polish | Embed conversion, theme config mapping, Pandoc backend, internal link rewriting | 📋 Planned |

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

> Built by [Edgar Bermudez](https://github.com/edgarbc) to enable long-term content ownership and reproducible publishing workflows.
>
> Not affiliated with Medium or any of its subsidiaries.
