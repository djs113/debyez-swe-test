import uuid
import logging

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
from src.core.job_store import create_job, set_processing, set_complete, set_failed, get_job, cleanup_job

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

templates = Jinja2Templates(directory=TEMPLATES_DIR)

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

templates.env.filters['safe_str'] = safe_str
templates.env.filters['truncate_text'] = truncate_text

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


def detect_schema_with_validation(content: bytes):
    """
    Detect XML schema and return validation errors for each schema.
    Returns: (schema_type, validation_errors_dict) or (None, validation_errors_dict)
    Raises: ValueError for malformed XML before attempting schema validation
    """
    # First, validate XML syntax before schema detection
    try:
        parser = etree.XMLParser(resolve_entities=False, remove_blank_text=True)
        etree.fromstring(content, parser=parser)
    except etree.XMLSyntaxError as e:
        logger.error(f"Invalid XML syntax: {e}")
        raise ValueError(f"Invalid XML syntax: {str(e)}")
    except Exception as e:
        logger.error(f"Error parsing XML: {e}")
        raise ValueError(f"Error parsing XML: {str(e)}")

    try:
        registry = get_registry()
        validation_errors = {}

        # Validate against each registered schema's XSD file
        for schema_type in registry.list_schemas():
            is_valid, reason = registry.validate_against_xsd(content, schema_type)
            if is_valid:
                logger.info(f"Schema detected: {schema_type}")
                print(f"  → Detected: {schema_type}")
                return schema_type, {}

            # Store validation error for this schema
            validation_errors[schema_type] = reason
            logger.debug(f"  {schema_type}: {reason}")
            print(f"  {schema_type}: {reason}")

        # No schema matched
        logger.warning(f"No schema matched for uploaded XML")
        print(f"  → No schema matched. XML must validate against a registered XSD.")
        return None, validation_errors

    except Exception as e:
        logger.error(f"Error during schema detection: {e}")
        raise ValueError(f"Error during schema detection: {str(e)}")
    
@app.get("/")
async def get_ui(request: Request):
        return templates.TemplateResponse("index.html", {"request": request})
    
@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    request_id = str(uuid.uuid4())
    temp_path = str(Path.cwd() / f"temp_{request_id}_{file.filename}")

    logger.info(f"[{request_id}] Uploading file: {file.filename}")

    # Clean up any old temp files before creating new one
    base_dir = Path.cwd()
    for old_file in base_dir.glob("temp_*.xml"):
        try:
            old_file.unlink()
            logger.info(f"[Cleanup] Removed old temp file: {old_file.name}")
        except Exception as e:
            logger.warning(f"[Cleanup] Could not remove {old_file.name}: {e}")

    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        logger.info(f"[{request_id}] File saved to {temp_path}")

        with open(temp_path, "rb") as f:
            content = f.read()
            schema, validation_errors = detect_schema_with_validation(content)

        if not schema:
            logger.warning(f"[{request_id}] No schema matched for file {file.filename}")
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "XML validation failed against all registered schemas",
                    "validation_errors": validation_errors
                }
            )

        logger.info(f"[{request_id}] File validated successfully as {schema}")
        return {
            "filename": file.filename,
            "detected_schema": schema,
            "request_id": request_id
        }

    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"[{request_id}] Validation error: {e}")
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise HTTPException(
            status_code=400,
            detail={
                "error": str(e),
                "details": "File must be valid XML matching a registered schema"
            }
        )
    except Exception as e:
        logger.error(f"[{request_id}] Unexpected error: {e}", exc_info=True)
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Error processing XML file",
                "details": str(e)
            }
        )

@app.get("/templates/{schema}")
async def get_templates(schema: str):
    return {"templates": SCHEMA_REGISTRY[schema]["templates"]}

@app.post("/validate/{request_id}/{schema}")
async def validate_file(request_id: str, schema: str):
    """Validate an already-uploaded file against a specific schema."""
    base_dir = Path.cwd()

    # Find the temp file matching this request_id
    temp_files = list(base_dir.glob(f"temp_{request_id}_*"))
    if not temp_files:
        raise HTTPException(status_code=404, detail="Uploaded file not found")

    temp_path = temp_files[0]

    try:
        with open(temp_path, "rb") as f:
            content = f.read()

        registry = get_registry()
        is_valid, reason = registry.validate_against_xsd(content, schema)

        if is_valid:
            return {"valid": True, "schema": schema}
        else:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": f"XML validation failed against {schema} schema",
                    "validation_error": reason
                }
            )
    except HTTPException:
        raise
    except etree.XMLSyntaxError as e:
        raise HTTPException(
            status_code=400,
            detail={"error": "Invalid XML syntax", "details": str(e)}
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"error": "Error validating file", "details": str(e)}
        )

async def run_render_job(job_id: str, schema: str, filename: str, temp_path: str, output_path: str, template_name: str):
    """Background task to render PDF and update job status."""
    try:
        set_processing(job_id)
        render_document(schema, temp_path, output_path, template_name)
        set_complete(job_id, output_path, filename)
    except Exception as e:
        set_failed(job_id, str(e))

@app.get("/status/{job_id}")
async def get_status(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

@app.get("/download/{job_id}")
async def download_pdf(job_id: str, background_tasks: BackgroundTasks):
    job = get_job(job_id)
    if not job or job["status"] != "COMPLETE":
        raise HTTPException(status_code=404, detail="File not ready")

    pdf_path = job["result"]

    # Schedule cleanup: remove PDF file and job from store
    def cleanup_after_download():
        if os.path.exists(pdf_path):
            os.remove(pdf_path)
        cleanup_job(job_id)

    background_tasks.add_task(cleanup_after_download)

    return FileResponse(
        pdf_path,
        media_type='application/pdf',
        filename=f"{job['filename'].split('.')[0]}.pdf"
    )

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

    job_id = create_job()

    # Fire and forget: background rendering (cleanup of temp file happens inside run_render_job)
    background_tasks.add_task(
        run_render_job, job_id, schema, filename, temp_path, output_path, template_name
    )

    return {"job_id": job_id, "status": "PENDING"}