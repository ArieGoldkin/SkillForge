"""Unit tests for aggregation Jinja2 templates."""

from app.core.template_utils import render_jinja_template

@pytest.mark.unit


class TestAggregationFindingsTemplate:
    """Test aggregation_findings.j2 template rendering."""

    def test_template_with_empty_data(self):
        """Test template renders with empty data."""
        context = {
            "agent_findings": [],
            "conflicts": [],
            "confidence_scores": {},
        }

        result = render_jinja_template("aggregation_findings.j2", context)

        assert "AGENT FINDINGS" in result
        assert "CONFIDENCE SCORES" in result
        assert len(result) > 0

    def test_template_with_single_finding(self):
        """Test template renders with single agent finding."""
        context = {
            "agent_findings": [
                {
                    "agent_type": "tech_comparator",
                    "findings": {"primary_tech": "LangGraph", "recommendation": "Use it"},
                }
            ],
            "conflicts": [],
            "confidence_scores": {"tech_comparator": 0.85},
        }

        result = render_jinja_template("aggregation_findings.j2", context)

        assert "TECH COMPARATOR" in result
        assert "0.85" in result
        assert "LangGraph" in result
        assert "primary_tech" in result

    def test_template_with_multiple_findings(self):
        """Test template renders with multiple agent findings."""
        context = {
            "agent_findings": [
                {
                    "agent_type": "tech_comparator",
                    "findings": {"primary_tech": "LangGraph"},
                },
                {
                    "agent_type": "security_auditor",
                    "findings": {"security_risks": []},
                },
            ],
            "conflicts": [],
            "confidence_scores": {"tech_comparator": 0.85, "security_auditor": 0.90},
        }

        result = render_jinja_template("aggregation_findings.j2", context)

        assert "TECH COMPARATOR" in result
        assert "SECURITY AUDITOR" in result
        assert "0.85" in result
        assert "0.90" in result

    def test_template_with_conflicts(self):
        """Test template renders conflicts section when conflicts exist."""
        context = {
            "agent_findings": [
                {
                    "agent_type": "tech_comparator",
                    "findings": {"recommendation": "Use LangGraph"},
                }
            ],
            "conflicts": [
                {
                    "agent_1": "tech_comparator",
                    "agent_2": "security_auditor",
                    "conflict": "Tech recommends, security warns",
                }
            ],
            "confidence_scores": {"tech_comparator": 0.85},
        }

        result = render_jinja_template("aggregation_findings.j2", context)

        assert "CONFLICTS DETECTED" in result
        assert "Tech recommends, security warns" in result
        assert "tech_comparator" in result
        assert "security_auditor" in result

    def test_template_without_conflicts(self):
        """Test template does not render conflicts section when no conflicts."""
        context = {
            "agent_findings": [
                {
                    "agent_type": "tech_comparator",
                    "findings": {"recommendation": "Use LangGraph"},
                }
            ],
            "conflicts": [],
            "confidence_scores": {"tech_comparator": 0.85},
        }

        result = render_jinja_template("aggregation_findings.j2", context)

        assert "CONFLICTS DETECTED" not in result

    def test_template_confidence_scores_sorted(self):
        """Test template sorts confidence scores in descending order."""
        context = {
            "agent_findings": [],
            "conflicts": [],
            "confidence_scores": {
                "tech_comparator": 0.75,
                "security_auditor": 0.90,
                "implementation_planner": 0.80,
            },
        }

        result = render_jinja_template("aggregation_findings.j2", context)

        # Find confidence scores section
        scores_section = result.split("CONFIDENCE SCORES:")[1]
        lines = [line.strip() for line in scores_section.split("\n") if line.strip()]

        # Should be sorted: security_auditor (0.90), implementation_planner (0.80),
        # tech_comparator (0.75)
        assert "security_auditor: 0.90" in lines[0]
        assert "implementation_planner: 0.80" in lines[1]
        assert "tech_comparator: 0.75" in lines[2]

    def test_template_findings_json_formatting(self):
        """Test template formats findings as JSON."""
        findings_data = {
            "primary_tech": "LangGraph",
            "alternatives": ["LangChain", "Temporal"],
            "comparison": {"LangGraph": {"pros": ["Control"], "cons": ["Complex"]}},
        }
        context = {
            "agent_findings": [
                {
                    "agent_type": "tech_comparator",
                    "findings": findings_data,
                }
            ],
            "conflicts": [],
            "confidence_scores": {"tech_comparator": 0.85},
        }

        result = render_jinja_template("aggregation_findings.j2", context)

        # Should contain JSON-formatted findings
        assert '"primary_tech"' in result
        assert '"LangGraph"' in result
        assert '"alternatives"' in result
        # Verify it's valid JSON structure
        json_start = result.find("Findings: {")
        assert json_start > 0

    def test_template_agent_type_formatting(self):
        """Test template formats agent_type with underscores replaced."""
        context = {
            "agent_findings": [
                {
                    "agent_type": "tech_comparator",
                    "findings": {},
                },
                {
                    "agent_type": "security_auditor",
                    "findings": {},
                },
            ],
            "conflicts": [],
            "confidence_scores": {"tech_comparator": 0.85, "security_auditor": 0.90},
        }

        result = render_jinja_template("aggregation_findings.j2", context)

        # Should replace underscores with spaces and uppercase in headers
        assert "TECH COMPARATOR" in result
        assert "SECURITY AUDITOR" in result
        # Check that formatted headers appear (not raw agent_type in findings section)
        # Exclude CONTRIBUTING AGENTS section which uses raw agent_type
        contributing_section = result.split("AGENT FINDINGS:")[0]
        findings_section = result.split("AGENT FINDINGS:")[1].split("CONFIDENCE SCORES:")[0]
        # Raw agent_type can appear in CONTRIBUTING AGENTS section
        assert "tech_comparator" in contributing_section  # OK in contributing agents list
        # But should not appear in formatted findings headers
        assert "tech_comparator" not in findings_section  # Should not appear in header
        assert "security_auditor" not in findings_section  # Should not appear in header
