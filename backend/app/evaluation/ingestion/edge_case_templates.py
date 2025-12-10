"""Edge case templates for evaluation dataset generation.

This module provides template content and patterns for generating
edge case examples across 8 categories:
1. Very Short - 1-2 word queries
2. Very Long - 10K+ word articles
3. Special Characters - Unicode, emojis, code blocks
4. Misspellings - Common typos
5. Ambiguous - Multi-agent routing challenges
6. Minimal Context - Missing key information
7. Contradictory - Self-contradicting claims
8. Multilingual - Non-English or mixed language
"""

from __future__ import annotations

import random
from dataclasses import dataclass

# Very short query templates (1-2 words)
VERY_SHORT_QUERIES: list[dict[str, str]] = [
    {"content": "React?", "note": "Single word with question mark"},
    {"content": "help", "note": "Generic help request"},
    {"content": "Python vs", "note": "Incomplete comparison"},
    {"content": "fast?", "note": "Ambiguous single word"},
    {"content": "API", "note": "Acronym only"},
    {"content": "why", "note": "Single interrogative"},
    {"content": "bug", "note": "Single noun"},
    {"content": "best", "note": "Superlative without context"},
    {"content": "how", "note": "Single interrogative"},
    {"content": "error", "note": "Single word error report"},
]

# Misspelling patterns for common tech terms
MISSPELLING_PATTERNS: dict[str, list[str]] = {
    "React": ["Reavt", "Reacr", "Raect", "Reactt", "Reakt"],
    "Python": ["Pytohn", "Pyhton", "Pyton", "Pythob", "Phyton"],
    "JavaScript": ["Javascrip", "JavaSript", "Javasript", "JavaScirpt", "Javscript"],
    "TypeScript": ["TypeScipt", "Typescirpt", "Tyepscript", "Typscript", "TypeScrip"],
    "FastAPI": ["FastAPi", "FatsAPI", "FastApi", "Fasta PI", "FastAIP"],
    "PostgreSQL": ["Postgress", "PostgeSQL", "PostgresQL", "Postgres QL", "PostreSQL"],
    "MongoDB": ["MongoDb", "MongDB", "Mongdo", "MonogDB", "MongoBD"],
    "Kubernetes": ["Kuberneets", "Kuberentes", "Kubernates", "K8s", "Kubernetis"],
    "Docker": ["Dokcer", "Doker", "Dcoker", "Docekr", "Dockerr"],
    "Vue": ["Veu", "Vu", "Vuee", "Vuejs", "Vuje"],
    "Angular": ["Angualr", "Anuglar", "Angluar", "Anguler", "Anglar"],
    "GraphQL": ["GrapQL", "GraphQl", "GrahpQL", "GraphQGL", "Graphql"],
}

# Technical content snippets for generating long content
TECH_CONTENT_SNIPPETS: list[str] = [
    "Modern web development requires a deep understanding of both frontend and backend technologies.",
    "API design patterns have evolved significantly with the rise of microservices architecture.",
    "Performance optimization involves careful analysis of bottlenecks and systematic improvements.",
    "Security best practices include input validation, authentication, and authorization mechanisms.",
    "Database schema design impacts application scalability and maintainability significantly.",
    "Containerization with Docker simplifies deployment and ensures consistent environments.",
    "CI/CD pipelines automate testing, building, and deployment processes efficiently.",
    "State management in modern frameworks requires careful consideration of data flow patterns.",
    "Error handling strategies should provide meaningful feedback while maintaining security.",
    "Testing strategies span unit tests, integration tests, and end-to-end testing approaches.",
    "Caching mechanisms improve performance by reducing redundant computations and database queries.",
    "Logging and monitoring enable debugging and performance analysis in production environments.",
    "Code review practices improve code quality and facilitate knowledge sharing among team members.",
    "Documentation is essential for maintainability and onboarding new developers effectively.",
    "Version control workflows like GitFlow provide structure for collaborative development.",
]

# Special character content templates
SPECIAL_CHAR_TEMPLATES: list[dict[str, str]] = [
    {
        "content": "Performance metrics: ∑(latency) = 100ms, ∏(throughput) > 1000 req/s, ∫cost dt = $50/mo",
        "note": "Unicode math symbols",
    },
    {
        "content": "React 19 is blazing fast! Best framework for 2025 development",
        "note": "Emojis in tech content",
    },
    {
        "content": '```python\nprint("test"\n# Missing closing backticks and parenthesis',
        "note": "Malformed code block",
    },
    {
        "content": "R\u200be\u200ba\u200bc\u200bt vs V\u200bu\u200be comparison",
        "note": "Zero-width characters between letters",
    },
    {
        "content": "Compare: React\u00a0vs\u00a0Vue\u2003(non-breaking\u2002spaces)",
        "note": "Various whitespace characters",
    },
    {
        "content": "Arrow functions: () => {} vs function() {} \u2192 \u2190 \u2194",
        "note": "Unicode arrows",
    },
    {
        "content": "Check \u2713 Pass \u2717 Fail \u26a0 Warning \u2139 Info",
        "note": "Unicode symbols",
    },
    {
        "content": "```\ncode without language\n```\n```py\nmore code\n```",
        "note": "Multiple code blocks, inconsistent format",
    },
]

