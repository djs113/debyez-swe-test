#!/usr/bin/env python
"""Quick test of schema registry"""
from src.schema_registry import get_registry

# Initialize registry
registry = get_registry()

# Show what was loaded
print('Loaded Schemas:')
for schema_type in registry.list_schemas():
    meta = registry.get_schema_metadata(schema_type)
    print(f'\n{schema_type}:')
    print(f'  Namespace: {meta["namespace"]}')
    print(f'  Root Elements: {meta["root_elements"]}')
    print(f'  Required Children: {meta["required_children"]}')
