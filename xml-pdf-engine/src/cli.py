import os
import click
from src.renderer.engine import render_document
from src.app import detect_schema

@click.command()
@click.option('--input', '-i', required=True, type=click.Path(exists=True), help='Path to input XML file')
@click.option('--output', '-o', required=True, help='Path for output PDF file')
@click.option('--schema', '-s', default=None, help='Schema type (auto-detected if not provided)')
def render(input, output, schema):
    """Render XML to PDF - auto-detects schema if not specified."""
    try:
        # Ensure the directory for the output file exists
        output_dir = os.path.dirname(output)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)

        click.echo(f"Processing {input}...")
        
        # Auto-detect schema if not provided
        if not schema:
            with open(input, 'rb') as f:
                schema = detect_schema(f.read())
            if not schema:
                click.secho("Error: Could not auto-detect schema type", fg='red', err=True)
                return
            click.echo(f"Detected schema: {schema}")
        
        # Generate PDF using detected schema
        render_document(schema, input, output)
        
        click.secho(f"Successfully generated: {output}", fg='green')
    except Exception as e:
        import traceback
        click.secho(f"Error: {str(e)}", fg='red', err=True)
        traceback.print_exc()

if __name__ == '__main__':
    render()