from abc import ABC, abstractmethod
from typing import List


class PDFReader(ABC):
    @abstractmethod
    def read(self, path: str) -> str:
        pass

    @abstractmethod
    def to_list(self, path: str, select_pages: List[int]) -> List[str]:
        pass
