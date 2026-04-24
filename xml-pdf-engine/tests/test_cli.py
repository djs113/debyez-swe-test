import os
import tempfile
from dotenv import load_dotenv
from click.testing import CliRunner
from src.cli import render

# Load environment variables from .env file
load_dotenv()

def test_render_cli():
    """Primary test with automatic cleanup (for CI/CD)"""
    runner = CliRunner()
    sample_xml = os.path.join("data", "samples", "patient_001.xml")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        output_pdf = os.path.join(tmpdir, "output.pdf")
        result = runner.invoke(render, ['--input', sample_xml, '--output', output_pdf])
        
        assert result.exit_code == 0
        assert f"Successfully generated: {output_pdf}" in result.output
        assert os.path.exists(output_pdf)
        assert os.path.getsize(output_pdf) > 0

def test_render_cli_debug():
    """Debug test - saves output for inspection during development"""
    debug_mode = os.getenv("DEBUG_TESTS", "0") == "1"
    
    if not debug_mode:
        return  # Skip if DEBUG_TESTS not set to 1
        
    runner = CliRunner()
    sample_xml = os.path.join("data", "samples", "patient_001.xml")
    output_pdf = os.path.join("test_output", "debug_patient.pdf")
    
    os.makedirs("test_output", exist_ok=True)
    result = runner.invoke(render, ['--input', sample_xml, '--output', output_pdf])
    
    assert result.exit_code == 0
    assert os.path.exists(output_pdf)
    print(f"\nDebug PDF saved to: {os.path.abspath(output_pdf)}")
