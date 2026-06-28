# medium2md

[![PyPI version](https://img.shields.io/pypi/v/medium2md-cli.svg)](https://pypi.org/project/medium2md-cli/)
[![Python Versions](https://img.shields.io/pypi/pyversions/medium2md-cli.svg)](https://pypi.org/project/medium2md-cli/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

<img width="378" height="280" alt="image" src="https://github.com/user-attachments/assets/4e2a0319-68b2-4207-b570-c4dcf8d33f4e" />


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
- Optional machine-readable JSON conversion report (`--report`): per-post records (source, title, slug/output, images, failed image URLs), skipped stubs with reasons, errors, and run summary counts
- `verify` command: checks a converted directory for broken local image links and invalid/missing front matter (errors), and reports leftover remote image URLs and empty bodies (warnings); non-zero exit on errors for CI

### Planned

- Extract date and optional metadata (tags, etc.) into front matter
- Incremental runs via state file
- Embed detection and shortcode conversion (YouTube, Twitter, Gist)
- Pandoc backend option
- Theme-specific front matter mapping

### Known limitations (current)

- Front matter currently includes `title`, `slug`, `draft`, and optional `medium.canonical`; date/tags are not extracted yet.
- Embedded content is not converted to Hugo shortcodes yet.
- Incremental conversion/state tracking is not implemented yet.
- Output structure is Hugo-first (`content/posts/<slug>/index.md`); a dedicated Obsidian output mode is not implemented yet.

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
uv run medium2md convert input/medium-export.zip --out ../blog/content/posts
```

> **Note:** The `input/` directory is tracked by git (via `.gitkeep`) so it exists after a fresh clone, but its contents are ignored — your ZIP files will never be accidentally committed.

To record a machine-readable summary of the run (useful in CI), pass `--report`:

```bash
uv run medium2md convert input/medium-export.zip --out ../blog/content/posts --report report.json
```

The report lists every converted post (source, slug/output path, image count, and any image URLs that failed to download), the skipped comment/reply stubs with their reasons, per-post errors, and run-level summary counts.

### Verifying output

After a conversion, `verify` checks the output directory for integrity — invalid/missing front matter and broken local image links are reported as **errors** (non-zero exit); images left as remote URLs (failed downloads) and empty bodies are **warnings**:

```bash
uv run medium2md verify ../blog/content/posts            # Hugo bundles
uv run medium2md verify ./vault --target obsidian        # Obsidian notes (checks ![[...]] embeds)
```

Use the same `--target` (and `--attachments-dir` for Obsidian) you used for the conversion.

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
| 1 — Core conversion | ZIP ingestion, post discovery, HTML→Markdown conversion, Hugo bundle writing, local/remote image localization, slug collision handling | ✅ Implemented |
| 2 — Content fidelity + verification | Filter out comment/reply stubs (word-count gate, reported + overridable); better metadata extraction (`date`/`tags`/canonical from the body footer); machine-readable conversion report; `verify` command; clearer failure reporting | ✅ Implemented (stub filtering, `date`/canonical extraction, `--report` JSON, and `verify` all shipped; `tags` omitted — the export HTML carries none) |
| 3 — Obsidian output mode | `--target hugo\|obsidian` output-profile flag; flat `<Title>.md` notes into `--out`; shared `_attachments/` folder with collision-safe `<slug>-<n>-<hash>.<ext>` image names; `![[...]]` embeds; figcaptions as italic captions; Obsidian front matter (date/source/aliases, no draft/slug) | ✅ Implemented (wikilink rewriting between posts still planned) |
| 4 — Incremental + extensibility | Incremental state tracking, embed conversion, optional Pandoc backend, internal link rewriting (Hugo), config/theme front-matter mapping | 📋 Planned |

### Roadmap status snapshot (code-verified)

- The repository has implemented the core `convert` flow end-to-end (Hugo output).
- Milestone 2 is complete (stub filtering, `date`/canonical extraction, `--report` JSON, and the `verify` command); `tags` are omitted only because the export HTML carries none.
- Milestone 3 adds Obsidian as a co-equal output target (alongside Hugo), building on M2's richer metadata.
- Milestone 4 remains optional/polish after fidelity, verification, and Obsidian output are stable.

---

## Contributing

Contributions are welcome! To get started:

1. Fork the repository
2. Create a feature branch (`git checkout -b feat/my-feature`)
3. Make your changes
4. Open a pull request (run `uv run medium2md convert --help` to confirm the CLI works)

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
