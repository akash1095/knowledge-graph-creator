from knowledge_graph_creator.doc_extractor.pdf_extractor import PyMuPDFReader
from knowledge_graph_creator.extractors.reference_extractor import ReferenceExtractor
from knowledge_graph_creator.patterns import ReferencePattern


class PDFReferenceOrchestrator:
    def __init__(self, reader, extractor):
        self.reader = reader
        self.extractor = extractor

    def process(self, path: str):
        text = self.reader.read(path)
        references_ = self.extractor.extract(text)
        return references_


# Usage
reader = PyMuPDFReader()
extractor = ReferenceExtractor(ReferencePattern.BRACKETED_NUMBER)
orchestrator = PDFReferenceOrchestrator(reader, extractor)
references = orchestrator.process("data/3643806.pdf")
