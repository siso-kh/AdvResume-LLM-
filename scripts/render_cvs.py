"""
CV Renderer — Converts profile JSON to PDF using Jinja2 + WeasyPrint

Usage:
    python scripts/render_cvs.py [--input data/synthetic/profiles.json] [--output-dir data/synthetic]
"""

import json
import argparse
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from xhtml2pdf import pisa


def render_profile_to_html(profile, template_env):
    """Render a single profile to HTML string."""
    template = template_env.get_template("cv_template.html")
    return template.render(**profile)


def render_profile_to_pdf(profile, template_env, output_dir):
    """Render a single profile to PDF file."""
    html_content = render_profile_to_html(profile, template_env)

    # Save HTML for debugging
    html_path = output_dir / f"{profile['id']}.html"
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    # Render PDF
    pdf_path = output_dir / f"{profile['id']}.pdf"
    with open(pdf_path, "wb") as pdf_file:
        pisa_status = pisa.CreatePDF(
            src=html_content,
            dest=pdf_file,
            encoding='utf-8'
        )
        if pisa_status.err:
            raise Exception(f"PDF generation failed with errors: {pisa_status.err}")

    return pdf_path, html_path


def render_all_cvs(input_path, output_dir, template_dir):
    """Render all profiles from JSON to PDF files."""
    # Load profiles
    with open(input_path, "r", encoding="utf-8") as f:
        profiles = json.load(f)

    # Setup Jinja2
    template_env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=True,
    )

    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Render each profile
    success_count = 0
    error_count = 0

    for profile in profiles:
        try:
            pdf_path, html_path = render_profile_to_pdf(profile, template_env, output_path)
            success_count += 1
            if success_count % 10 == 0:
                print(f"  Rendered {success_count}/{len(profiles)} CVs...")
        except Exception as e:
            error_count += 1
            print(f"  ERROR rendering {profile['id']}: {e}")

    print(f"\n{'='*60}")
    print(f"  Rendering complete")
    print(f"  Success: {success_count}")
    print(f"  Errors: {error_count}")
    print(f"  Output: {output_path}")
    print(f"{'='*60}")

    return success_count, error_count


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Render CV profiles to PDF")
    parser.add_argument("--input", type=str, default="data/synthetic/profiles.json", help="Input profiles JSON")
    parser.add_argument("--output-dir", type=str, default="data/synthetic", help="Output directory for PDFs")
    parser.add_argument("--template-dir", type=str, default="templates", help="Template directory")
    args = parser.parse_args()

    render_all_cvs(args.input, args.output_dir, args.template_dir)
