import zipfile
from datetime import datetime, timezone
from pathlib import Path
import tempfile
from typing import Optional

import typer

from medium2md.pipeline import (
    DEFAULT_ATTACHMENTS_DIR,
    build_report,
    find_post_html_files,
    inspect_post,
    classify_stub,
    convert_html_file,
    slug_from_post,
    dedupe_name,
    write_bundle,
    make_obsidian_image_namer,
    obsidian_image_srcer,
    to_obsidian_embeds,
    sanitize_note_filename,
    verify_output,
    write_obsidian_note,
    write_report,
)

app = typer.Typer(help="Convert a Medium export ZIP into Hugo page bundles or Obsidian notes.")


@app.command()
def convert(
    export_zip: Path = typer.Argument(..., exists=True, file_okay=True, dir_okay=False),
    out: Path = typer.Option(Path("content/posts"), "--out", "-o"),
    target: str = typer.Option(
        "hugo",
        "--target",
        "-t",
        help="Output format: 'hugo' (page bundles) or 'obsidian' (flat notes + shared attachments).",
    ),
    attachments_dir: str = typer.Option(
        DEFAULT_ATTACHMENTS_DIR,
        "--attachments-dir",
        help="(obsidian) Shared image folder, relative to --out.",
    ),
    min_words: int = typer.Option(
        100,
        "--min-words",
        help=(
            "Skip posts whose body has fewer than this many words. Medium exports your "
            "comments/replies as posts; this filters out those stubs. Use 0 to include everything."
        ),
    ),
    report: Optional[Path] = typer.Option(
        None,
        "--report",
        help="Write a machine-readable JSON conversion report to this path.",
    ),
):
    """Convert a Medium export ZIP into Hugo page bundles or Obsidian notes."""
    target = target.lower()
    if target not in ("hugo", "obsidian"):
        typer.echo(typer.style(f"Error: --target must be 'hugo' or 'obsidian', got {target!r}.", fg="red"), err=True)
        raise typer.Exit(2)
    out = out.resolve()
    if not out.exists():
        if not typer.confirm(
            f"Output directory does not exist: {out}\nCreate it?",
            default=True,
        ):
            raise typer.Exit(1)
        out.mkdir(parents=True, exist_ok=True)
        typer.echo(f"Created {out}")
    elif not out.is_dir():
        typer.echo(f"Error: Output path is not a directory: {out}", err=True)
        raise typer.Exit(1)

    typer.echo(f"Export: {export_zip}")
    typer.echo(f"Out:    {out}")
    typer.echo(f"Target: {target}")

    with tempfile.TemporaryDirectory(prefix="medium2md_") as td:
        tmp_dir = Path(td)

        with zipfile.ZipFile(export_zip, "r") as z:
            z.extractall(tmp_dir)

        all_html = sorted(tmp_dir.rglob("*.html"))
        post_files = find_post_html_files(tmp_dir)

        typer.echo(f"Found {len(all_html)} HTML file(s) in export, {len(post_files)} post(s) to convert.")

        if not post_files:
            typer.echo(
                typer.style(
                    "Warning: No post HTML files found. "
                    "Expected posts under a 'posts/' folder in the export, or excluded README/blocks/bookmarks/claps/highlights/interests.",
                    fg="yellow",
                ),
                err=True,
            )
            raise typer.Exit(1)

        used_slugs: set[str] = set()
        used_notes: set[str] = set()  # obsidian note filenames (case-insensitive)
        written_records: list[dict] = []
        skipped_records: list[dict] = []
        error_records: list[dict] = []

        for i, html_path in enumerate(post_files, 1):
            rel = html_path.relative_to(tmp_dir)
            try:
                title, canonical, words = inspect_post(html_path)
                stub_reason = classify_stub(title, words, min_words)
                if stub_reason is not None:
                    skipped_records.append(
                        {"source": str(rel), "title": title, "words": words, "reason": stub_reason}
                    )
                    typer.echo(
                        typer.style(
                            f"  [{i}/{len(post_files)}] skipped stub ({stub_reason}): {title}",
                            fg="yellow",
                        )
                    )
                    continue
                # Unique slug (used for Hugo dirs and for Obsidian image filenames).
                slug = dedupe_name(slug_from_post(title, canonical), used_slugs, sep="-")

                if target == "obsidian":
                    images_dir = out / attachments_dir
                    result = convert_html_file(
                        html_path, tmp_dir, images_dir,
                        make_obsidian_image_namer(slug), obsidian_image_srcer,
                    )
                    body_md = to_obsidian_embeds(result.body_md)
                    note_name = dedupe_name(sanitize_note_filename(result.title), used_notes)
                    dest = write_obsidian_note(
                        out, note_name, result.title, result.canonical, body_md, slug, result.date
                    )
                else:
                    result = convert_html_file(html_path, tmp_dir, out / slug / "images")
                    dest = write_bundle(
                        out, slug, result.title, result.canonical, result.body_md, result.date
                    )

                written_records.append(
                    {
                        "source": str(rel),
                        "title": result.title,
                        "slug": slug,
                        "output": str(dest.relative_to(out)),
                        "images": result.num_images,
                        "images_failed": result.failed_images,
                    }
                )
                img_info = f" ({result.num_images} image(s))" if result.num_images else ""
                fail_info = (
                    typer.style(f" [{len(result.failed_images)} image(s) failed]", fg="yellow")
                    if result.failed_images
                    else ""
                )
                typer.echo(f"  [{i}/{len(post_files)}] {dest.relative_to(out)}{img_info}{fail_info}")
            except Exception as e:
                error_records.append({"source": str(rel), "error": str(e)})
                typer.echo(
                    typer.style(f"  [{i}/{len(post_files)}] Failed {rel}: {e}", fg="red"),
                    err=True,
                )

        written = len(written_records)
        errors = len(error_records)
        images_failed = sum(len(p["images_failed"]) for p in written_records)

        typer.echo("")
        if written:
            typer.echo(typer.style(f"Done. {written} post(s) written to {out}", fg="green"))
        if skipped_records:
            typer.echo(
                typer.style(
                    f"Skipped {len(skipped_records)} comment/reply stub(s) under {min_words} words "
                    f"(use --min-words 0 to include them).",
                    fg="yellow",
                )
            )
        if images_failed:
            typer.echo(
                typer.style(
                    f"Note: {images_failed} image(s) failed to download and remain as remote URLs.",
                    fg="yellow",
                )
            )
        if errors:
            typer.echo(typer.style(f"Failed: {errors} post(s) could not be converted.", fg="red"), err=True)

        if report is not None:
            options: dict = {"min_words": min_words}
            if target == "obsidian":
                options["attachments_dir"] = attachments_dir
            report_data = build_report(
                export_zip=export_zip.resolve(),
                out=out,
                target=target,
                options=options,
                html_files=len(all_html),
                posts_considered=len(post_files),
                written=written_records,
                skipped=skipped_records,
                errors=error_records,
                generated_at=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            )
            write_report(report.resolve(), report_data)
            typer.echo(f"Report: {report.resolve()}")

        if written == 0:
            typer.echo(
                typer.style(
                    "No posts were written. Check errors above or export structure (expected 'posts/' folder).",
                    fg="yellow",
                ),
                err=True,
            )
            raise typer.Exit(1)


