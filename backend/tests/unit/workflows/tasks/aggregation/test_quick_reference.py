"""Unit tests for quick_reference extraction."""

import pytest

from app.domains.analysis.workflows.tasks.aggregation.quick_reference import (
    FILES_DISCLAIMER,
    _extract_complexity,
    _extract_critical_commands,
    _extract_files_to_modify,
    _extract_gotchas,
    _extract_prerequisites,
    _extract_primary_technology,
    extract_quick_reference,
)
from app.domains.analysis.schemas.tasks.aggregated_insights import QuickReference



@pytest.fixture
def sample_findings_complete():
    """Complete agent findings with all data."""
    return [
        {
            "agent_type": "tech_comparator",
            "result": {
                "primary_tech": "LangGraph",
                "alternatives": ["LangChain Agents"],
                "comparison": {},
                "recommendation": "Use LangGraph",
                "confidence_score": 0.85,
            },
        },
        {
            "agent_type": "dependency_mapper",
            "result": {
                "required_dependencies": [
                    {
                        "name": "langgraph",
                        "version": "0.6.7",
                        "purpose": "Graph-based workflows",
                        "compatibility": "compatible",
                    },
                    {
                        "name": "psycopg",
                        "version": "3.1.0",
                        "purpose": "PostgreSQL driver",
                        "compatibility": "compatible",
                    },
                ],
                "peer_dependencies": ["Python 3.11+", "PostgreSQL 14+"],
                "installation_notes": [
                    "pip install langgraph==0.6.7",
                    "pip install psycopg[binary]==3.1.0",
                ],
                "recommendation": "Install all dependencies",
                "confidence_score": 0.90,
            },
        },
        {
            "agent_type": "implementation_planner",
            "result": {
                "prerequisites": ["Python 3.11+", "PostgreSQL 14+", "Docker installed"],
                "steps": [
                    {
                        "step": 1,
                        "action": "Install dependencies with `pip install langgraph==0.6.7`",
                        "files": ["backend/requirements.txt"],
                    },
                    {
                        "step": 2,
                        "action": "Create graph structure",
                        "files": [
                            "backend/app/workflows/graph.py",
                            "backend/app/workflows/state.py",
                        ],
                    },
                    {
                        "step": 3,
                        "action": "Configure PostgreSQL checkpointing",
                        "files": ["backend/app/config/database.py"],
                    },
                ],
                "testing_strategy": "Write unit tests for each node",
                "estimated_time": "3-4 hours",
                "confidence_score": 0.85,
            },
        },
        {
            "agent_type": "security_auditor",
            "result": {
                "security_risks": [
                    {
                        "risk_type": "authentication",
                        "severity": "high",
                        "description": "API endpoints lack authentication",
                        "mitigation": "Implement JWT-based authentication",
                    },
                    {
                        "risk_type": "injection",
                        "severity": "medium",
                        "description": "SQL injection possible in raw queries",
                        "mitigation": "Use parameterized queries",
                    },
                ],
                "best_practices": [],
                "compliance_notes": [],
                "recommendation": "Address high-severity risks first",
                "confidence_score": 0.88,
            },
        },
        {
            "agent_type": "code_quality_critic",
            "result": {
                "code_issues": [
                    {
                        "issue_type": "code_smell",
                        "severity": "medium",
                        "description": "Large function with multiple responsibilities",
                        "suggestion": "Extract separate functions for each responsibility",
                    }
                ],
                "best_practices": [],
                "maintainability_score": 0.75,
                "refactoring_suggestions": [],
                "recommendation": "Refactor large functions",
                "confidence_score": 0.80,
            },
        },
    ]


@pytest.fixture
def sample_findings_minimal():
    """Minimal agent findings."""
    return [
        {
            "agent_type": "tech_comparator",
            "result": {
                "primary_tech": "React",
                "confidence_score": 0.80,
            },
        }
    ]


class TestExtractPrimaryTechnology:
    """Test primary technology extraction."""

    def test_extract_from_tech_comparator(self):
        """Test extraction from tech_comparator."""
        findings_by_type = {
            "tech_comparator": {"primary_tech": "LangGraph"},
            "dependency_mapper": {
                "required_dependencies": [{"name": "langgraph", "version": "0.6.7"}]
            },
        }
        result = _extract_primary_technology(findings_by_type)
        assert "LangGraph" in result
        assert "0.6.7" in result

    def test_extract_without_version(self):
        """Test extraction when version not in tech_comparator."""
        findings_by_type = {
            "tech_comparator": {"primary_tech": "React"},
            "dependency_mapper": {
                "required_dependencies": [{"name": "react", "version": "19.0.0"}]
            },
        }
        result = _extract_primary_technology(findings_by_type)
        assert "React" in result
        assert "19" in result

    def test_fallback_to_dependencies(self):
        """Test fallback when tech_comparator missing."""
        findings_by_type = {
            "dependency_mapper": {
                "required_dependencies": [{"name": "fastapi", "version": "0.115.0"}]
            },
        }
        result = _extract_primary_technology(findings_by_type)
        assert "fastapi" in result
        assert "0.115.0" in result

    def test_no_technology_found(self):
        """Test when no technology can be extracted."""
        findings_by_type = {}
        result = _extract_primary_technology(findings_by_type)
        assert result == ""


