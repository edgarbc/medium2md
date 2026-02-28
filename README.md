# Medium2MD

Convert a Medium export ZIP into clean, Hugo-ready Markdown page bundles.

medium2md is a CLI tool that transforms Medium’s HTML export into properly structured Hugo content using page bundles:

```
content/posts/<slug>/
  index.md
  images/*
  optional featured.*
```

This enables full ownership of your content and a clean migration from Medium to Hugo.

## Status

This project is in early scaffolding/development. Core files (`cli.py`, `main.py`, `__init__.py`) live under the `medium2md/` package subdirectory. No pipeline modules have been implemented yet.

## Why This Exists

Medium allows you to export your account data as a ZIP archive, but the export:

- Contains raw HTML
- Includes inconsistent metadata
- Uses remote image links

medium2md provides:

- HTML → Markdown conversion
- Hugo front matter generation
- Image localization into page bundles
- Canonical URL preservation
- Conversion reports
- Incremental re-runs (planned)

This tool is designed to be:

- Deterministic
- Reproducible
- CI-friendly
- Hugo-native

## Features

### MVP

- Convert Medium export ZIP
- Extract title, date, canonical URL
- Normalize Medium HTML
- Convert to Markdown
- Create Hugo page bundles
- Download and rewrite image links
- Generate conversion report

### Planned

- Incremental runs via state file
- Embed detection and shortcode conversion
- Pandoc backend option
- Slug collision handling
- Verification command
- Theme-specific front matter mapping

## This project uses uv.

- Clone the repo
- `git clone https://github.com/<your-username>/medium2md.git`
- `cd medium2md`
- Install dependencies
- `uv sync`

### Example:

`uv run medium2md convert export.zip \
  --out ../blog/content/posts`

### Output Structure

Each Medium post becomes a Hugo page bundle:

```
content/posts/my-post-slug/
  index.md
  images/*
```

### Front matter example:

```
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

### Project Structure

```
medium2md/       (repo root)
  medium2md/     (Python package)
    __init__.py
    cli.py
    main.py
  pyproject.toml
  README.md
  project-plan.md
```

### Development Roadmap

Milestone 1 — MVP

- ZIP ingestion
- Post detection
- HTML normalization
- Markdown conversion
- Hugo bundle writing
- Basic image localization

Milestone 2 — Robustness

- Incremental state tracking
- Slug collision handling
- Metadata fallback logic
- Verify command

Milestone 3 — Polish

- Embed conversion (YouTube, Twitter, Gist)
- Theme config mapping
- Pandoc backend option
- Internal link rewriting

### Philosophy

This tool follows a layered pipeline:

- ZIP
- HTML parsing
- DOM normalization
- Markdown conversion
- Asset localization
    - Front matter generation
    - Hugo bundle writing
    - Report generation

Each stage is isolated, testable, and composable.

The goal is correctness first, cleverness later.

### Contributing

- Fork the repo
- Create a feature branch
- Make your changes
- Run tests: `uv run pytest`
- Open a pull request

### License

MIT License.

### Author

Edgar Bermudez

### Built to enable long-term content ownership and reproducible publishing workflows.

It is not affiliated with Medium or any of its subsidiaries.

