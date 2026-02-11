"""Weekly report generator module.

This module provides functionality for generating weekly briefing reports
from expert analysis results in markdown format.
"""

import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

from react_agent.agents.expert_panel.config import EXPERT_REGISTRY, ExpertRole

from .analyzer import AnalysisResult


@dataclass
class ExpertSection:
    """Data class representing a section in the weekly report for an expert.

    Attributes:
        expert_role: The expert role for this section.
        expert_name: Name of the expert.
        summaries: List of content summaries from this expert.
        key_findings: List of key findings aggregated from analyses.
        implications: List of implications aggregated from analyses.
        content_count: Number of contents analyzed by this expert.
    """

    expert_role: ExpertRole
    expert_name: str
    summaries: List[str]
    key_findings: List[str]
    implications: List[str]
    content_count: int


@dataclass
class WeeklyReport:
    """Data class representing a weekly briefing report.

    Attributes:
        start_date: Start date of the reporting period.
        end_date: End date of the reporting period.
        total_crawled: Total number of contents crawled.
        total_analyzed: Total number of contents analyzed.
        new_chunks: Number of new chunks added to knowledge base.
        new_experts: List of newly registered dynamic experts.
        expert_sections: Dictionary mapping expert roles to their sections.
        cross_analysis: Cross-expert analysis summary.
        generated_at: Timestamp when the report was generated.
    """

    start_date: datetime
    end_date: datetime
    total_crawled: int
    total_analyzed: int
    new_chunks: int
    new_experts: List[str]
    expert_sections: Dict[ExpertRole, ExpertSection]
    cross_analysis: str = ""
    generated_at: datetime = field(default_factory=datetime.now)


