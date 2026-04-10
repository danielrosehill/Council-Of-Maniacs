"""CLI entry point for running career council sessions — used by Claude skills."""

import asyncio
import json
import sys
import os
from pathlib import Path
from datetime import datetime

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from backend.career.council import run_career_council
from backend.career.report import compile_pdf, save_typst_source
from backend.career.config import MODES


def run(background: str, mode: str, output_dir: str | None = None, pdf: bool = True) -> dict:
    """Run career council and generate report. Returns paths and summary."""
    if output_dir is None:
        output_dir = str(Path(__file__).resolve().parent.parent.parent / "data" / "career-reports")

    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    slug = f"career-{mode}-{timestamp}"

    # Run the council
    results = asyncio.run(run_career_council(background, mode))

    # Save raw JSON
    json_path = os.path.join(output_dir, f"{slug}.json")
    with open(json_path, "w") as f:
        json.dump({"background": background, **results}, f, indent=2)

    # Save Typst source
    typ_path = os.path.join(output_dir, f"{slug}.typ")
    save_typst_source(results, background, typ_path)

    # Compile PDF
    pdf_path = None
    if pdf:
        pdf_path = os.path.join(output_dir, f"{slug}.pdf")
        try:
            compile_pdf(results, background, pdf_path)
        except RuntimeError as e:
            print(f"Warning: PDF compilation failed: {e}", file=sys.stderr)
            print("Typst source saved — you can compile manually.", file=sys.stderr)
            pdf_path = None

    return {
        "json_path": json_path,
        "typst_path": typ_path,
        "pdf_path": pdf_path,
        "mode": mode,
        "mode_label": MODES[mode]["label"],
        "moderator_summary": results["stage3"]["response"],
        "num_ideas": len(results["stage1"]),
    }


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Council of Maniacs — Career Division")
    parser.add_argument("mode", choices=list(MODES.keys()), help="Ideation mode")
    parser.add_argument("--background-file", "-f", required=True, help="Path to file with professional background")
    parser.add_argument("--output-dir", "-o", default=None, help="Output directory for reports")
    parser.add_argument("--no-pdf", action="store_true", help="Skip PDF compilation")

    args = parser.parse_args()

    with open(args.background_file) as f:
        background = f.read().strip()

    if not background:
        print("Error: Background file is empty.", file=sys.stderr)
        sys.exit(1)

    print(f"Running Council of Maniacs — Career Division ({MODES[args.mode]['label']})...")
    print(f"Background: {len(background)} characters loaded")
    print("Summoning 8 unhinged personas...")

    result = run(background, args.mode, args.output_dir, pdf=not args.no_pdf)

    print(f"\nDone! Reports saved:")
    print(f"  JSON: {result['json_path']}")
    print(f"  Typst: {result['typst_path']}")
    if result["pdf_path"]:
        print(f"  PDF:  {result['pdf_path']}")

    print(f"\n--- Moderator's Summary ---\n{result['moderator_summary']}")


if __name__ == "__main__":
    main()
