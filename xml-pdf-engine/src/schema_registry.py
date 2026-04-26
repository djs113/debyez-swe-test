"""
Dynamic schema registry loaded from XSD files.
Parses XSD files to extract namespace, root elements, and required structure.
"""

from lxml import etree
import os
from pathlib import Path
from typing import Dict, List, Tuple, Optional


class SchemaRegistry:
    """
    Dynamically load and parse XSD files to create a registry of schema metadata.
    Enables detection based on actual XSD definitions rather than hardcoded values.
    """
    
    def __init__(self, schemas_dir: str = None):
        if schemas_dir is None:
            # Use absolute path relative to this module
            base_dir = Path(__file__).parent.parent
            schemas_dir = base_dir / "data" / "schemas"
        
        self.schemas_dir = Path(schemas_dir)
        self.registry: Dict[str, Dict] = {}
        self.load_schemas()
    
    def load_schemas(self):
        """Load all XSD files from schemas directory."""
        if not self.schemas_dir.exists():
            print(f"Warning: Schemas directory {self.schemas_dir} does not exist")
            return
        
        for xsd_file in self.schemas_dir.glob("*.xsd"):
            schema_name = self._infer_schema_name(xsd_file.stem)
            try:
                metadata = self._parse_xsd(str(xsd_file))
                self.registry[schema_name] = metadata
                print(f"[+] Loaded schema: {schema_name} from {xsd_file.name}")
            except Exception as e:
                print(f"[-] Failed to load {xsd_file.name}: {e}")
    
    def _infer_schema_name(self, filename: str) -> str:
        """
        Infer schema name from filename.
        e.g., "patient-registration" -> "PATIENT", "medical-billing" -> "BILLING"
        """
        mapping = {
            "patient": "PATIENT",
            "billing": "BILLING",
            "encounter": "ENCOUNTER",
            "medical": "BILLING",
        }
        
        for key, schema_name in mapping.items():
            if key in filename.lower():
                return schema_name
        
        return filename.upper()
    
    def _parse_xsd(self, xsd_path: str) -> Dict:
        """
        Parse XSD file and extract metadata.
        Returns dict with: namespace, root_elements, required_children
        """
        tree = etree.parse(xsd_path)
        root = tree.getroot()
        
        # XSD namespace
        xs_ns = {"xs": "http://www.w3.org/2001/XMLSchema"}
        
        # Extract target namespace
        target_namespace = root.get("targetNamespace")
        
        # Find root element(s) - look for xs:element with type or global elements
        root_elements = []
        required_children = set()
        
        # Strategy 1: Find top-level elements (those without parent complexType)
        for elem in root.findall(".//xs:element[@name]", xs_ns):
            # Check if this element is at the root level (not nested in a complexType)
            parent = elem.getparent()
            if parent.tag == root.tag:  # Direct child of schema = root element candidate
                elem_name = elem.get("name")
                if target_namespace:
                    root_elements.append(f"{{{target_namespace}}}{elem_name}")
                else:
                    root_elements.append(elem_name)
        
        # Strategy 2: Find required children from the root type definition
        # Get the type of the first (main) element
        if root_elements:
            # Extract local name from the first root element
            root_type_name = root_elements[0].split("}")[-1] + "Type"
            
            # Find the complexType with this name
            for ctype in root.findall(".//xs:complexType[@name]", xs_ns):
                if ctype.get("name") == root_type_name:
                    # Extract element names from sequence
                    for seq_elem in ctype.findall(".//xs:sequence/xs:element[@name]", xs_ns):
                        min_occurs = seq_elem.get("minOccurs")
                        # Consider required if minOccurs is 0 or absent (defaults to 1)
                        if not min_occurs or min_occurs != "0":
                            required_children.add(seq_elem.get("name"))
        
        # Strategy 3: If no required children found, extract from complexType with "Type" suffix
        if not required_children:
            for ctype in root.findall(".//xs:complexType[@name]", xs_ns):
                ctype_name = ctype.get("name")
                if ctype_name.endswith("Type") and len(required_children) == 0:
                    for seq_elem in ctype.findall(".//xs:sequence/xs:element[@name]", xs_ns):
                        required_children.add(seq_elem.get("name"))
                    if required_children:
                        break
        
        return {
            "namespace": target_namespace,
            "root_elements": root_elements,
            "required_children": list(required_children),
            "xsd_path": xsd_path,
        }
    
    def get_schema_metadata(self, schema_type: str) -> Optional[Dict]:
        """Get metadata for a specific schema type."""
        return self.registry.get(schema_type)
    
    def list_schemas(self) -> List[str]:
        """List all registered schema types."""
        return list(self.registry.keys())
    
    def validate_against_xsd(self, xml_content: bytes, schema_type: str) -> Tuple[bool, str]:
        """
        Validate XML against the actual XSD file.
        Returns (is_valid, reason)
        """
        metadata = self.get_schema_metadata(schema_type)
        if not metadata:
            return False, f"Schema type '{schema_type}' not found in registry"
        
        xsd_path = metadata["xsd_path"]
        if not os.path.exists(xsd_path):
            return False, f"XSD file not found: {xsd_path}"
        
        try:
            xsd_tree = etree.parse(xsd_path)
            schema = etree.XMLSchema(xsd_tree)
            xml_tree = etree.fromstring(xml_content)
            
            is_valid = schema.validate(xml_tree)
            if not is_valid:
                return False, f"XSD validation failed: {schema.error_log[0]}"
            return True, "Valid against XSD"
        except Exception as e:
            return False, f"Validation error: {str(e)}"


# Global registry instance
_registry: Optional[SchemaRegistry] = None


def get_registry() -> SchemaRegistry:
    """Get or create the global schema registry."""
    global _registry
    if _registry is None:
        _registry = SchemaRegistry()
    return _registry
