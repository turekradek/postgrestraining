import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class ErsError(Exception):
    """Generic ERS error used to gather all of the ERS Taxonomy compliant errors."""

    def __init__(self, tag: str, message: str, detailed_message: str):
        self.tag = tag
        self.message = message
        self.detailed_message = detailed_message
        super().__init__()

    def __str__(self) -> str:
        return repr(self)

    def __repr__(self) -> str:
        return (
            f"{self.tag}: {self.message}. Detailed message: {self.detailed_message}.\n\n{self.tag}"
        )
        
class DBError(ErsError):
    """Raised when database error."""

    def __init__(self, message: str = "no detail message"):
        super().__init__(
            tag="## DBERROR ##",
            message="Database Error. Boskos will stop and manual intervention is needed",
            detailed_message=message,
        )