class TestExtractComplexity:
    """Test complexity extraction."""

    def test_extract_from_implementation_planner(self):
        """Test extraction from implementation planner."""
        findings_by_type = {"implementation_planner": {"estimated_time": "3-4 hours"}}
        result = _extract_complexity(findings_by_type)
        assert "Intermediate" in result
        assert "3-4 hours" in result

    def test_beginner_complexity(self):
        """Test beginner complexity detection."""
        findings_by_type = {"implementation_planner": {"estimated_time": "1-2 hours"}}
        result = _extract_complexity(findings_by_type)
        assert "Beginner" in result

    def test_advanced_complexity(self):
        """Test advanced complexity detection."""
        findings_by_type = {"implementation_planner": {"estimated_time": "6-8 hours"}}
        result = _extract_complexity(findings_by_type)
        assert "Advanced" in result

    def test_expert_complexity_days(self):
        """Test expert complexity with days."""
        findings_by_type = {"implementation_planner": {"estimated_time": "2-3 days"}}
        result = _extract_complexity(findings_by_type)
        assert "Expert" in result

    def test_default_complexity(self):
        """Test default when no estimate available."""
        findings_by_type = {}
        result = _extract_complexity(findings_by_type)
        assert "Intermediate" in result


class TestExtractPrerequisites:
    """Test prerequisites extraction."""

    def test_extract_from_dependency_mapper(self):
        """Test extraction from dependency mapper."""
        findings_by_type = {
            "dependency_mapper": {"peer_dependencies": ["Python 3.11+", "PostgreSQL 14+"]}
        }
        result = _extract_prerequisites(findings_by_type)
        assert len(result) == 2
        assert "Python 3.11+" in result
        assert "PostgreSQL 14+" in result

    def test_extract_from_implementation_planner(self):
        """Test extraction from implementation planner."""
        findings_by_type = {
            "implementation_planner": {"prerequisites": ["Node.js 18+", "Docker installed"]}
        }
        result = _extract_prerequisites(findings_by_type)
        assert len(result) == 2
        assert "Node.js 18+" in result

    def test_combine_sources(self):
        """Test combining prerequisites from multiple sources."""
        findings_by_type = {
            "dependency_mapper": {"peer_dependencies": ["Python 3.11+"]},
            "implementation_planner": {"prerequisites": ["PostgreSQL 14+", "Docker installed"]},
        }
        result = _extract_prerequisites(findings_by_type)
        assert len(result) <= 4
        assert "Python 3.11+" in result

    def test_max_four_prerequisites(self):
        """Test max 4 prerequisites enforced."""
        findings_by_type = {
            "dependency_mapper": {
                "peer_dependencies": ["Item 1", "Item 2", "Item 3", "Item 4", "Item 5"]
            }
        }
        result = _extract_prerequisites(findings_by_type)
        assert len(result) == 4


class TestExtractCriticalCommands:
    """Test critical commands extraction."""

    def test_extract_from_installation_notes(self):
        """Test extraction from dependency mapper installation notes."""
        findings_by_type = {
            "dependency_mapper": {
                "installation_notes": [
                    "pip install langgraph==0.6.7",
                    "pip install psycopg[binary]==3.1.0",
                ]
            }
        }
        result = _extract_critical_commands(findings_by_type)
        assert len(result) == 2
        assert "pip install langgraph==0.6.7" in result

    def test_extract_from_implementation_steps(self):
        """Test extraction from implementation planner steps."""
        findings_by_type = {
            "implementation_planner": {
                "steps": [
                    {
                        "step": 1,
                        "action": "Install with `npm install react@19.0.0`",
                    }
                ]
            }
        }
        result = _extract_critical_commands(findings_by_type)
        assert len(result) >= 1
        assert any("npm install" in cmd for cmd in result)

    def test_filter_install_commands(self):
        """Test only install commands are extracted."""
        findings_by_type = {
            "dependency_mapper": {
                "installation_notes": [
                    "pip install package",
                    "Remember to configure settings",  # Not a command
                ]
            }
        }
        result = _extract_critical_commands(findings_by_type)
        assert len(result) == 1
        assert "pip install" in result[0]

    def test_max_six_commands(self):
        """Test max 6 commands enforced."""
        findings_by_type = {
            "dependency_mapper": {
                "installation_notes": [f"pip install package{i}" for i in range(10)]
            }
        }
        result = _extract_critical_commands(findings_by_type)
        assert len(result) == 6


