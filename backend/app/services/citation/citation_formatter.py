"""Citation formatter for bibliographic entries, footnotes, and inline references."""

from typing import List
from app.services.citation.schemas import CitationItem, FormattedCitationEntry


class CitationFormatter:
    """Formats citation collections into clean human-readable and markdown text blocks."""

    def format_entry(self, citation: CitationItem) -> str:
        """Format a single citation item into standard bibliographic text:
        e.g. [1] Source Name — Document Title (https://...)
        """
        source_display = citation.source_name or "Tài liệu kiểm chứng"
        url_part = f" ({citation.source_url})" if citation.source_url else ""
        return f"[{citation.footnote_index}] {source_display}{url_part}"

    def format_footnotes_section(
        self,
        citations: List[CitationItem],
        header: str = "### Tài liệu tham khảo:",
    ) -> str:
        """Format a distinct list of footnote citations into a markdown section."""
        if not citations:
            return ""

        # Deduplicate citations by footnote_index
        seen_indices = set()
        entries: List[str] = []

        # Sort by footnote index
        sorted_citations = sorted(citations, key=lambda c: c.footnote_index)

        for c in sorted_citations:
            if c.footnote_index not in seen_indices:
                seen_indices.add(c.footnote_index)
                entries.append(self.format_entry(c))

        return f"\n\n{header}\n" + "\n".join(entries)

    def format_inline_tags(self, indices: List[int]) -> str:
        """Format multiple footnote indices into bracketed tags: e.g. [1, 2]."""
        if not indices:
            return ""
        sorted_unique = sorted(set(indices))
        return "[" + ", ".join(str(idx) for idx in sorted_unique) + "]"
