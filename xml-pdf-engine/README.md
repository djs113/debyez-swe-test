# XML to PDF Rendering Engine

A CLI tool to convert patient registration XML files into formatted PDF reports.

## Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Required System Libraries:**
   WeasyPrint may require additional system libraries for Pango/GDK-PixBuf. See [WeasyPrint documentation](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#installation).

## Usage

Run the rendering command:
```bash
python src/cli.py render --input data/samples/patient_001.xml --output report.pdf
```

## Running Tests
```bash
pytest
```
