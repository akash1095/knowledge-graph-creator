import re
from dataclasses import asdict, dataclass
from loguru import logger


@dataclass
class ReferenceDetails:
    id_: int
    authors: str
    year: str
    title: str
    publish: str
    page_or_volume: str = ""

    def __post_init__(self):
        if not self.authors or not self.year or not self.title:
            raise ValueError("Authors, year, and title are required fields.")
        if not self.year.isdigit():
            raise ValueError("Year must be a numeric value.")

    def to_dict(self):
        """Convert the dataclass to a dictionary."""
        return asdict(self)

    def __str__(self):
        """Readable string representation."""
        return (
            f"ReferenceDetails(id_={self.id_}, authors='{self.authors}', "
            f"year='{self.year}', title='{self.title}', publish='{self.publish}', "
            f"page_or_volume='{self.page_or_volume}')"
        )


class ReferenceDetailsExtractor:

    @staticmethod
    def parse_with_regex(ref_id: int, ref_text: str) -> ReferenceDetails | None:

        pattern = r"^(?P<authors>.+?).\s*(?P<year>\d{4})\.\s*(?P<title>.+?)\.\s*(?P<publish>[^,.]+)(?:[.,]*\s*(?P<page_or_volume>.*))?$"
        match = re.match(pattern, ref_text.strip(), re.DOTALL)
        if not match:
            logger.error(f"Error parsing reference {ref_id} - '{ref_text}': {match}")
            return None
            raise ValueError(f"Reference {ref_id} does not match the expected format.")

        authors = match.group("authors").strip()
        year = match.group("year").strip()
        title = match.group("title").strip().replace("\n", " ")
        publish = match.group("publish").replace("\n", " ").strip()
        page_or_volume = match.group("page_or_volume") or ""

        return ReferenceDetails(
            id_=ref_id,
            authors=authors,
            title=title,
            publish=publish,
            year=year,
            page_or_volume=page_or_volume.strip(),
        )

    @staticmethod
    def parse(ref_id: int, ref_text: str) -> ReferenceDetails:
        try:
            parts = ref_text.split(".", maxsplit=4)
            authors = parts[0]
            year = parts[1].strip()
            title = parts[2]
            publish = parts[3].replace("\n", " ").strip()
            page_or_volume = (
                parts[3].split(",")[-1].strip() if len(parts[3].split(",")) > 1 else ""
            )
            if page_or_volume and page_or_volume in publish:
                publish = publish.replace(page_or_volume, "").rstrip(", ").strip()
            return ReferenceDetails(
                id_=ref_id,
                authors=authors,
                title=title,
                publish=publish,
                year=year,
                page_or_volume=page_or_volume,
            )
        except (IndexError, ValueError) as e:
            raise ValueError(f"Error parsing reference {ref_id} - '{ref_text}': {e}")
