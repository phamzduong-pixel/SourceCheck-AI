"""Custom application exception definitions."""

from typing import Any, Dict, Optional


class SourceCheckException(Exception):
    """Base class for all SourceCheck AI domain exceptions."""

    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_ERROR",
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(self.message)


class EntityNotFoundException(SourceCheckException):
    """Raised when a requested resource is not found."""

    def __init__(self, entity_name: str, entity_id: Any):
        super().__init__(
            message=f"{entity_name} with id '{entity_id}' not found.",
            code="ENTITY_NOT_FOUND",
            details={"entity_name": entity_name, "entity_id": str(entity_id)},
        )


class ValidationException(SourceCheckException):
    """Raised when input validation fails in services."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            details=details,
        )


class RetrievalException(SourceCheckException):
    """Raised when knowledge retrieval or search fails."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="RETRIEVAL_ERROR",
            details=details,
        )


class LLMProviderException(SourceCheckException):
    """Raised when calls to LLM provider fail or timeout."""

    def __init__(self, provider: str, message: str):
        super().__init__(
            message=f"LLM provider '{provider}' error: {message}",
            code="LLM_PROVIDER_ERROR",
            details={"provider": provider, "error": message},
        )


class VerificationException(SourceCheckException):
    """Raised when verification pipeline encounters an unrecoverable failure."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="VERIFICATION_ERROR",
            details=details,
        )


class UnsupportedFileTypeException(SourceCheckException):
    """Raised when an uploaded file type is not supported."""

    def __init__(self, extension: str, supported: list):
        super().__init__(
            message=f"File type '{extension}' is not supported. Supported types: {', '.join(supported)}",
            code="UNSUPPORTED_FILE_TYPE",
            details={"extension": extension, "supported": supported},
        )


class EmptyDocumentException(SourceCheckException):
    """Raised when a document contains no readable text."""

    def __init__(self, filename: str):
        super().__init__(
            message=f"Document '{filename}' contains no readable text content.",
            code="EMPTY_DOCUMENT",
            details={"filename": filename},
        )


class DocumentParsingException(SourceCheckException):
    """Raised when parsing fails for a document."""

    def __init__(self, filename: str, reason: str):
        super().__init__(
            message=f"Failed to parse document '{filename}': {reason}",
            code="DOCUMENT_PARSING_ERROR",
            details={"filename": filename, "reason": reason},
        )


class FileTooLargeException(SourceCheckException):
    """Raised when an uploaded file exceeds the configured size limit."""

    def __init__(self, filename: str, file_size: int, max_size: int):
        super().__init__(
            message=f"File '{filename}' ({file_size} bytes) exceeds maximum limit of {max_size} bytes.",
            code="FILE_TOO_LARGE",
            details={"filename": filename, "file_size": file_size, "max_size": max_size},
        )


class EmbeddingProviderException(SourceCheckException):
    """Raised when an embedding provider fails to generate vectors."""

    def __init__(self, provider: str, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"Embedding provider '{provider}' error: {message}",
            code="EMBEDDING_PROVIDER_ERROR",
            details={"provider": provider, "error": message, **(details or {})},
        )


class VectorSearchException(SourceCheckException):
    """Raised when vector similarity search encounters an error."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"Vector search failed: {message}",
            code="VECTOR_SEARCH_ERROR",
            details=details,
        )