# Ambiguous content that could route to multiple agents
AMBIGUOUS_TEMPLATES: list[dict[str, str | list[str]]] = [
    {
        "content": "Is React secure enough for building authenticated REST APIs? Show me a complete tutorial with performance benchmarks.",
        "agents": [
            "tech_comparator",
            "security_auditor",
            "implementation_planner",
            "performance_analyst",
        ],
        "note": "4 agents: comparison, security, implementation, performance",
    },
    {
        "content": "Compare Next.js vs Nuxt.js for SEO-optimized e-commerce. Which has better security defaults and easier deployment?",
        "agents": ["tech_comparator", "security_auditor", "integration_feasibility"],
        "note": "3 agents: comparison, security, integration",
    },
    {
        "content": "Build a modern SaaS with authentication, real-time updates, CI/CD, and comprehensive monitoring dashboard.",
        "agents": [
            "implementation_planner",
            "security_auditor",
            "performance_analyst",
            "code_quality_critic",
        ],
        "note": "4 agents: implementation, security, performance, quality",
    },
    {
        "content": "Is the LangChain ecosystem still the best choice? What are the emerging alternatives and their trade-offs?",
        "agents": ["tech_comparator", "trend_validator", "dependency_mapper"],
        "note": "3 agents: comparison, trends, dependencies",
    },
    {
        "content": "Review this authentication implementation for security vulnerabilities, code quality, and performance issues.",
        "agents": ["security_auditor", "code_quality_critic", "performance_analyst"],
        "note": "3 agents: security, quality, performance",
    },
]

# Minimal context templates (missing key information)
MINIMAL_CONTEXT_TEMPLATES: list[dict[str, str]] = [
    {
        "content": "How do I implement authentication?",
        "missing": "technology/framework",
        "note": "No tech stack specified",
    },
    {
        "content": "Is it fast enough?",
        "missing": "what 'it' refers to",
        "note": "Ambiguous pronoun, no context",
    },
    {
        "content": "Migrate from the old API to the new one",
        "missing": "which APIs, versions",
        "note": "No specific API names or versions",
    },
    {
        "content": "Build a web app",
        "missing": "requirements, features, tech stack",
        "note": "Extremely vague request",
    },
    {
        "content": "Fix this code: function foo() { return bar }",
        "missing": "language, error, context",
        "note": "No language specified, unclear what's wrong",
    },
    {
        "content": "Which database should I use?",
        "missing": "use case, scale, requirements",
        "note": "No requirements specified",
    },
    {
        "content": "Make it faster",
        "missing": "what to optimize, current metrics",
        "note": "No baseline or target metrics",
    },
    {
        "content": "Deploy to production",
        "missing": "platform, infrastructure, app type",
        "note": "No deployment target specified",
    },
]

# Contradictory content templates
CONTRADICTORY_TEMPLATES: list[dict[str, str]] = [
    {
        "content": "React is consistently 10x faster than Vue in all benchmarks. However, independent tests show Vue outperforms React by 300% in rendering speed.",
        "contradiction": "performance claims",
        "note": "Directly contradicting performance statements",
    },
    {
        "content": "Always store passwords in plaintext for easy debugging during development. Security best practice: Never store passwords in plaintext under any circumstances.",
        "contradiction": "security advice",
        "note": "Dangerous vs correct security advice",
    },
    {
        "content": "Class components are the recommended approach in modern React. Functional components with hooks have completely replaced class components as best practice.",
        "contradiction": "React patterns",
        "note": "Outdated vs current best practices",
    },
    {
        "content": "MongoDB is a relational SQL database designed for structured data. PostgreSQL is a NoSQL document store optimized for unstructured data.",
        "contradiction": "database types",
        "note": "Completely reversed database categorizations",
    },
    {
        "content": "Microservices are always better than monoliths for any project size. Monoliths are always the superior choice regardless of scale.",
        "contradiction": "architecture advice",
        "note": "Absolute contradicting architecture claims",
    },
]

