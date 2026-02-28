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
| Image localization | Downloads and rewrites remote image links |
| Canonical URL | Preserves the original Medium URL |
| Conversion reports | Summarizes what was converted and what was skipped |
| Incremental re-runs | *(planned)* Re-run only changed posts |

This tool is designed to be **deterministic**, **reproducible**, and **CI-friendly**.

---

## Features

### MVP (current)

- Convert Medium export ZIP
- Extract title, date, and canonical URL
- Normalize Medium HTML
- Convert HTML to Markdown
- Create Hugo page bundles
- Download and rewrite image links
- Generate a conversion report

### Planned

- Incremental runs via state file
- Embed detection and shortcode conversion (YouTube, Twitter, Gist)
- Pandoc backend option
- Slug collision handling
- Verification command
- Theme-specific front matter mapping

---

## Installation

This project uses [uv](https://github.com/astral-sh/uv) for dependency management.

```bash
git clone https://github.com/edgarbc/medium2md.git
cd medium2md
uv sync
```

Once published to PyPI, you will also be able to install it with:

```bash
pip install medium2md
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

Each converted post produces an `index.md` with Hugo-compatible YAML front matter:

```yaml
---
title: "My Post Title"
date: 2022-04-18T10:03:00Z
lastmod: 2022-06-01T15:10:00Z
draft: true
tags: ["tag1", "tag2"]
slug: "my-post-slug"
medium:
  canonical: "https://medium.com/@you/post-slug"
---
```

---

## Output Structure

Each Medium post becomes a Hugo page bundle:

```
content/posts/
└── my-post-slug/
    ├── index.md
    └── images/
        └── cover.jpg
```

---

## Project Structure

```
medium2md/           
├── medium2md/       
│   ├── __init__.py
│   ├── cli.py
│   └── main.py
├── pyproject.toml
├── README.md
├── project-plan.md
└── input/
    └── medium-export.zip
├── output/
    └── content/
        └── posts/
            └── my-post-slug/
                ├── index.md
                └── images/
                    └── cover.jpg
```

### Pipeline Architecture

medium2md follows a layered pipeline where each stage is isolated, testable, and composable:

```
ZIP -> HTML parsing -> DOM normalization -> Markdown conversion
    -> Asset localization -> Front matter generation -> Hugo bundle writing -> Report
```

> **Philosophy:** Correctness first, cleverness later.

---

## Development Roadmap

| Milestone | Focus | Status |
|---|---|---|
| 1 — MVP | ZIP ingestion, HTML→Markdown, Hugo bundle writing, image localization | 🚧 In Progress |
| 2 — Robustness | Incremental state tracking, slug collision handling, metadata fallback, verify command | 📋 Planned |
| 3 — Polish | Embed conversion, theme config mapping, Pandoc backend, internal link rewriting | 📋 Planned |

---

## Contributing

Contributions are welcome! To get started:

1. Fork the repository
2. Create a feature branch (`git checkout -b feat/my-feature`)
3. Make your changes
4. Run tests: `uv run pytest`
5. Open a pull request

---

## License

This project is licensed under the [MIT License](LICENSE).

---

> Built by [Edgar Bermudez](https://github.com/edgarbc) to enable long-term content ownership and reproducible publishing workflows.
>
> Not affiliated with Medium or any of its subsidiaries.
