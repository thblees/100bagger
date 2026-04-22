"""Build HTML report → PDF using Microsoft Edge headless."""
import subprocess
import sys
from pathlib import Path

EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
HERE = Path(__file__).resolve().parent


def html_to_pdf(html_path: Path, pdf_path: Path) -> None:
    """Convert an HTML file to PDF via Edge headless."""
    html_url = html_path.resolve().as_uri()
    cmd = [
        EDGE,
        "--headless=new",
        "--disable-gpu",
        "--no-pdf-header-footer",
        f"--print-to-pdf={pdf_path.resolve()}",
        html_url,
    ]
    print("Running Edge headless...")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        print("STDOUT:", result.stdout)
        print("STDERR:", result.stderr)
        raise RuntimeError(f"Edge failed with exit code {result.returncode}")
    if not pdf_path.exists():
        raise RuntimeError(f"PDF was not created at {pdf_path}")
    print(f"OK -> {pdf_path}  ({pdf_path.stat().st_size / 1024:.1f} KB)")


def main():
    html_file = HERE / "report.html"
    pdf_file = HERE / "100bagger-report-Q2-2026-PROTOTYP.pdf"
    if not html_file.exists():
        print(f"missing: {html_file}")
        sys.exit(1)
    html_to_pdf(html_file, pdf_file)


if __name__ == "__main__":
    main()