@app.command()
def verify(
    out: Path = typer.Argument(..., exists=True, file_okay=False, dir_okay=True),
    target: str = typer.Option(
        "hugo",
        "--target",
        "-t",
        help="Output format to verify: 'hugo' (page bundles) or 'obsidian' (flat notes).",
    ),
    attachments_dir: str = typer.Option(
        DEFAULT_ATTACHMENTS_DIR,
        "--attachments-dir",
        help="(obsidian) Shared image folder, relative to the output dir.",
    ),
):
    """Check a converted output directory for integrity (front matter, image links)."""
    target = target.lower()
    if target not in ("hugo", "obsidian"):
        typer.echo(typer.style(f"Error: --target must be 'hugo' or 'obsidian', got {target!r}.", fg="red"), err=True)
        raise typer.Exit(2)
    out = out.resolve()

    notes, issues = verify_output(out, target, attachments_dir)
    if not notes:
        pattern = "*.md" if target == "obsidian" else "*/index.md"
        typer.echo(
            typer.style(
                f"No {target} notes ({pattern}) found under {out}. Wrong --target or directory?",
                fg="yellow",
            ),
            err=True,
        )
        raise typer.Exit(1)

    errors = [i for i in issues if i.level == "error"]
    warnings = [i for i in issues if i.level == "warning"]

    # Errors first, then warnings; grouped enough to scan by note.
    for issue in sorted(issues, key=lambda i: (i.level != "error", i.note, i.kind)):
        color = "red" if issue.level == "error" else "yellow"
        typer.echo(
            typer.style(f"  {issue.level.upper():7} [{issue.kind}] {issue.note}: {issue.detail}", fg=color),
            err=issue.level == "error",
        )

    typer.echo("")
    style = "red" if errors else ("yellow" if warnings else "green")
    typer.echo(
        typer.style(
            f"Checked {len(notes)} note(s): {len(errors)} error(s), {len(warnings)} warning(s).",
            fg=style,
        )
    )
    if errors:
        raise typer.Exit(1)