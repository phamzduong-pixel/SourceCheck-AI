"""LLM Provider implementations: OpenAI, Anthropic, and Mock providers."""

import json
import logging
import re
from typing import Any, Dict, List, Optional, Type, TypeVar
import httpx
from pydantic import BaseModel, ValidationError
from app.core.config import settings
from app.core.exceptions import LLMProviderException
from app.services.generation.base import BaseLLMProvider
from app.services.generation.schemas import GeneratedAnswer, GenerationStatus

logger = logging.getLogger(__name__)
SchemaType = TypeVar("SchemaType", bound=BaseModel)


def _extract_json_substring(text: str) -> str:
    """Extract a JSON object substring from raw text if surrounded by markdown code fences."""
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()

    # If still containing markdown or leading text, find first { and last }
    start_idx = text.find("{")
    end_idx = text.rfind("}")
    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
        return text[start_idx : end_idx + 1]
    return text


class OpenAILLMProvider(BaseLLMProvider):
    """OpenAI Chat Completions API provider using asynchronous httpx client."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: str = "https://api.openai.com/v1",
        timeout_seconds: float = settings.LLM_TIMEOUT_SECONDS,
    ):
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.model = model or settings.LLM_MODEL
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def _check_api_key(self) -> None:
        if not self.api_key or not self.api_key.strip():
            raise LLMProviderException(
                provider="OpenAI",
                message="OPENAI_API_KEY is not configured in environment or settings.",
            )

    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.0,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Call OpenAI chat completion endpoint returning text content."""
        self._check_api_key()
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    headers=headers,
                )

            if response.status_code != 200:
                raise LLMProviderException(
                    provider="OpenAI",
                    message=f"API returned status {response.status_code}: {response.text}",
                )

            data = response.json()
            return data["choices"][0]["message"]["content"] or ""

        except httpx.TimeoutException as e:
            raise LLMProviderException(
                provider="OpenAI",
                message=f"Request timed out after {self.timeout_seconds}s: {str(e)}",
            )
        except httpx.RequestError as e:
            raise LLMProviderException(
                provider="OpenAI",
                message=f"HTTP connection failed: {str(e)}",
            )

    async def generate_structured(
        self,
        prompt: str,
        schema: Type[SchemaType],
        system_prompt: Optional[str] = None,
        temperature: float = 0.0,
        max_tokens: Optional[int] = None,
    ) -> SchemaType:
        """Call OpenAI chat completion with JSON schema formatting and parse into Pydantic model."""
        self._check_api_key()
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        # Configure response_format for OpenAI JSON Schema
        json_schema = schema.model_json_schema()
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": schema.__name__,
                    "schema": json_schema,
                    "strict": True,
                },
            },
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    headers=headers,
                )

            if response.status_code != 200:
                # If json_schema mode is unsupported on older endpoint, fallback to json_object mode
                if "json_schema" in response.text:
                    logger.warning("json_schema format not supported by model; retrying with json_object")
                    payload["response_format"] = {"type": "json_object"}
                    async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                        response = await client.post(
                            f"{self.base_url}/chat/completions",
                            json=payload,
                            headers=headers,
                        )

            if response.status_code != 200:
                raise LLMProviderException(
                    provider="OpenAI",
                    message=f"API error ({response.status_code}): {response.text}",
                )

            data = response.json()
            raw_content = data["choices"][0]["message"]["content"] or ""
            json_str = _extract_json_substring(raw_content)

            parsed_dict = json.loads(json_str)
            return schema.model_validate(parsed_dict)

        except httpx.TimeoutException as e:
            raise LLMProviderException(
                provider="OpenAI",
                message=f"Request timed out after {self.timeout_seconds}s: {str(e)}",
            )
        except httpx.RequestError as e:
            raise LLMProviderException(
                provider="OpenAI",
                message=f"HTTP connection failed: {str(e)}",
            )
        except (json.JSONDecodeError, ValidationError) as e:
            raise LLMProviderException(
                provider="OpenAI",
                message=f"Failed to parse structured output into {schema.__name__}: {str(e)}",
            )


class MockLLMProvider(BaseLLMProvider):
    """Deterministic Mock LLM Provider for unit testing and local offline runs."""

    def __init__(self, should_fail: bool = False, failure_type: str = "error"):
        self.should_fail = should_fail
        self.failure_type = failure_type

    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.0,
        max_tokens: Optional[int] = None,
    ) -> str:
        if self.should_fail:
            if self.failure_type == "timeout":
                raise LLMProviderException("MockLLM", "Mock request timed out after 30.0s")
            raise LLMProviderException("MockLLM", "Simulated mock provider failure")

        return f"Mock response answering: {prompt[:40]}..."

    async def generate_structured(
        self,
        prompt: str,
        schema: Type[SchemaType],
        system_prompt: Optional[str] = None,
        temperature: float = 0.0,
        max_tokens: Optional[int] = None,
    ) -> SchemaType:
        if self.should_fail:
            if self.failure_type == "timeout":
                raise LLMProviderException("MockLLM", "Mock request timed out after 30.0s")
            raise LLMProviderException("MockLLM", "Simulated mock provider failure")

        # Deterministic generation for GeneratedAnswer
        if issubclass(schema, GeneratedAnswer):
            # Check if evidence is empty or missing in prompt
            if "No relevant evidence found" in prompt or "[E1]" not in prompt:
                return schema(
                    answer="Thông tin trong các tài liệu kiểm chứng hiện tại không đủ để trả lời câu hỏi này.",
                    status=GenerationStatus.INSUFFICIENT_EVIDENCE,
                    evidence_ids=[],
                )

            # Find evidence IDs mentioned in prompt (e.g. [E1], [E2])
            found_ids = re.findall(r"\[E(\d+)\]", prompt)
            evidence_ids = [f"E{num}" for num in found_ids[:2]] if found_ids else ["E1"]

            # Extract factual content from evidence block if available
            fact_match = re.search(r'Nội dung:\s*["\'](.*?)["\']', prompt)
            if fact_match:
                extracted_fact = fact_match.group(1).strip()
                answer_text = f"Dựa trên tài liệu kiểm chứng, {extracted_fact}"
            else:
                answer_text = "Dựa trên tài liệu kiểm chứng, câu hỏi đã được xác nhận với bằng chứng liên quan."

            return schema(
                answer=answer_text,
                status=GenerationStatus.SUPPORTED,
                evidence_ids=evidence_ids,
            )

        return schema.model_construct()



def get_llm_provider(
    provider_name: Optional[str] = None,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
) -> BaseLLMProvider:
    """Factory creating LLM provider based on configuration with graceful mock fallback."""
    prov = (provider_name or settings.LLM_PROVIDER).lower()
    key = api_key or settings.OPENAI_API_KEY

    if prov == "mock":
        return MockLLMProvider()

    if prov == "openai":
        if not key or not key.strip():
            logger.warning(
                "OPENAI_API_KEY is empty. Falling back to MockLLMProvider for development/testing."
            )
            return MockLLMProvider()
        return OpenAILLMProvider(api_key=key, model=model)

    logger.warning(f"Unsupported LLM provider '{prov}'. Falling back to MockLLMProvider.")
    return MockLLMProvider()
