from abc import ABC, abstractmethod
from typing import Dict


class TextExtractor(ABC):
    @abstractmethod
    def extract(self, text: str) -> Dict[int, str]:
        pass
