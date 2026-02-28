import zipfile
from pathlib import Path
import tempfile
import typer

from medium2md.pipeline import (
    find_post_html_files,
    get_title_canonical,
    convert_html_file,
    slug_from_post,
    write_bundle,
)

app = typer.Typer(help="Convert a Medium export ZIP into Hugo page bundles.")


@app.command()
def convert(
    export_zip: Path = typer.Argument(..., exists=True, file_okay=True, dir_okay=False),
    out: Path = typer.Option(Path("content/posts"), "--out", "-o"),
):
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
        written = 0
        errors = 0

        for i, html_path in enumerate(post_files, 1):
            rel = html_path.relative_to(tmp_dir)
            try:
                title, canonical = get_title_canonical(html_path)
                slug = slug_from_post(title, canonical)
                base_slug = slug
                while slug in used_slugs:
                    # Simple collision: append -2, -3, ...
                    suffix = 2 if slug == base_slug else int(slug.split("-")[-1]) + 1
                    slug = f"{base_slug}-{suffix}"
                used_slugs.add(slug)
                bundle_dir = out / slug
                bundle_dir.mkdir(parents=True, exist_ok=True)
                title, canonical, body_md, num_images = convert_html_file(html_path, tmp_dir, bundle_dir)
                write_bundle(out, slug, title, canonical, body_md)
                written += 1
                img_info = f" ({num_images} image(s))" if num_images else ""
                typer.echo(f"  [{i}/{len(post_files)}] {slug}  →  {out / slug / 'index.md'}{img_info}")
            except Exception as e:
                errors += 1
                typer.echo(
                    typer.style(f"  [{i}/{len(post_files)}] Failed {rel}: {e}", fg="red"),
                    err=True,
                )

        typer.echo("")
        if written:
            typer.echo(typer.style(f"Done. {written} post(s) written to {out}", fg="green"))
        if errors:
            typer.echo(typer.style(f"Failed: {errors} post(s) could not be converted.", fg="red"), err=True)
        if written == 0:
            typer.echo(
                typer.style(
                    "No posts were written. Check errors above or export structure (expected 'posts/' folder).",
                    fg="yellow",
                ),
                err=True,
            )
            raise typer.Exit(1)