class TestExtractFilesToModify:
    """Test files to modify extraction."""

    def test_extract_from_steps(self):
        """Test extraction from implementation planner steps."""
        findings_by_type = {
            "implementation_planner": {
                "steps": [
                    {"step": 1, "files": ["backend/app/main.py"]},
                    {"step": 2, "files": ["backend/app/config.py", "backend/app/database.py"]},
                ]
            }
        }
        result = _extract_files_to_modify(findings_by_type)
        assert len(result) == 3
        assert "backend/app/main.py" in result
        assert "backend/app/config.py" in result

    def test_no_duplicates(self):
        """Test duplicates are removed."""
        findings_by_type = {
            "implementation_planner": {
                "steps": [
                    {"step": 1, "files": ["backend/app/main.py"]},
                    {"step": 2, "files": ["backend/app/main.py"]},
                ]
            }
        }
        result = _extract_files_to_modify(findings_by_type)
        assert len(result) == 1

    def test_max_ten_files(self):
        """Test max 10 files enforced."""
        findings_by_type = {
            "implementation_planner": {
                "steps": [{"step": 1, "files": [f"file_{i}.py" for i in range(15)]}]
            }
        }
        result = _extract_files_to_modify(findings_by_type)
        assert len(result) == 10


class TestExtractGotchas:
    """Test gotchas extraction."""

    def test_extract_from_security_risks(self):
        """Test extraction from security auditor."""
        findings_by_type = {
            "security_auditor": {
                "security_risks": [
                    {
                        "risk_type": "authentication",
                        "severity": "high",
                        "description": "Missing API key validation",
                        "mitigation": "Implement API key validation middleware",
                    }
                ]
            }
        }
        result = _extract_gotchas(findings_by_type)
        assert len(result) == 1
        assert "Authentication" in result[0].issue
        assert "high" in result[0].symptom
        assert "Implement" in result[0].quick_fix

    def test_extract_from_code_issues(self):
        """Test extraction from code quality critic."""
        findings_by_type = {
            "code_quality_critic": {
                "code_issues": [
                    {
                        "issue_type": "code_smell",
                        "severity": "medium",
                        "description": "Large function",
                        "suggestion": "Extract smaller functions",
                    }
                ]
            }
        }
        result = _extract_gotchas(findings_by_type)
        assert len(result) == 1
        assert "Code Smell" in result[0].issue

    def test_combine_security_and_code_issues(self):
        """Test combining security and code quality issues."""
        findings_by_type = {
            "security_auditor": {
                "security_risks": [
                    {
                        "risk_type": "xss",
                        "severity": "critical",
                        "description": "XSS vulnerability",
                        "mitigation": "Sanitize user input",
                    }
                ]
            },
            "code_quality_critic": {
                "code_issues": [
                    {
                        "issue_type": "antipattern",
                        "severity": "high",
                        "description": "God object pattern",
                        "suggestion": "Split into smaller classes",
                    }
                ]
            },
        }
        result = _extract_gotchas(findings_by_type)
        assert len(result) == 2

    def test_max_five_gotchas(self):
        """Test max 5 gotchas enforced."""
        findings_by_type = {
            "security_auditor": {
                "security_risks": [
                    {
                        "risk_type": f"risk_{i}",
                        "severity": "medium",
                        "description": f"Risk {i}",
                        "mitigation": f"Fix {i}",
                    }
                    for i in range(10)
                ]
            }
        }
        result = _extract_gotchas(findings_by_type)
        assert len(result) == 5


class TestExtractQuickReference:
    """Test full quick reference extraction."""

    def test_extract_complete_quick_reference(self, sample_findings_complete):
        """Test extraction with complete data."""
        result = extract_quick_reference(sample_findings_complete)

        assert result is not None
        assert "LangGraph" in result.primary_technology
        assert "0.6.7" in result.primary_technology
        assert "Intermediate" in result.complexity
        assert len(result.prerequisites) > 0
        assert len(result.critical_commands) > 0
        assert len(result.files_to_modify) > 0
        assert len(result.gotchas) > 0

    def test_extract_minimal_quick_reference(self, sample_findings_minimal):
        """Test extraction with minimal data."""
        result = extract_quick_reference(sample_findings_minimal)

        # Should still create QuickReference with defaults
        assert result is not None
        assert "React" in result.primary_technology
        assert "Intermediate" in result.complexity

    def test_extract_no_primary_technology(self):
        """Test extraction fails without primary technology."""
        findings = [
            {
                "agent_type": "dependency_mapper",
                "result": {"required_dependencies": []},
            }
        ]
        result = extract_quick_reference(findings)
        assert result is None

    def test_extract_empty_findings(self):
        """Test extraction with empty findings."""
        result = extract_quick_reference([])
        assert result is None

    def test_extract_invalid_findings(self):
        """Test extraction with invalid findings structure."""
        findings = [{"invalid": "structure"}]
        result = extract_quick_reference(findings)
        assert result is None

    def test_extract_handles_exceptions(self):
        """Test extraction handles exceptions gracefully."""
        findings = [
            {
                "agent_type": "tech_comparator",
                "result": None,  # Will cause exception
            }
        ]
        result = extract_quick_reference(findings)
        assert result is None


