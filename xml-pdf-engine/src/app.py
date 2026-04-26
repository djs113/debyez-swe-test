import uuid

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request, BackgroundTasks
from fastapi.responses import FileResponse
from fastapi.templating import Jinja2Templates
import os
import shutil
from pathlib import Path
from lxml import etree
from src.renderer.engine import render_document
from src.schema_registry import get_registry
from src.core.registry import SCHEMA_REGISTRY

app = FastAPI()

# Initialize schema registry on startup
@app.on_event("startup")
async def startup_event():
    """Load schema registry when app starts."""
    registry = get_registry()
    print(f"Schema Registry initialized with {len(registry.list_schemas())} schemas: {registry.list_schemas()}")

# Helper to clean up temporary files after sending
def cleanup_files(temp_path: str, output_path: str):
    if os.path.exists(temp_path):
        os.remove(temp_path)
    if os.path.exists(output_path):
        os.remove(output_path)

def detect_schema(content: bytes):
    """
    Detect XML schema type using XSD-based validation against actual XSD files.
    Tests the XML against each registered schema's XSD definition and returns
    the matching schema or None if no schema validates.
    Returns: schema_type (str) or None
    """
    try:
        registry = get_registry()

        # Validate against each registered schema's XSD file
        for schema_type in registry.list_schemas():
            is_valid, _ = registry.validate_against_xsd(content, schema_type)
            if is_valid:
                print(f"  → Detected: {schema_type}")
                return schema_type

        # No schema matched
        print(f"  → No schema matched. XML must validate against a registered XSD.")
        return None

    except etree.XMLSyntaxError as e:
        raise ValueError(f"Invalid XML syntax: {str(e)}")
    except Exception as e:
        raise ValueError(f"Error parsing XML: {str(e)}")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

templates = Jinja2Templates(directory=TEMPLATES_DIR)

@app.get("/")
async def get_ui(request: Request):
        return templates.TemplateResponse("index.html", {"request": request})
    
@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    request_id = str(uuid.uuid4())
    
    temp_path = str(Path.cwd() / f"temp_{request_id}_{file.filename}")
    
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    with open(temp_path, "rb") as f:
        content = f.read()
        schema = detect_schema(content)
        
    if not schema:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise HTTPException(status_code=400, detail="Schema could not be detected.")
        
    return {
        "filename": file.filename, 
        "detected_schema": schema, 
        "request_id": request_id 
    }

@app.get("/templates/{schema}")
async def get_templates(schema: str):
    return {"templates": SCHEMA_REGISTRY[schema]["templates"]}

@app.post("/generate")
async def generate_pdf(
    background_tasks: BackgroundTasks, 
    filename: str = Form(...), 
    schema: str = Form(...),
    request_id: str = Form(...),
    template_name: str = Form(...)
):
    base_dir = Path.cwd()
    temp_path = str(base_dir / f"temp_{request_id}_{filename}")
    output_path = str(base_dir / f"output_{request_id}.pdf")
    
    # 1. Generate PDF
    render_document(schema, temp_path, output_path, template_name)
    
    # 2. Schedule cleanup to happen AFTER the response is sent
    background_tasks.add_task(cleanup_files, temp_path, output_path)
    
    # 3. Return the PDF
    return FileResponse(
        output_path, 
        media_type='application/pdf',
        filename=f"{filename.split('.')[0]}.pdf"
    )