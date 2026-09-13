"""Citation package: Provenance, verbatim quoting, and footnote formatting."""

from app.services.citation.citation_formatter import CitationFormatter
from app.services.citation.citation_grounder import CitationGrounder
from app.services.citation.citation_service import CitationService
from app.services.citation.schemas import (
    CitationItem,
    CitationStance,
    CitationSummary,
    FormattedCitationEntry,
)

__all__ = [
    "CitationService",
    "CitationGrounder",
    "CitationFormatter",
    "CitationItem",
    "CitationStance",
    "FormattedCitationEntry",
    "CitationSummary",
]
