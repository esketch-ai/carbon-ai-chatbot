"""Tests for LLM expert meeting engine module."""

import pytest

from react_agent.agents.expert_panel.config import ExpertRole
from react_agent.weekly_pipeline.expert_meeting import (
    ExpertMeeting,
    MeetingResult,
    NewExpertProposal,
)


class TestNewExpertProposal:
    """Test NewExpertProposal dataclass."""

    def test_new_expert_proposal_structure(self):
        """Test creating NewExpertProposal with all fields."""
        proposal = NewExpertProposal(
            suggested_role="hydrogen_expert",
            suggested_name="Dr. 수소",
            expertise=["그린수소", "블루수소", "수소연료전지"],
            keywords=["수소", "hydrogen", "연료전지", "fuel cell"],
            reason="수소 경제 관련 콘텐츠가 증가하여 전문가 필요",
        )

        assert proposal.suggested_role == "hydrogen_expert"
        assert proposal.suggested_name == "Dr. 수소"
        assert len(proposal.expertise) == 3
        assert "그린수소" in proposal.expertise
        assert len(proposal.keywords) == 4
        assert "수소" in proposal.keywords
        assert "전문가 필요" in proposal.reason


class TestMeetingResult:
    """Test MeetingResult dataclass."""

    def test_meeting_result_structure(self):
        """Test creating MeetingResult with required fields."""
        result = MeetingResult(
            assigned_experts=[ExpertRole.POLICY_EXPERT, ExpertRole.MARKET_EXPERT],
            new_expert_proposals=[],
            reasoning="정책과 시장 분석이 모두 필요한 복합 콘텐츠입니다.",
            consensus_score=0.85,
        )

        assert len(result.assigned_experts) == 2
        assert ExpertRole.POLICY_EXPERT in result.assigned_experts
        assert ExpertRole.MARKET_EXPERT in result.assigned_experts
        assert result.new_expert_proposals == []
        assert "복합 콘텐츠" in result.reasoning
        assert result.consensus_score == 0.85
        assert result.raw_response == ""

    def test_meeting_result_with_new_expert_proposals(self):
        """Test creating MeetingResult with new expert proposals."""
        proposal = NewExpertProposal(
            suggested_role="esg_expert",
            suggested_name="Dr. ESG",
            expertise=["ESG 공시", "지속가능경영"],
            keywords=["ESG", "공시", "지속가능"],
            reason="ESG 관련 콘텐츠 증가",
        )

        result = MeetingResult(
            assigned_experts=[ExpertRole.POLICY_EXPERT],
            new_expert_proposals=[proposal],
            reasoning="현재는 정책 전문가가 담당하되, ESG 전문가 신설 제안",
            consensus_score=0.7,
            raw_response='{"assigned_experts": ["policy_expert"]}',
        )

        assert len(result.assigned_experts) == 1
        assert len(result.new_expert_proposals) == 1
        assert result.new_expert_proposals[0].suggested_role == "esg_expert"
        assert result.raw_response != ""


class TestExpertMeeting:
    """Test ExpertMeeting class."""

    def test_expert_meeting_init(self):
        """Test ExpertMeeting initialization."""
        meeting = ExpertMeeting()

        assert meeting.model_name == "claude-sonnet-4-20250514"
        assert meeting.llm is not None

    def test_expert_meeting_init_custom_model(self):
        """Test ExpertMeeting initialization with custom model."""
        meeting = ExpertMeeting(model="claude-3-haiku-20240307")

        assert meeting.model_name == "claude-3-haiku-20240307"

    def test_get_expert_list(self):
        """Test _get_expert_list method returns formatted expert list."""
        meeting = ExpertMeeting()
        expert_list = meeting._get_expert_list()

        # Should contain all 5 experts
        assert "policy_expert" in expert_list
        assert "carbon_credit_expert" in expert_list
        assert "market_expert" in expert_list
        assert "technology_expert" in expert_list
        assert "mrv_expert" in expert_list

        # Should contain expert names
        assert "Dr." in expert_list

    def test_parse_response_valid_json(self):
        """Test _parse_response with valid JSON response."""
        meeting = ExpertMeeting()

        valid_response = """
        {
            "assigned_experts": ["policy_expert", "market_expert"],
            "new_expert_proposals": [],
            "reasoning": "정책과 시장 분석이 필요합니다.",
            "consensus_score": 0.9
        }
        """

        result = meeting._parse_response(valid_response)

        assert isinstance(result, MeetingResult)
        assert len(result.assigned_experts) == 2
        assert ExpertRole.POLICY_EXPERT in result.assigned_experts
        assert ExpertRole.MARKET_EXPERT in result.assigned_experts
        assert result.consensus_score == 0.9
        assert result.raw_response == valid_response

    def test_parse_response_with_new_expert(self):
        """Test _parse_response with new expert proposal."""
        meeting = ExpertMeeting()

        response_with_proposal = """
        {
            "assigned_experts": ["technology_expert"],
            "new_expert_proposals": [
                {
                    "suggested_role": "battery_expert",
                    "suggested_name": "Dr. 배터리",
                    "expertise": ["리튬이온 배터리", "ESS"],
                    "keywords": ["배터리", "ESS", "에너지저장"],
                    "reason": "배터리 기술 전문성 필요"
                }
            ],
            "reasoning": "기술 전문가가 담당하되, 배터리 전문가 신설 권장",
            "consensus_score": 0.75
        }
        """

        result = meeting._parse_response(response_with_proposal)

        assert len(result.assigned_experts) == 1
        assert ExpertRole.TECHNOLOGY_EXPERT in result.assigned_experts
        assert len(result.new_expert_proposals) == 1
        assert result.new_expert_proposals[0].suggested_role == "battery_expert"
        assert result.new_expert_proposals[0].suggested_name == "Dr. 배터리"

    def test_parse_response_invalid_json(self):
        """Test _parse_response with invalid JSON falls back gracefully."""
        meeting = ExpertMeeting()

        invalid_response = "This is not valid JSON"

        result = meeting._parse_response(invalid_response)

        # Should return a default result with policy expert
        assert isinstance(result, MeetingResult)
        assert len(result.assigned_experts) >= 1
        assert result.raw_response == invalid_response

    def test_parse_response_with_markdown_code_block(self):
        """Test _parse_response with JSON wrapped in markdown code block."""
        meeting = ExpertMeeting()

        markdown_response = """
        Here is my analysis:

        ```json
        {
            "assigned_experts": ["mrv_expert"],
            "new_expert_proposals": [],
            "reasoning": "MRV 검증 전문가가 적합합니다.",
            "consensus_score": 0.88
        }
        ```
        """

        result = meeting._parse_response(markdown_response)

        assert isinstance(result, MeetingResult)
        assert ExpertRole.MRV_EXPERT in result.assigned_experts
        assert result.consensus_score == 0.88