class ReportGenerator:
    """Generator for weekly briefing reports.

    Converts expert analysis results into formatted markdown reports
    and handles file persistence.

    Attributes:
        output_dir: Directory path for saving generated reports.
    """

    EXPERT_ICONS: Dict[ExpertRole, str] = {
        ExpertRole.POLICY_EXPERT: "🏛️",
        ExpertRole.CARBON_CREDIT_EXPERT: "📜",
        ExpertRole.MARKET_EXPERT: "💹",
        ExpertRole.TECHNOLOGY_EXPERT: "⚡",
        ExpertRole.MRV_EXPERT: "📋",
    }

    REPORT_TEMPLATE = """# 주간 탄소정책 브리핑

**기간**: {start_date} ~ {end_date}
**생성일시**: {generated_at}

---

## 📊 주간 통계

| 항목 | 수치 |
|------|------|
| 수집 콘텐츠 | {total_crawled}건 |
| 분석 콘텐츠 | {total_analyzed}건 |
| 신규 청크 | {new_chunks}건 |
{new_experts_row}

---

## 📋 전문가별 분석

{expert_sections}

---

## 🔗 교차 분석

{cross_analysis}

---

## 📝 청크 요약

{chunk_summary}

---

*이 보고서는 자동으로 생성되었습니다.*
"""

    EXPERT_SECTION_TEMPLATE = """### {icon} {expert_name} ({role_name})

**분석 콘텐츠**: {content_count}건

#### 요약
{summaries}

#### 주요 발견
{key_findings}

#### 시사점
{implications}

"""

    def __init__(self, output_dir: str = "./data/weekly_reports") -> None:
        """Initialize the ReportGenerator.

        Args:
            output_dir: Directory path for saving generated reports.
        """
        self.output_dir = output_dir

    def generate_report(
        self,
        analysis_results: List[AnalysisResult],
        start_date: datetime,
        end_date: datetime,
        total_crawled: int = 0,
        total_analyzed: int = 0,
        new_chunks: int = 0,
        new_experts: Optional[List[str]] = None,
    ) -> WeeklyReport:
        """Generate a weekly report from analysis results.

        Args:
            analysis_results: List of analysis results from experts.
            start_date: Start date of the reporting period.
            end_date: End date of the reporting period.
            total_crawled: Total number of contents crawled.
            total_analyzed: Total number of contents analyzed.
            new_chunks: Number of new chunks added to knowledge base.
            new_experts: List of newly registered dynamic experts.

        Returns:
            WeeklyReport containing aggregated analysis data.
        """
        if new_experts is None:
            new_experts = []

        # Group analysis results by expert role
        expert_sections = self._group_by_expert(analysis_results)

        # Generate cross-analysis
        cross_analysis = self._generate_cross_analysis(expert_sections)

        return WeeklyReport(
            start_date=start_date,
            end_date=end_date,
            total_crawled=total_crawled,
            total_analyzed=total_analyzed or len(analysis_results),
            new_chunks=new_chunks,
            new_experts=new_experts,
            expert_sections=expert_sections,
            cross_analysis=cross_analysis,
        )

    def _group_by_expert(
        self, analysis_results: List[AnalysisResult]
    ) -> Dict[ExpertRole, ExpertSection]:
        """Group analysis results by expert role.

        Args:
            analysis_results: List of analysis results to group.

        Returns:
            Dictionary mapping expert roles to their aggregated sections.
        """
        grouped: Dict[ExpertRole, Dict] = {}

        for result in analysis_results:
            role = result.expert_role

            if role not in grouped:
                expert_config = EXPERT_REGISTRY.get(role)
                expert_name = expert_config.name if expert_config else str(role.value)

                grouped[role] = {
                    "expert_name": expert_name,
                    "summaries": [],
                    "key_findings": [],
                    "implications": [],
                    "content_count": 0,
                }

            if result.summary:
                grouped[role]["summaries"].append(result.summary)
            grouped[role]["key_findings"].extend(result.key_findings)
            grouped[role]["implications"].extend(result.implications)
            grouped[role]["content_count"] += 1

        # Convert to ExpertSection objects
        sections = {}
        for role, data in grouped.items():
            sections[role] = ExpertSection(
                expert_role=role,
                expert_name=data["expert_name"],
                summaries=data["summaries"],
                key_findings=data["key_findings"],
                implications=data["implications"],
                content_count=data["content_count"],
            )

        return sections

    def to_markdown(self, report: WeeklyReport) -> str:
        """Convert a WeeklyReport to markdown format.

        Args:
            report: The WeeklyReport to convert.

        Returns:
            Formatted markdown string.
        """
        # Format dates
        start_date_str = report.start_date.strftime("%Y년 %m월 %d일")
        end_date_str = report.end_date.strftime("%Y년 %m월 %d일")
        generated_at_str = report.generated_at.strftime("%Y-%m-%d %H:%M:%S")

        # Format new experts row
        if report.new_experts:
            new_experts_row = f"| 신규 전문가 | {', '.join(report.new_experts)} |"
        else:
            new_experts_row = ""

        # Format expert sections
        expert_sections_md = self._format_expert_sections(report.expert_sections)

        # Format cross analysis
        cross_analysis = report.cross_analysis or "교차 분석 데이터가 없습니다."

        # Generate chunk summary
        chunk_summary = self._generate_chunk_summary(report.expert_sections)

        return self.REPORT_TEMPLATE.format(
            start_date=start_date_str,
            end_date=end_date_str,
            generated_at=generated_at_str,
            total_crawled=report.total_crawled,
            total_analyzed=report.total_analyzed,
            new_chunks=report.new_chunks,
            new_experts_row=new_experts_row,
            expert_sections=expert_sections_md,
            cross_analysis=cross_analysis,
            chunk_summary=chunk_summary,
        )

    def _format_expert_sections(
        self, expert_sections: Dict[ExpertRole, ExpertSection]
    ) -> str:
        """Format expert sections as markdown.

        Args:
            expert_sections: Dictionary of expert sections.

        Returns:
            Formatted markdown string for all expert sections.
        """
        if not expert_sections:
            return "분석된 전문가 섹션이 없습니다."

        sections_md = []

        for role, section in expert_sections.items():
            icon = self.EXPERT_ICONS.get(role, "📌")

            # Format role name
            role_names = {
                ExpertRole.POLICY_EXPERT: "정책/법규 전문가",
                ExpertRole.CARBON_CREDIT_EXPERT: "탄소배출권 전문가",
                ExpertRole.MARKET_EXPERT: "시장/거래 전문가",
                ExpertRole.TECHNOLOGY_EXPERT: "감축기술 전문가",
                ExpertRole.MRV_EXPERT: "MRV/검증 전문가",
            }
            role_name = role_names.get(role, role.value)

            # Format summaries
            if section.summaries:
                summaries = "\n".join(f"- {s}" for s in section.summaries)
            else:
                summaries = "- 요약 없음"

            # Format key findings
            if section.key_findings:
                key_findings = "\n".join(f"- {f}" for f in section.key_findings)
            else:
                key_findings = "- 주요 발견 없음"

            # Format implications
            if section.implications:
                implications = "\n".join(f"- {i}" for i in section.implications)
            else:
                implications = "- 시사점 없음"

            section_md = self.EXPERT_SECTION_TEMPLATE.format(
                icon=icon,
                expert_name=section.expert_name,
                role_name=role_name,
                content_count=section.content_count,
                summaries=summaries,
                key_findings=key_findings,
                implications=implications,
            )
            sections_md.append(section_md)

        return "\n".join(sections_md)

    def save_report(self, report: WeeklyReport) -> str:
        """Save the report to a markdown file.

        Args:
            report: The WeeklyReport to save.

        Returns:
            File path of the saved report.
        """
        # Ensure output directory exists
        os.makedirs(self.output_dir, exist_ok=True)

        # Generate filename
        start_str = report.start_date.strftime("%Y%m%d")
        end_str = report.end_date.strftime("%Y%m%d")
        filename = f"weekly_briefing_{start_str}_{end_str}.md"
        filepath = os.path.join(self.output_dir, filename)

        # Generate markdown content
        markdown = self.to_markdown(report)

        # Write to file
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(markdown)

        return filepath

    def _generate_cross_analysis(
        self, expert_sections: Dict[ExpertRole, ExpertSection]
    ) -> str:
        """Generate cross-expert analysis summary.

        Identifies connections and patterns across different expert domains.

        Args:
            expert_sections: Dictionary of expert sections.

        Returns:
            Cross-analysis summary string.
        """
        if len(expert_sections) < 2:
            return "교차 분석을 위한 충분한 전문가 데이터가 없습니다."

        # Build a simple cross-analysis based on available data
        analysis_parts = []

        expert_roles = list(expert_sections.keys())
        total_findings = sum(
            len(s.key_findings) for s in expert_sections.values()
        )
        total_implications = sum(
            len(s.implications) for s in expert_sections.values()
        )

        analysis_parts.append(
            f"본 주간에는 {len(expert_roles)}개 분야의 전문가가 분석을 수행했습니다."
        )
        analysis_parts.append(
            f"총 {total_findings}개의 주요 발견과 {total_implications}개의 시사점이 도출되었습니다."
        )

        # Check for policy-market interaction
        if (
            ExpertRole.POLICY_EXPERT in expert_sections
            and ExpertRole.MARKET_EXPERT in expert_sections
        ):
            analysis_parts.append(
                "정책 변화가 시장에 미치는 영향에 대한 분석이 포함되어 있습니다."
            )

        # Check for technology-related analysis
        if ExpertRole.TECHNOLOGY_EXPERT in expert_sections:
            tech_section = expert_sections[ExpertRole.TECHNOLOGY_EXPERT]
            if tech_section.content_count > 0:
                analysis_parts.append(
                    "감축 기술 관련 동향이 분석에 반영되었습니다."
                )

        return " ".join(analysis_parts)

    def _generate_chunk_summary(
        self, expert_sections: Dict[ExpertRole, ExpertSection]
    ) -> str:
        """Generate a summary of knowledge base chunks.

        Args:
            expert_sections: Dictionary of expert sections.

        Returns:
            Chunk summary string.
        """
        if not expert_sections:
            return "이번 주에 추가된 청크가 없습니다."

        summary_parts = []
        total_content = sum(s.content_count for s in expert_sections.values())

        summary_parts.append(f"이번 주에 총 {total_content}건의 콘텐츠가 분석되었습니다.")

        # List expert contributions
        for role, section in expert_sections.items():
            if section.content_count > 0:
                summary_parts.append(
                    f"- {section.expert_name}: {section.content_count}건 분석"
                )

        return "\n".join(summary_parts)