# Multilingual content templates
MULTILINGUAL_TEMPLATES: list[dict[str, str]] = [
    {
        "content": "¿Cómo implementar autenticación JWT en FastAPI? Necesito un tutorial paso a paso con ejemplos de código.",
        "language": "Spanish",
        "note": "Full Spanish technical question",
    },
    {
        "content": "Comment optimiser les performances de React en 2025? Quelles sont les meilleures pratiques actuelles?",
        "language": "French",
        "note": "Full French technical question",
    },
    {
        "content": "Wie integriere ich PostgreSQL mit FastAPI? Brauche ich SQLAlchemy oder gibt es bessere Alternativen?",
        "language": "German",
        "note": "Full German technical question",
    },
    {
        "content": "Build a React app // crear una aplicación with authentication // con autenticación",
        "language": "English-Spanish code-switching",
        "note": "Mixed language with code comments",
    },
    {
        "content": "Reactのパフォーマンスを最適化する方法を教えてください。ベストプラクティスは何ですか？",  # noqa: RUF001
        "language": "Japanese",
        "note": "Full Japanese technical question",
    },
    {
        "content": "Como configurar o Docker para desenvolvimento local? Preciso de um guia completo.",
        "language": "Portuguese",
        "note": "Full Portuguese technical question",
    },
    {
        "content": "Как настроить CI/CD pipeline с GitHub Actions? Нужен пример для Python проекта.",  # noqa: RUF001
        "language": "Russian",
        "note": "Full Russian technical question",
    },
    {
        "content": "React 앱에서 상태 관리를 어떻게 해야 하나요? Redux vs Zustand 비교해주세요.",
        "language": "Korean",
        "note": "Full Korean technical question",
    },
]


@dataclass
class EdgeCaseTemplates:
    """Templates and patterns for generating edge case content."""

    def get_very_short_queries(self) -> list[dict[str, str]]:
        """Get list of very short query examples.

        Returns:
            List of dicts with 'content' and 'note' keys.

        """
        return VERY_SHORT_QUERIES.copy()

    def generate_long_content(self, word_count: int = 10000) -> str:
        """Generate technical content of specified word count.

        Args:
            word_count: Target word count (default 10000).

        Returns:
            Generated technical content string.

        """
        content_parts = []
        current_words = 0

        while current_words < word_count:
            # Add random tech snippet
            snippet = random.choice(TECH_CONTENT_SNIPPETS)
            content_parts.append(snippet)
            current_words += len(snippet.split())

            # Add some variation
            if random.random() > 0.7:
                content_parts.append("\n\n")
            else:
                content_parts.append(" ")

        return "".join(content_parts).strip()

    def apply_misspellings(self, text: str, typo_rate: float = 0.3) -> str:
        """Apply realistic typos to text.

        Args:
            text: Original text to modify.
            typo_rate: Probability of applying typo to each word (0-1).

        Returns:
            Text with typos applied.

        """
        words = text.split()
        result = []

        for word in words:
            # Check if word matches any known tech term
            for correct, typos in MISSPELLING_PATTERNS.items():
                if word.lower() == correct.lower() and random.random() < typo_rate:
                    result.append(random.choice(typos))
                    break
            else:
                result.append(word)

        return " ".join(result)

    def get_special_char_templates(self) -> list[dict[str, str]]:
        """Get special character content templates.

        Returns:
            List of dicts with 'content' and 'note' keys.

        """
        return SPECIAL_CHAR_TEMPLATES.copy()

    def get_ambiguous_templates(self) -> list[dict[str, str | list[str]]]:
        """Get ambiguous content templates.

        Returns:
            List of dicts with 'content', 'agents', and 'note' keys.

        """
        return AMBIGUOUS_TEMPLATES.copy()

    def get_minimal_context_templates(self) -> list[dict[str, str]]:
        """Get minimal context templates.

        Returns:
            List of dicts with 'content', 'missing', and 'note' keys.

        """
        return MINIMAL_CONTEXT_TEMPLATES.copy()

    def get_contradictory_templates(self) -> list[dict[str, str]]:
        """Get contradictory content templates.

        Returns:
            List of dicts with 'content', 'contradiction', and 'note' keys.

        """
        return CONTRADICTORY_TEMPLATES.copy()

    def get_multilingual_templates(self) -> list[dict[str, str]]:
        """Get multilingual content templates.

        Returns:
            List of dicts with 'content', 'language', and 'note' keys.

        """
        return MULTILINGUAL_TEMPLATES.copy()

    def get_misspelling_example(self, tech_terms: list[str] | None = None) -> str:
        """Generate a sentence with misspellings.

        Args:
            tech_terms: List of tech terms to include (default: random selection).

        Returns:
            Sentence with misspelled tech terms.

        """
        if tech_terms is None:
            tech_terms = random.sample(list(MISSPELLING_PATTERNS.keys()), k=2)

        misspelled = []
        for term in tech_terms:
            if term in MISSPELLING_PATTERNS:
                misspelled.append(random.choice(MISSPELLING_PATTERNS[term]))
            else:
                misspelled.append(term)

        templates = [
            f"How to compare {misspelled[0]} vs {misspelled[1]}?",
            f"Tutorial for {misspelled[0]} with {misspelled[1]} integration",
            f"Is {misspelled[0]} better than {misspelled[1]} for web development?",
            f"Setup {misspelled[0]} and {misspelled[1]} in same project",
            f"Migrate from {misspelled[0]} to {misspelled[1]}",
        ]

        return random.choice(templates)
