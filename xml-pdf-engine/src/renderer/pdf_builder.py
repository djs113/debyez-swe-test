import pdfkit
import os
from jinja2 import Environment, FileSystemLoader
from src.parsers.patient import PatientParser

def generate_pdf(xml_path, output_path):
    # 1. Parse Data
    parser = PatientParser()
    patient = parser.parse(xml_path)
    
    # 2. Render HTML
    template_dir = os.path.join(os.path.dirname(__file__), '../templates')
    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template('patient_template.html')
    html_content = template.render(p=patient)
    
    # 3. Configure PDFKit
    config = pdfkit.configuration(wkhtmltopdf=r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe')
    
    # 4. Generate
    options = {
        'page-size': 'Letter',
        'margin-top': '0.75in',
        'margin-right': '0.75in',
        'margin-bottom': '0.75in',
        'margin-left': '0.75in',
    }
    
    pdfkit.from_string(html_content, output_path, configuration=config, options=options)