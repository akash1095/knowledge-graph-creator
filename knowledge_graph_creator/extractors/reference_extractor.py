from typing import Dict

from knowledge_graph_creator.extractors.base import TextExtractor


class ReferenceExtractor(TextExtractor):
    def __init__(self, pattern: str):
        self.pattern = pattern

    def extract(self, text: str) -> Dict[int, str]:
        import re

        matches = re.findall(self.pattern, text, re.DOTALL)
        return {int(num): content.strip() for num, content in matches}
