from setuptools import setup, find_packages

setup(
    name="xml_pdf_renderer",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "click",
        "lxml",
        "jinja2",
        "pdfkit",
        "pydantic",
    ],
    entry_points={
        'console_scripts': [
            'render=src.cli:render',
        ],
    },
)