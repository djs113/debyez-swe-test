import uuid

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request, BackgroundTasks
from fastapi.responses import FileResponse, HTMLResponse
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

# Helper to clean up output PDF files after download
def cleanup_output_pdf(output_path: str):
    """Only clean up the output PDF, not the input XML temp file"""
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

try:
    templates = Jinja2Templates(directory=TEMPLATES_DIR)
except Exception as e:
    print(f"Error initializing templates: {e}")
    templates = None

@app.get("/")
async def get_ui():
    # Read and return the HTML file directly
    index_path = os.path.join(TEMPLATES_DIR, "index.html")
    if not os.path.exists(index_path):
        raise HTTPException(status_code=404, detail="UI template not found")

    with open(index_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    return HTMLResponse(content=html_content)
    
@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    request_id = str(uuid.uuid4())

    # Clean up any old temp files from previous uploads
    base_dir = Path.cwd()
    old_temp_files = list(base_dir.glob("temp_*"))
    for old_file in old_temp_files:
        try:
            old_file.unlink()  # Delete the old temp file
        except Exception as e:
            print(f"Warning: Could not delete old temp file {old_file}: {e}")

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

    # Validate that XML matches the selected schema before generating
    try:
        with open(temp_path, "rb") as f:
            content = f.read()

        registry = get_registry()
        is_valid, reason = registry.validate_against_xsd(content, schema)

        if not is_valid:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": f"XML does not match the selected {schema} schema",
                    "validation_error": reason
                }
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Error validating file against schema",
                "details": str(e)
            }
        )

    # 1. Generate PDF
    render_document(schema, temp_path, output_path, template_name)

    # 2. Schedule cleanup of output PDF only (keep temp XML for future generations)
    background_tasks.add_task(cleanup_output_pdf, output_path)

    # 3. Return the PDF
    return FileResponse(
        output_path,
        media_type='application/pdf',
        filename=f"{filename.split('.')[0]}.pdf"
    )