class TestFilesToModifyAntiHallucination:
    """Tests for files_to_modify extraction with anti-hallucination (Issue #299-304)."""

    def test_files_disclaimer_constant_exists(self):
        """Verify disclaimer constant exists and contains expected text."""
        assert FILES_DISCLAIMER is not None
        assert isinstance(FILES_DISCLAIMER, str)
        assert "AI-suggested" in FILES_DISCLAIMER or "suggested" in FILES_DISCLAIMER.lower()
        assert len(FILES_DISCLAIMER) > 0

    def test_empty_files_when_no_steps(self):
        """Verify empty files list when no implementation steps."""
        findings_by_type = {"implementation_planner": {"steps": []}}
        files = _extract_files_to_modify(findings_by_type)
        assert files == []

    def test_empty_files_when_no_implementation_planner(self):
        """Verify empty files list when implementation_planner is missing."""
        findings_by_type = {"tech_comparator": {"primary_tech": "React"}}
        files = _extract_files_to_modify(findings_by_type)
        assert files == []

    def test_empty_files_when_steps_have_no_files(self):
        """Verify empty files list when steps don't contain files field."""
        findings_by_type = {
            "implementation_planner": {
                "steps": [
                    {"step": 1, "action": "Install dependencies"},
                    {"step": 2, "action": "Configure environment"},
                ]
            }
        }
        files = _extract_files_to_modify(findings_by_type)
        assert files == []

    def test_extracted_files_limited_to_max(self):
        """Verify max 10 files extracted even when more are available."""
        # Create findings with 15 files
        steps = [{"step": i, "action": f"Step {i}", "files": [f"file{i}.py"]} for i in range(15)]
        findings_by_type = {"implementation_planner": {"steps": steps}}

        files = _extract_files_to_modify(findings_by_type)
        assert len(files) <= 10

    def test_duplicate_files_removed(self):
        """Verify duplicate files are filtered out."""
        findings_by_type = {
            "implementation_planner": {
                "steps": [
                    {"step": 1, "files": ["backend/app/main.py", "backend/app/config.py"]},
                    {"step": 2, "files": ["backend/app/main.py", "backend/app/utils.py"]},
                ]
            }
        }
        files = _extract_files_to_modify(findings_by_type)
        assert len(files) == 3  # main.py, config.py, utils.py
        assert "backend/app/main.py" in files
        assert "backend/app/config.py" in files
        assert "backend/app/utils.py" in files

    def test_quick_reference_has_files_disclaimer_field(self):
        """Verify QuickReference schema includes files_disclaimer field."""
        qr = QuickReference(
            primary_technology="Test Framework 1.0",
            complexity="Intermediate (Est. 3-4 hours)",
        )
        assert hasattr(qr, "files_disclaimer")
        assert isinstance(qr.files_disclaimer, str)
        assert len(qr.files_disclaimer) > 0

    def test_quick_reference_files_disclaimer_default_value(self):
        """Verify files_disclaimer has appropriate default value."""
        qr = QuickReference(
            primary_technology="Test Framework 1.0",
            complexity="Intermediate (Est. 3-4 hours)",
        )
        # Check that default disclaimer is set and contains key phrases
        assert "suggested" in qr.files_disclaimer.lower() or "AI" in qr.files_disclaimer
        assert "project" in qr.files_disclaimer.lower() or "adapt" in qr.files_disclaimer.lower()

    def test_files_extraction_with_valid_files(self):
        """Verify files are correctly extracted when present."""
        findings_by_type = {
            "implementation_planner": {
                "steps": [
                    {"step": 1, "files": ["src/index.ts", "src/config.ts"]},
                    {"step": 2, "files": ["src/utils.ts"]},
                ]
            }
        }
        files = _extract_files_to_modify(findings_by_type)
        assert len(files) == 3
        assert "src/index.ts" in files
        assert "src/config.ts" in files
        assert "src/utils.ts" in files

    def test_files_extraction_ignores_invalid_types(self):
        """Verify extraction handles invalid file types gracefully."""
        findings_by_type = {
            "implementation_planner": {
                "steps": [
                    {"step": 1, "files": ["valid.py", None, 123, {}, []]},
                    {"step": 2, "files": "not_a_list"},
                ]
            }
        }
        files = _extract_files_to_modify(findings_by_type)
        assert len(files) == 1
        assert "valid.py" in files
