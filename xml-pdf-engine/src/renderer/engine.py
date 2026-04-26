import os
import pdfkit
from jinja2 import Environment, FileSystemLoader
from src.core.registry import SCHEMA_REGISTRY

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

def render_document(schema_type, xml_path, output_path, template_name):
    """
    Main engine: uses the Registry to lookup the correct parser and template.
    Generates PDF using pdfkit/wkhtmltopdf.
    """
    # 1. Strategy Lookup
    config = SCHEMA_REGISTRY.get(schema_type)
    if not config:
        raise ValueError(f"No configuration found for schema: {schema_type}")
        
    # 2. Execution (The 'Strategy' in action)
    # The engine doesn't care if it's a Patient or a Billing record;
    # it just knows the parser has a .parse() method.
    parser = config["parser"]
    data = parser.parse(xml_path)
    
    # 3. Dynamic Template Rendering
    template = env.get_template(template_name)
    html_content = template.render(p=data)
    
    # 4. Generate PDF using pdfkit
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