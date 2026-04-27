import os
import pdfkit
import asyncio
from datetime import datetime
from jinja2 import Environment, FileSystemLoader
from src.core.registry import SCHEMA_REGISTRY
import logging

logger = logging.getLogger(__name__)

# Forward declaration - will be defined below
RENDERERS = {}


# Initialize Jinja2 Environment
TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), '../templates')
env = Environment(
    loader=FileSystemLoader(TEMPLATE_DIR),
    auto_reload=True
)

# Add custom Jinja2 filters for robust rendering
def safe_str(value, default="N/A"):
    """Convert value to string safely, handling None and empty values."""
    if value is None or value == "" or value == []:
        return default
    return str(value).strip()

def truncate_text(value, length=500, suffix="..."):
    """Truncate text to specified length with suffix."""
    if value is None:
        return ""
    text = str(value).strip()
    if len(text) <= length:
        return text
    return text[:length-len(suffix)] + suffix

env.filters['safe_str'] = safe_str
env.filters['truncate_text'] = truncate_text

def _generate_pdf_pdfkit(html_content, output_path):
    """
    Generate PDF using pdfkit with wkhtmltopdf.
    Fast and reliable for standard HTML to PDF conversion.
    """
    try:
        config_pdf = pdfkit.configuration(wkhtmltopdf=r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe')
    except:
        config_pdf = None

    options = {
        'page-size': 'Letter',
        'margin-top': '0.5in',
        'margin-right': '0.5in',
        'margin-bottom': '0.5in',
        'margin-left': '0.5in',
    }

    pdfkit.from_string(html_content, output_path, configuration=config_pdf, options=options)
    logger.info(f"PDF generated with PDFKit: {output_path}")

async def _generate_pdf_playwright(html_content, output_path):
    """
    Generate PDF using Playwright (headless browser automation).
    Provides better CSS support and modern rendering compared to wkhtmltopdf.
    Requires: playwright install (to download browser binaries)
    """
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        raise ImportError("Playwright is not installed. Install with: pip install playwright")

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            await page.set_content(html_content)
            await page.pdf(
                path=output_path,
                format='Letter',
                margin={
                    'top': '0.5in',
                    'right': '0.5in',
                    'bottom': '0.5in',
                    'left': '0.5in'
                }
            )
            await browser.close()
        logger.info(f"PDF generated with Playwright: {output_path}")
    except NotImplementedError as e:
        error_msg = "Playwright browsers not installed. Run: playwright install"
        logger.error(f"Playwright error: {error_msg}")
        raise RuntimeError(error_msg)
    except Exception as e:
        logger.error(f"Error generating PDF with Playwright: {e}")
        raise

async def render_document(schema_type, xml_path, output_path, template_name, strategy='PDFKIT'):
    """
    Main rendering orchestrator: parses XML, renders HTML, and generates PDF.
    Strategy: 'PDFKIT' (default) or 'PLAYWRIGHT'
    """
    if strategy not in RENDERERS:
        raise ValueError(f"Unknown rendering strategy: {strategy}. Available: {list(RENDERERS.keys())}")

    logger.info(f"Rendering {schema_type} PDF with {strategy} strategy")

    # 1. Schema Lookup
    config = SCHEMA_REGISTRY.get(schema_type)
    if not config:
        raise ValueError(f"No configuration found for schema: {schema_type}")

    # 2. Parse XML
    parser = config["parser"]
    data = parser.parse(xml_path)

    # 3. Render HTML from template
    template = env.get_template(template_name)
    html_content = template.render(p=data, now=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    # 4. Generate PDF using selected strategy
    generator = RENDERERS[strategy]
    if strategy == 'PLAYWRIGHT':
        await generator(html_content, output_path)
    else:
        generator(html_content, output_path)

# Populate RENDERERS dictionary after functions are defined
RENDERERS = {
    "PLAYWRIGHT": _generate_pdf_playwright,
    "PDFKIT": _generate_pdf_pdfkit
}