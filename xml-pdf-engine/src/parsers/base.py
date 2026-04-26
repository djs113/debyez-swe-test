from abc import ABC, abstractmethod

class BaseParser(ABC):
    @abstractmethod
    def parse(self, xml_path: str):
        pass