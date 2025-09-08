from typing import List

import pymupdf

from knowledge_graph_creator.doc_extractor.base import PDFReader


class PyMuPDFReader(PDFReader):

    def read(self, path: str) -> str:
        """
        Extract text from a PDF file and return it as a single string.
        :param path:
        :return: Extracted text as a single string.
        """

        doc = pymupdf.open(path)
        return "\n".join(page.get_text() for page in doc)

    def to_list(self, path: str, select_pages: List[int]) -> List[str]:
        """
        Extract text from a PDF file and return it as a list of strings, each representing a page.
        :param path:
        :param select_pages: List of page numbers to extract. If None, all pages are extracted.
        :return: List of strings, each string is the text of a page.
        """

        doc = pymupdf.open(path)
        if select_pages:
            if isinstance(select_pages, int):
                select_pages = [select_pages]
            doc.select(select_pages)
        return [page.get_text() for page in doc]
