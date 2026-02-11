"""Tests for dynamic expert generator module."""

import pytest

from react_agent.agents.expert_panel.config import ExpertConfig, ExpertRole
from react_agent.weekly_pipeline.expert_meeting import NewExpertProposal
from react_agent.weekly_pipeline.expert_generator import (
    DynamicExpertRole,
    ExpertGenerator,
    clear_dynamic_experts,
    get_dynamic_expert,
    get_dynamic_experts,
    register_dynamic_expert,
)


class TestDynamicExpertRole:
    """Test DynamicExpertRole dataclass."""

    def test_dynamic_expert_role_creation(self):
        """Test creating DynamicExpertRole with value."""
        role = DynamicExpertRole(value="hydrogen_expert")

        assert role.value == "hydrogen_expert"

    def test_dynamic_expert_role_str(self):
        """Test __str__ method returns value."""
        role = DynamicExpertRole(value="battery_expert")

        assert str(role) == "battery_expert"

    def test_dynamic_expert_role_hash(self):
        """Test __hash__ method allows use in sets/dicts."""
        role1 = DynamicExpertRole(value="hydrogen_expert")
        role2 = DynamicExpertRole(value="hydrogen_expert")
        role3 = DynamicExpertRole(value="battery_expert")

        # Same value should have same hash
        assert hash(role1) == hash(role2)

        # Can be used in a set
        role_set = {role1, role2, role3}
        assert len(role_set) == 2

    def test_dynamic_expert_role_eq(self):
        """Test __eq__ method for equality comparison."""
        role1 = DynamicExpertRole(value="hydrogen_expert")
        role2 = DynamicExpertRole(value="hydrogen_expert")
        role3 = DynamicExpertRole(value="battery_expert")

        assert role1 == role2
        assert role1 != role3


class TestExpertGenerator:
    """Test ExpertGenerator class."""

    def test_persona_template_exists(self):
        """Test that PERSONA_TEMPLATE class attribute exists."""
        assert hasattr(ExpertGenerator, "PERSONA_TEMPLATE")
        assert isinstance(ExpertGenerator.PERSONA_TEMPLATE, str)
        assert len(ExpertGenerator.PERSONA_TEMPLATE) > 0

    def test_default_tools_exists(self):
        """Test that DEFAULT_TOOLS class attribute exists."""
        assert hasattr(ExpertGenerator, "DEFAULT_TOOLS")
        assert ExpertGenerator.DEFAULT_TOOLS == ["tavily_search", "web_browser"]

    def test_generate_from_proposal_returns_expert_config(self):
        """Test generate_from_proposal returns ExpertConfig."""
        generator = ExpertGenerator()

        proposal = NewExpertProposal(
            suggested_role="hydrogen_expert",
            suggested_name="Dr. 수소",
            expertise=["그린수소 생산", "수소연료전지", "수소 저장기술"],
            keywords=["수소", "hydrogen", "연료전지", "fuel cell"],
            reason="수소 경제 관련 콘텐츠 증가",
        )

        config = generator.generate_from_proposal(proposal)

        assert config is not None
        assert isinstance(config, ExpertConfig)
        assert config.name == "Dr. 수소"
        assert "그린수소 생산" in config.expertise
        assert "수소" in config.keywords
        assert config.tools == ["tavily_search", "web_browser"]

    def test_generate_from_proposal_creates_persona(self):
        """Test that generated ExpertConfig has proper persona."""
        generator = ExpertGenerator()

        proposal = NewExpertProposal(
            suggested_role="esg_expert",
            suggested_name="Dr. ESG",
            expertise=["ESG 공시", "지속가능경영", "사회적책임"],
            keywords=["ESG", "공시", "지속가능"],
            reason="ESG 관련 콘텐츠 증가",
        )

        config = generator.generate_from_proposal(proposal)

        assert config is not None
        assert len(config.persona) > 0
        # Persona should mention expertise areas
        assert "ESG" in config.persona or "전문가" in config.persona

    def test_generate_from_proposal_empty_expertise(self):
        """Test generate_from_proposal with empty expertise returns None."""
        generator = ExpertGenerator()

        proposal = NewExpertProposal(
            suggested_role="unknown_expert",
            suggested_name="Dr. Unknown",
            expertise=[],  # Empty expertise
            keywords=[],
            reason="No specific reason",
        )

        config = generator.generate_from_proposal(proposal)

        assert config is None


