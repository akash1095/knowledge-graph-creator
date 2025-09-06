from enum import Enum


class ReferencePattern(str, Enum):
    BRACKETED_NUMBER = r"\[(\d+)\](.*?)(?=\[\d+\]|$)"
    NUMBERED_LIST = r"(\d+)\.(.*?)(?=\d+\.|$)"
