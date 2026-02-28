import zipfile
from pathlib import Path
import tempfile
import typer

app = typer.Typer(help="Convert a Medium export ZIP into Hugo page bundles.")

def find_html_files(root: Path) -> list[Path]:
    return sorted(p for p in root.rglob("*.html") if p.is_file())

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

        html_files = find_html_files(tmp_dir)
        typer.echo(f"Found {len(html_files)} HTML files.")

        for p in html_files[:20]:
            typer.echo(f" - {p.relative_to(tmp_dir)}")