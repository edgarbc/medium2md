# medium2md

[![PyPI version](https://img.shields.io/pypi/v/medium2md-cli.svg)](https://pypi.org/project/medium2md-cli/)
[![Python Versions](https://img.shields.io/pypi/pyversions/medium2md-cli.svg)](https://pypi.org/project/medium2md-cli/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> Convert a Medium export ZIP into clean Markdown with localized images, optimized for Hugo and compatible with Obsidian knowledge bases.

**medium2md** is a CLI tool that transforms Medium's HTML export into properly structured Markdown with localized assets. Today, output is optimized for [Hugo](https://gohugo.io/) page bundles and is also readable in [Obsidian](https://obsidian.md/) vaults; planned roadmap work adds stronger Obsidian-specific formatting conventions.

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
| Obsidian compatibility | Current output is Obsidian-readable; dedicated Obsidian formatting profile is planned |

This tool is designed to be **deterministic**, **reproducible**, and **CI-friendly**.

### Primary objective

Generate correctly formatted Markdown files from Medium posts, with images localized into each post bundle, so the output can be used as a durable personal/team knowledge base in Hugo (or other Markdown-first workflows).

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
- Obsidian-friendly output profile (e.g., front matter + file layout conventions for vault workflows)

### Known limitations (current)

- Front matter currently includes `title`, `slug`, `draft`, and optional `medium.canonical`; date/tags are not extracted yet.
- Embedded content is not converted to Hugo shortcodes yet.
- Incremental conversion/state tracking is not implemented yet.
- Output structure is Hugo-first (`content/posts/<slug>/index.md`); a dedicated Obsidian output mode is not implemented yet.

---

## Installation

### Install the CLI

Install **medium2md** once, then run `medium2md` from any directory:

```bash
pip install medium2md-cli
# or
uv tool install medium2md-cli
```

After installation, the CLI command is simply `medium2md`.

### Development checkout

If you're contributing to this repository, use [uv](https://github.com/astral-sh/uv) to create the project environment:

```bash
git clone https://github.com/edgarbc/medium2md.git
cd medium2md
uv sync
```

---

## Usage

Run `medium2md` from wherever you keep your Medium export ZIP. For example, from your home directory:

```bash
cd ~
medium2md ~/Downloads/medium-export.zip --out ~/blog/content/posts
```

If you prefer not to install the CLI first, you can also run it directly with `uvx`:

```bash
uvx medium2md-cli ~/Downloads/medium-export.zip --out ~/blog/content/posts
```

> **Note:** The export ZIP can live anywhere on your machine. It does **not** need to be copied into this repository.

### Example CLI run

Verified example from `~` using a demo Medium export ZIP:

```bash
cd ~
medium2md ~/Downloads/medium-export-demo.zip --out ~/demo-blog/content/posts
```

![CLI screenshot showing medium2md converting a demo Medium export ZIP from the home directory](docs/images/cli-example.png)

If you're developing inside this repository, the git-ignored `input/` directory is still available as an optional scratch location for local ZIP files.

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
├── docs/
│   └── images/
│       └── cli-example.png
├── medium2md/
│   ├── __init__.py
│   ├── cli.py
│   ├── pipeline.py
│   └── main.py
├── pyproject.toml
├── README.md
├── project-plan.md
└── input/
    └── .gitkeep
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
| 2 — Content fidelity + verification | Better metadata extraction (`date`, tags), machine-readable conversion report, `verify` command, clearer failure reporting, Obsidian formatting compatibility review | 📋 Planned |
| 3 — Incremental + extensibility | Incremental state tracking, embed conversion, output-profile mapping (Hugo/Obsidian), optional Pandoc backend, internal link rewriting | 📋 Planned |

### Roadmap status snapshot (code-verified)

- The repository has implemented the core `convert` flow end-to-end.
- Milestone 2 is the highest-impact next step for knowledge-base quality (`date`/tags extraction, verification/reporting, Obsidian compatibility conventions).
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
