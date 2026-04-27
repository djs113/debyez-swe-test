from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)

class BaseParser(ABC):
    # Field length limits to prevent PDF rendering issues
    FIELD_LIMITS = {
        'name': 100,
        'text': 500,
        'address': 200,
        'phone': 50,
        'email': 100,
        'code': 50,
        'identifier': 100,
        'description': 1000,
    }

    @staticmethod
    def truncate_field(value, field_type='text', default=''):
        """Truncate field to max length with ellipsis."""
        if value is None:
            return default
        if not isinstance(value, str):
            value = str(value)

        max_len = BaseParser.FIELD_LIMITS.get(field_type, 500)
        if len(value) > max_len:
            logger.warning(f"Field truncated from {len(value)} to {max_len} chars")
            return value[:max_len-3] + '...'
        return value

    @staticmethod
    def safe_get_text(node, xpath, namespaces=None, default=None, field_type='text'):
        """Safely extract text from XML node with length validation."""
        try:
            if node is None:
                return default
            result = node.xpath(xpath, namespaces=namespaces) if namespaces else node.xpath(xpath)
            value = result[0].text if result else default
            return BaseParser.truncate_field(value, field_type, default or '')
        except Exception as e:
            logger.warning(f"Error extracting {xpath}: {e}")
            return default

    @staticmethod
    def safe_get_attr(element, attr, default=None, field_type='text'):
        """Safely extract attribute with length validation."""
        try:
            value = element.get(attr, default)
            return BaseParser.truncate_field(value, field_type, default or '')
        except Exception as e:
            logger.warning(f"Error extracting attribute {attr}: {e}")
            return default

    @staticmethod
    def safe_get_element(node, xpath, namespaces=None, required=False):
        """Safely get first element from XPath query."""
        try:
            if node is None:
                if required:
                    logger.error(f"Required element {xpath} not found - node is None")
                return None
            result = node.xpath(xpath, namespaces=namespaces) if namespaces else node.xpath(xpath)
            if not result:
                if required:
                    logger.error(f"Required element {xpath} not found")
                return None
            return result[0]
        except Exception as e:
            logger.error(f"Error getting element {xpath}: {e}")
            return None

    @staticmethod
    def log_unknown_elements(element, expected_names):
        """Log any child elements not in the expected list (defensive robustness)."""
        if element is None:
            return

        try:
            for child in element:
                # Extract local name from tag (strip namespace prefix)
                tag = child.tag
                if '}' in tag:
                    local_name = tag.split('}')[1]
                else:
                    local_name = tag

                if local_name not in expected_names:
                    logger.warning(f"Unknown/unexpected element found and skipped: <{local_name}>")
        except Exception as e:
            logger.debug(f"Error logging unknown elements: {e}")

    @abstractmethod
    def parse(self, xml_path: str):
        pass