class TestInferDomain:
    """Test _infer_domain method."""

    def test_infer_domain_trade(self):
        """Test domain inference for trade-related expertise."""
        generator = ExpertGenerator()

        expertise = ["통상 정책", "무역 협정", "수출입 규제"]
        domain = generator._infer_domain(expertise)

        assert domain == "통상"

    def test_infer_domain_finance(self):
        """Test domain inference for finance-related expertise."""
        generator = ExpertGenerator()

        expertise = ["금융 상품", "투자 전략", "자본시장"]
        domain = generator._infer_domain(expertise)

        assert domain == "금융"

    def test_infer_domain_energy(self):
        """Test domain inference for energy-related expertise."""
        generator = ExpertGenerator()

        expertise = ["에너지 전환", "재생에너지", "전력 시장"]
        domain = generator._infer_domain(expertise)

        assert domain == "에너지"

    def test_infer_domain_industry(self):
        """Test domain inference for industry-related expertise."""
        generator = ExpertGenerator()

        expertise = ["산업 혁신", "제조업", "산업 정책"]
        domain = generator._infer_domain(expertise)

        assert domain == "산업"

    def test_infer_domain_agriculture(self):
        """Test domain inference for agriculture-related expertise."""
        generator = ExpertGenerator()

        expertise = ["농업 기술", "농산물 시장", "식량 안보"]
        domain = generator._infer_domain(expertise)

        assert domain == "농업"

    def test_infer_domain_shipping(self):
        """Test domain inference for shipping-related expertise."""
        generator = ExpertGenerator()

        expertise = ["해운 물류", "선박 연료", "항만 시설"]
        domain = generator._infer_domain(expertise)

        assert domain == "해운"

    def test_infer_domain_default(self):
        """Test domain inference returns default for unknown domains."""
        generator = ExpertGenerator()

        expertise = ["기타 분야", "특수 영역"]
        domain = generator._infer_domain(expertise)

        # Should return a default domain (탄소 or similar)
        assert domain is not None
        assert len(domain) > 0


class TestModuleFunctions:
    """Test module-level functions for dynamic expert management."""

    def setup_method(self):
        """Clear dynamic experts before each test."""
        clear_dynamic_experts()

    def teardown_method(self):
        """Clear dynamic experts after each test."""
        clear_dynamic_experts()

    def test_register_dynamic_expert_success(self):
        """Test registering a dynamic expert successfully."""
        proposal = NewExpertProposal(
            suggested_role="hydrogen_expert",
            suggested_name="Dr. 수소",
            expertise=["그린수소", "블루수소"],
            keywords=["수소", "hydrogen"],
            reason="수소 전문가 필요",
        )

        result = register_dynamic_expert(proposal)

        assert result is True

    def test_register_dynamic_expert_empty_expertise(self):
        """Test registering expert with empty expertise fails."""
        proposal = NewExpertProposal(
            suggested_role="empty_expert",
            suggested_name="Dr. Empty",
            expertise=[],
            keywords=[],
            reason="No expertise",
        )

        result = register_dynamic_expert(proposal)

        assert result is False

    def test_get_dynamic_experts_returns_list(self):
        """Test get_dynamic_experts returns list of ExpertConfig."""
        proposal1 = NewExpertProposal(
            suggested_role="hydrogen_expert",
            suggested_name="Dr. 수소",
            expertise=["그린수소"],
            keywords=["수소"],
            reason="수소 전문가 필요",
        )
        proposal2 = NewExpertProposal(
            suggested_role="esg_expert",
            suggested_name="Dr. ESG",
            expertise=["ESG 공시"],
            keywords=["ESG"],
            reason="ESG 전문가 필요",
        )

        register_dynamic_expert(proposal1)
        register_dynamic_expert(proposal2)

        experts = get_dynamic_experts()

        assert isinstance(experts, list)
        assert len(experts) == 2
        assert all(isinstance(e, ExpertConfig) for e in experts)

    def test_get_dynamic_expert_by_role(self):
        """Test get_dynamic_expert returns specific expert by role."""
        proposal = NewExpertProposal(
            suggested_role="hydrogen_expert",
            suggested_name="Dr. 수소",
            expertise=["그린수소", "블루수소"],
            keywords=["수소", "hydrogen"],
            reason="수소 전문가 필요",
        )

        register_dynamic_expert(proposal)

        expert = get_dynamic_expert("hydrogen_expert")

        assert expert is not None
        assert isinstance(expert, ExpertConfig)
        assert expert.name == "Dr. 수소"

    def test_get_dynamic_expert_not_found(self):
        """Test get_dynamic_expert returns None for unknown role."""
        expert = get_dynamic_expert("nonexistent_expert")

        assert expert is None

    def test_clear_dynamic_experts(self):
        """Test clear_dynamic_experts removes all dynamic experts."""
        proposal = NewExpertProposal(
            suggested_role="hydrogen_expert",
            suggested_name="Dr. 수소",
            expertise=["그린수소"],
            keywords=["수소"],
            reason="수소 전문가 필요",
        )

        register_dynamic_expert(proposal)
        assert len(get_dynamic_experts()) == 1

        clear_dynamic_experts()

        assert len(get_dynamic_experts()) == 0

    def test_register_duplicate_role_overwrites(self):
        """Test registering same role overwrites existing expert."""
        proposal1 = NewExpertProposal(
            suggested_role="hydrogen_expert",
            suggested_name="Dr. 수소 V1",
            expertise=["그린수소"],
            keywords=["수소"],
            reason="Version 1",
        )
        proposal2 = NewExpertProposal(
            suggested_role="hydrogen_expert",
            suggested_name="Dr. 수소 V2",
            expertise=["블루수소"],
            keywords=["hydrogen"],
            reason="Version 2",
        )

        register_dynamic_expert(proposal1)
        register_dynamic_expert(proposal2)

        experts = get_dynamic_experts()
        assert len(experts) == 1

        expert = get_dynamic_expert("hydrogen_expert")
        assert expert is not None
        assert expert.name == "Dr. 수소 V2"
