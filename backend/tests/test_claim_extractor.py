"""Tests for ClaimExtractor, RuleBasedClaimExtractor, LLMClaimExtractor, and schema validation."""

import pytest
from app.core.exceptions import LLMProviderException
from app.services.generation.base import BaseLLMProvider
from app.services.generation.llm_provider import MockLLMProvider
from app.services.verification import (
    BaseClaimExtractor,
    ClaimExtractor,
    ClaimItem,
    ClaimExtractionOutput,
    ClaimExtractionResponse,
    LLMClaimExtractor,
    RuleBasedClaimExtractor,
)


# ---------------------------------------------------------------------------
# Unit Tests for RuleBasedClaimExtractor
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_rule_based_single_sentence():
    """Verify single sentence returns single corresponding claim."""
    extractor = RuleBasedClaimExtractor()
    text = "Tăng trưởng GDP của Việt Nam năm 2023 đạt 5.05%."
    claims = await extractor.extract_claims(text)

    assert len(claims) == 1
    assert claims[0].claim_id == "claim_1"
    assert claims[0].order == 1
    assert "Tăng trưởng GDP của Việt Nam năm 2023 đạt 5.05%" in claims[0].text


@pytest.mark.asyncio
async def test_rule_based_multiple_sentences():
    """Verify multiple sentences are cleanly segmented into distinct claims in order."""
    extractor = RuleBasedClaimExtractor()
    text = "Việt Nam có 63 tỉnh thành. Thủ đô là Hà Nội. Thành phố lớn nhất là TP.HCM."
    claims = await extractor.extract_claims(text)

    assert len(claims) == 3
    assert [c.order for c in claims] == [1, 2, 3]
    assert [c.claim_id for c in claims] == ["claim_1", "claim_2", "claim_3"]
    assert "Việt Nam có 63 tỉnh thành" in claims[0].text
    assert "Thủ đô là Hà Nội" in claims[1].text
    assert "Thành phố lớn nhất là TP.HCM" in claims[2].text


@pytest.mark.asyncio
async def test_rule_based_compound_conjunction_splitting():
    """Verify compound clauses connected by conjunctions (e.g. 'và') are split into atomic claims."""
    extractor = RuleBasedClaimExtractor()
    # Prompt requirement example:
    text = "SIC đào tạo AI và IoT. Chương trình kéo dài 6 tháng."
    claims = await extractor.extract_claims(text)

    assert len(claims) == 3
    assert [c.order for c in claims] == [1, 2, 3]
    # Clause 1
    assert "SIC đào tạo AI" in claims[0].text
    # Clause 2 (expanded predicate)
    assert "SIC đào tạo IoT" in claims[1].text
    # Clause 3
    assert "Chương trình kéo dài 6 tháng" in claims[2].text


@pytest.mark.asyncio
async def test_rule_based_empty_and_whitespace_input():
    """Verify empty or whitespace strings return empty list safely."""
    extractor = RuleBasedClaimExtractor()
    assert await extractor.extract_claims("") == []
    assert await extractor.extract_claims("    ") == []
    assert await extractor.extract_claims("   \n\t  ") == []


@pytest.mark.asyncio
async def test_rule_based_preserves_content_fidelity():
    """Verify extractor does not alter the underlying factual text."""
    extractor = RuleBasedClaimExtractor()
    text = "Xuất khẩu thủy sản năm 2023 đạt xấp xỉ 9 tỷ USD."
    claims = await extractor.extract_claims(text)

    assert len(claims) == 1
    assert "Xuất khẩu thủy sản năm 2023 đạt xấp xỉ 9 tỷ USD." == claims[0].text


# ---------------------------------------------------------------------------
# Unit Tests for LLMClaimExtractor & Fallbacks
# ---------------------------------------------------------------------------

class MockSuccessfulLLMProvider(BaseLLMProvider):
    async def generate_text(self, prompt, **kwargs):
        return ""

    async def generate_structured(self, prompt, schema, **kwargs):
        return schema(
            claims=[
                ClaimItem(claim_id="claim_1", text="Lạm phát năm 2023 ở mức 3.25%.", order=1),
                ClaimItem(claim_id="claim_2", text="Mục tiêu lạm phát năm 2024 dưới 4.5%.", order=2),
            ]
        )


class MockFailingLLMProvider(BaseLLMProvider):
    async def generate_text(self, prompt, **kwargs):
        return ""

    async def generate_structured(self, prompt, schema, **kwargs):
        raise LLMProviderException(provider="Mock", message="API connection timed out")


@pytest.mark.asyncio
async def test_llm_claim_extractor_success():
    """Verify LLMClaimExtractor parses structured output correctly with enforce order."""
    extractor = LLMClaimExtractor(provider=MockSuccessfulLLMProvider())
    text = "Lạm phát năm 2023 ở mức 3.25%. Mục tiêu lạm phát năm 2024 dưới 4.5%."
    claims = await extractor.extract_claims(text)

    assert len(claims) == 2
    assert claims[0].order == 1
    assert claims[1].order == 2
    assert claims[0].claim_id == "claim_1"
    assert claims[1].claim_id == "claim_2"
    assert "3.25%" in claims[0].text
    assert "4.5%" in claims[1].text


@pytest.mark.asyncio
async def test_llm_claim_extractor_fallback_on_provider_error():
    """Verify that when LLM provider throws error, it falls back to RuleBasedClaimExtractor gracefully."""
    extractor = LLMClaimExtractor(provider=MockFailingLLMProvider())
    text = "Tăng trưởng kinh tế quý 4 đạt 6.72%. Khu vực dịch vụ phục hồi tốt."
    claims = await extractor.extract_claims(text)

    # Must not raise exception, but return claims extracted via rule-based fallback
    assert len(claims) == 2
    assert claims[0].order == 1
    assert claims[1].order == 2
    assert "Tăng trưởng kinh tế quý 4 đạt 6.72%" in claims[0].text


# ---------------------------------------------------------------------------
# Unit Tests for ClaimExtractor Facade
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_claim_extractor_facade_extract_response():
    """Verify ClaimExtractor.extract returns full ClaimExtractionResponse payload."""
    facade = ClaimExtractor(mode="rule_based")
    text = "SIC đào tạo AI và IoT."
    resp = await facade.extract(answer=text)

    assert isinstance(resp, ClaimExtractionResponse)
    assert resp.answer == text
    assert resp.total_claims == 2
    assert len(resp.claims) == 2
    assert resp.claims[0].claim_id == "claim_1"
    assert resp.claims[1].claim_id == "claim_2"


@pytest.mark.asyncio
async def test_claim_extractor_facade_empty_answer():
    """Verify ClaimExtractor.extract handles empty input cleanly."""
    facade = ClaimExtractor()
    resp = await facade.extract(answer="")

    assert resp.total_claims == 0
    assert resp.claims == []


@pytest.mark.asyncio
async def test_claim_extractor_backward_compatible_extract_claims():
    """Verify backward compatibility helper extract_claims returning legacy ExtractedClaim."""
    facade = ClaimExtractor(mode="rule_based")
    text = "Hà Nội là thủ đô của Việt Nam."
    legacy_claims = await facade.extract_claims(text)

    assert len(legacy_claims) == 1
    assert legacy_claims[0].claim_id == "claim_1"
    assert "Hà Nội là thủ đô" in legacy_claims[0].claim_text
    assert legacy_claims[0].verifiable is True
