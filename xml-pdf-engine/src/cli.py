import os

import click
from src.renderer.pdf_builder import generate_pdf

@click.command()
@click.option('--input', '-i', required=True, type=click.Path(exists=True), help='Path to input XML file')
@click.option('--output', '-o', required=True, help='Path for output PDF file')
def render(input, output):
    """Simple CLI to render XML to PDF."""
    try:
        # Ensure the directory for the output file exists
        output_dir = os.path.dirname(output)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)

        click.echo(f"Processing {input}...")
        
        generate_pdf(input, output)
        
        click.secho(f"Successfully generated: {output}", fg='green')
    except Exception as e:
        click.secho(f"Error: {str(e)}", fg='red', err=True)

if __name__ == '__main__':
    render()