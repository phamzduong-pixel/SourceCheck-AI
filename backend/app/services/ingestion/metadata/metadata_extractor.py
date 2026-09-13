"""Document metadata extractor."""

from datetime import datetime, timezone
import hashlib
import os
from typing import Any, Dict, Optional
from app.services.ingestion.parsers.base import ParsedDocument


class MetadataExtractor:
    """Extracts standardized metadata from parsed documents and raw content."""

    @classmethod
    def extract(
        cls,
        parsed_doc: ParsedDocument,
        raw_content: bytes,
        custom_metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Extract and assemble comprehensive document metadata.
        
        Args:
            parsed_doc: The parsed document instance.
            raw_content: Raw byte content for hash and size calculation.
            custom_metadata: Optional additional metadata provided by the caller.
            
        Returns:
            Dictionary containing unified document metadata.
        """
        sha256_hash = hashlib.sha256(raw_content).hexdigest()
        file_size = len(raw_content)
        word_count = len(parsed_doc.full_text.split()) if parsed_doc.full_text else 0
        char_count = len(parsed_doc.full_text)
        page_count = len(parsed_doc.pages) if parsed_doc.pages else 1

        # Base metadata
        metadata: Dict[str, Any] = {
            "filename": parsed_doc.filename,
            "file_type": parsed_doc.file_type,
            "file_size_bytes": file_size,
            "sha256": sha256_hash,
            "page_count": page_count,
            "char_count": char_count,
            "word_count": word_count,
            "ingested_at": datetime.now(timezone.utc).isoformat(),
        }

        # Merge parser-extracted metadata (e.g. PDF author, DOCX title)
        if parsed_doc.metadata:
            for k, v in parsed_doc.metadata.items():
                if v is not None and k not in metadata:
                    metadata[k] = v

        # Default title if not present
        if "title" not in metadata or not metadata["title"]:
            base_name, _ = os.path.splitext(parsed_doc.filename)
            metadata["title"] = base_name

        # Merge caller custom metadata
        if custom_metadata:
            metadata.update(custom_metadata)

        return metadata
