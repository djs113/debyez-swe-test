#!/usr/bin/env python
"""Debug billing PDF rendering"""
from src.renderer.engine import render_document
import traceback

try:
    print("Starting billing PDF render...")
    render_document('BILLING', 'data/samples/billing_001.xml', 'test_billing.pdf')
    print("Success!")
except Exception as e:
    print(f"Error: {e}")
    traceback.print_exc()
