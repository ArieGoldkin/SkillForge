# Real-World Data Collection Strategy for SkillForge Evaluation Datasets

**Issue:** #224
**Date:** December 10, 2025
**Status:** Research Complete
**Researcher:** UX Researcher Agent

---

## Executive Summary

SkillForge currently uses 41 synthetic evaluation examples across 8 test documents. This research identifies **9 high-quality real data sources** for technical content, prioritizes them by ROI (Quality × Quantity / Effort), and provides actionable collection strategies with specific API details, rate limits, and licensing considerations.

**Top 3 Recommended Sources (Immediate Action):**
1. **GitHub READMEs & Docs** (High quality, easy collection, permissive licensing)
2. **arXiv CS Papers** (Expert-level content, free API, excellent diversity)
3. **Official Framework Docs** (Gold standard quality, manual collection but high ROI)

---

## Table of Contents

1. [Real Data Source Analysis](#1-real-data-source-analysis)
2. [Content Taxonomy](#2-content-taxonomy)
3. [Data Collection Checklist](#3-data-collection-checklist)
4. [Source Prioritization Matrix](#4-source-prioritization-matrix)
5. [Implementation Roadmap](#5-implementation-roadmap)
6. [Appendix: API Details & Code Examples](#appendix-api-details--code-examples)

---

## 1. Real Data Source Analysis

### 1.1 GitHub (READMEs, Docs, Issues, PRs)

**API:** [GitHub REST API](https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api)

**Rate Limits (2025):**
- Authenticated: **5,000 requests/hour** (REST API)
- GraphQL: **5,000 points/hour** (can be split with REST for higher throughput)
- Unauthenticated: Severely limited (new restrictions as of May 2025)

**Content Types Available:**
- READMEs (project overviews, setup guides)
- Documentation folders (tutorials, architecture docs)
- Issues (troubleshooting, feature discussions)
- Pull Requests (code reviews, implementation patterns)
- Discussions (Q&A, RFCs)

**Licensing:**
- **Public repos:** Most use permissive licenses (MIT, Apache 2.0, BSD)
- **Check:** Each repo's LICENSE file
- **Best Practice:** Filter by license type using GitHub API (`license` field)
- **Terms:** Cannot scrape without authentication (May 2025 update)

**Data Quality:**
- High: Official framework repos (React, FastAPI, Next.js)
- Medium: Popular community repos (10k+ stars)
- Variable: Long-tail repos (may have incomplete docs)

**Collection Strategy:**
```python
# Target high-quality repos by topic
topics = ["fastapi", "react", "langchain", "kubernetes", "postgresql"]
min_stars = 1000  # Quality threshold

# Prioritize:
# 1. READMEs with installation + usage sections
# 2. docs/ folders with tutorials
# 3. Issues with "documentation" or "question" labels
# 4. PRs with architectural discussions
```

**Diversity:**
- 69+ languages
- All tech domains (frontend, backend, AI/ML, DevOps, mobile)
- Multiple difficulty levels (beginner guides → advanced architecture)

**Effort:** Low (API-driven, well-documented, Python libraries available: PyGithub)

**Estimated Volume:** 10,000+ high-quality documents available

---

### 1.2 arXiv Computer Science Papers

**API:** [arXiv API](https://info.arxiv.org/help/api/index.html)

**Rate Limits:**
- **1 request per 3 seconds** (mandatory delay)
- Single connection at a time
- Bulk downloads discouraged (use Amazon S3 for bulk access)

**Content Types Available:**
- Research papers (cs.AI, cs.LG, cs.SE, cs.DB, cs.CL)
- Abstracts (concise summaries)
- Preprints (cutting-edge research)

**Licensing:**
- **Default:** arXiv license (non-exclusive, cannot redistribute PDFs without permission)
- **Some papers:** CC BY-SA 4.0, CC BY-NC-SA 4.0 (redistribution allowed)
- **Critical:** Must link back to arXiv for full-text downloads
- **Acknowledgment Required:** "Thank you to arXiv for use of its open access interoperability."

**Data Quality:**
- Very High (peer-reviewed or pre-peer review)
- Expert-level content
- Cutting-edge techniques

**Collection Strategy:**
```python
# Focus on CS categories
categories = ["cs.AI", "cs.LG", "cs.SE", "cs.DB", "cs.CL", "cs.DC"]

# Target recent papers (2023-2025)
# Extract: Title, Abstract, Introduction, Methodology sections
# Skip: Heavy math sections (unless ML/AI focused)

# Sample query: cs.AI papers on LangGraph, RAG, agents
search_query = 'cat:cs.AI AND (ti:"language model" OR abs:"agent")'
```

**Diversity:**
- Theoretical + practical papers
- Cutting-edge AI/ML techniques
- Software engineering best practices
- Database optimization strategies

**Effort:** Medium (slow API, rate-limited, PDF parsing required)

**Estimated Volume:** 50,000+ relevant CS papers (last 5 years)

---

### 1.3 Stack Overflow (Questions, Answers, Tags)

**API:** [Stack Exchange API](https://api.stackexchange.com/)

**Rate Limits:**
- Authenticated: **10,000 requests/day**
- Unauthenticated: **300 requests/day**
- Backoff headers provided (must respect)

**Content Types Available:**
- Questions (problem statements)
- Answers (solutions with code examples)
- Comments (clarifications)
- Tags (topic categorization)

**Licensing:**
- **All content:** CC BY-SA 4.0 (requires attribution)
- **Cannot:** Represent as endorsed by Stack Overflow
- **Must:** Provide attribution link

**Data Quality:**
- **Very High:** Community-moderated, curated over 17+ years
- **83+ million Q&A pairs** (human-verified)
- **69,000+ topics**
- Filters out noise, bias, duplicates, inaccuracies

**Collection Strategy:**
```python
# Target high-quality questions
min_score = 10  # Upvotes threshold
has_accepted_answer = True

# Focus on tags relevant to SkillForge
tags = ["fastapi", "react", "python", "typescript", "langchain",
        "postgresql", "docker", "kubernetes", "oauth2", "jwt"]

# Prioritize:
# 1. Questions with accepted answers
# 2. Answers with code blocks
# 3. High upvote count (10+)
```

**Diversity:**
- Real-world problems (not synthetic)
- Multiple solutions per problem
- Beginner → expert difficulty
- All popular frameworks and languages

**Effort:** Low (excellent API, Python library: stackapi, well-documented)

**Estimated Volume:** 100,000+ high-quality Q&A pairs for target topics

---

### 1.4 Official Framework Documentation

**Sources:**
- React: https://react.dev/learn
- FastAPI: https://fastapi.tiangolo.com/
- Next.js: https://nextjs.org/docs
- LangChain: https://python.langchain.com/docs/
- PostgreSQL: https://www.postgresql.org/docs/
- Kubernetes: https://kubernetes.io/docs/

**API:** Manual scraping (no official APIs, use requests + BeautifulSoup)

**Rate Limits:** No formal limits, but:
- Use polite crawling (1 request/second)
- Respect robots.txt
- Set proper User-Agent

**Content Types Available:**
- Tutorials (step-by-step guides)
- API references (detailed specifications)
- Examples (working code samples)
- Concept explanations (architecture, patterns)

**Licensing:**
- **React:** MIT License (highly permissive)
- **FastAPI:** MIT License
- **LangChain:** MIT License
- **Most frameworks:** Permissive licenses (MIT, Apache 2.0)
- **Always check:** Each site's license page

**Data Quality:**
- **Gold Standard** (highest quality)
- Written by framework maintainers
- Kept up-to-date with releases
- Clear, well-structured

**Collection Strategy:**
```python
# Target specific sections
sections = [
    "tutorials",  # Step-by-step guides
    "guides",     # How-to articles
    "concepts",   # Architecture explanations
    "examples"    # Code samples
]

# Skip:
# - API references (too granular)
# - Changelog (version-specific)
# - Blog posts (marketing-heavy)
```

**Diversity:**
- Limited to specific frameworks
- High quality compensates for narrow scope
- Multiple difficulty levels per framework

**Effort:** Medium-High (manual scraping, must maintain scrapers, rate-limiting considerations)

**Estimated Volume:** 500-1,000 high-quality documents across top frameworks

---

### 1.5 Hacker News (Technical Posts, Ask HN, Show HN)

**API:** [Hacker News Firebase API](https://github.com/HackerNews/API)

**Rate Limits:**
- **No rate limit** (as of 2025)
- Real-time access via Firebase
- Up to 500 top stories available

**Content Types Available:**
- Stories (links to articles)
- Ask HN (questions and discussions)
- Show HN (project showcases)
- Comments (expert insights)

**Licensing:**
- **No explicit license** for HN content
- **Linked articles:** Check each article's license
- **Best practice:** Collect links, then fetch article content with permission

**Data Quality:**
- High: Community-curated (upvote system)
- Expert discussions in comments
- Trending topics in tech

**Collection Strategy:**
```python
# Target specific categories
endpoints = [
    "/v0/topstories",   # Most popular
    "/v0/beststories",  # Highest quality
    "/v0/askstories",   # Q&A format
    "/v0/showstories"   # Project demos
]

# Filter by score
min_score = 100  # Ensure high engagement

# Focus on:
# 1. Ask HN with detailed answers
# 2. Show HN with technical writeups
# 3. Top stories linking to tutorials/guides
```

**Diversity:**
- Cutting-edge topics
- Real-world problems
- Community-validated quality

**Effort:** Low (simple Firebase API, no rate limits, Python libraries available)

**Estimated Volume:** 10,000+ high-quality posts per year

---

### 1.6 YouTube (Educational Tech Channels)

**API:** [YouTube Data API v3](https://developers.google.com/youtube/v3/) + [youtube-transcript-api](https://pypi.org/project/youtube-transcript-api/)

**Rate Limits:**
- YouTube API: **10,000 quota units/day** (1 video = ~3 units)
- Transcript API: No official rate limit (reverse-engineered)

**Content Types Available:**
- Tutorials (step-by-step coding videos)
- Talks (conference presentations)
- Demos (product showcases)
- Transcripts (auto-generated or manual)

**Licensing:**
- **Videos:** Varies by creator (often All Rights Reserved)
- **Transcripts:** Same as video license
- **Best practice:** Link to video, extract key insights for educational use (fair use)
- **Cannot:** Redistribute transcripts without permission

**Data Quality:**
- **High:** Channels like Fireship, ThePrimeagen, Traversy Media
- **Variable:** Smaller channels (quality varies)
- **Challenge:** Auto-generated transcripts have errors

**Collection Strategy:**
```python
# Target high-quality channels
channels = [
    "UCsBjURrPoezykLs9EqgamOA",  # Fireship
    "UC8butISFwT-Wl7EV0hUK0BQ",  # freeCodeCamp
    # ... (add more)
]

# Filter videos:
min_views = 10000  # Quality threshold
has_transcript = True

# Extract:
# 1. Transcript (with timestamps)
# 2. Code snippets from description
# 3. Key concepts from comments
```

**Diversity:**
- Frontend, backend, AI/ML, DevOps
- Beginner → advanced
- Multiple teaching styles

**Effort:** Medium (API setup, transcript parsing, quality filtering)

**Estimated Volume:** 5,000+ high-quality tutorial videos

---

### 1.7 Dev.to & Medium (Technical Articles)

**Dev.to API:** [Forem API](https://developers.forem.com/api)
**Medium:** RSS feeds (no official API for content)

**Rate Limits:**
- Dev.to: **No strict limit** (be respectful, ~1 req/sec)
- Medium: RSS-based (no formal API)

**Content Types Available:**
- Tutorials (step-by-step guides)
- Opinion pieces (best practices)
- Project showcases (case studies)

**Licensing:**
- **Dev.to:** Authors retain copyright, platform has CC BY-SA 4.0 policy
- **Medium:** Authors retain rights, check each article's license
- **Cannot:** Scrape Medium content (Terms of Service violation)

**Data Quality:**
- **Variable:** No strict quality control
- **High:** Top authors with many followers
- **Low:** Beginner content with errors

**Collection Strategy:**
```python
# Dev.to: Target top tags
tags = ["python", "fastapi", "react", "devops", "kubernetes"]
min_reactions = 50  # Quality threshold

# Medium: Use RSS feeds for popular tags
# Risk: Medium may block aggressive scraping

# Focus on:
# 1. Articles with 100+ reactions (Dev.to)
# 2. Publications (Better Call Saul, The Startup)
```

**Diversity:**
- Real-world use cases
- Diverse writing styles
- Mix of beginner/advanced content

**Effort:** Low (Dev.to), High (Medium - scraping risks)

**Estimated Volume:** 50,000+ articles (Dev.to), 100,000+ (Medium, risky)

---

### 1.8 Reddit (r/programming, r/webdev, r/machinelearning)

**API:** [Reddit API](https://www.reddit.com/dev/api/)

**Rate Limits:**
- Authenticated: **60 requests/minute**
- OAuth2 required for most endpoints

**Content Types Available:**
- Discussion threads (Q&A, troubleshooting)
- Project showcases (Show & Tell)
- News links (article aggregation)
- Comments (expert insights)

**Licensing:**
- **Reddit content:** User-submitted, check Reddit TOS
- **Risk:** Content ownership unclear, may not be redistributable
- **Best practice:** Use for inspiration, not direct reproduction

**Data Quality:**
- **Variable:** Depends on subreddit moderation
- **High:** r/programming (strict moderation), r/askprogramming
- **Medium:** r/webdev, r/learnprogramming
- **Challenge:** Noise, memes, off-topic posts

**Collection Strategy:**
```python
# Target quality subreddits
subreddits = [
    "programming",
    "webdev",
    "Python",
    "reactjs",
    "MachineLearning",
    "devops"
]

# Filter:
min_upvotes = 100  # Quality threshold
flair = ["Tutorial", "Question", "Discussion"]

# Skip:
# - Memes, humor posts
# - News links (no analysis)
```

**Diversity:**
- Real-world problems
- Community-validated solutions
- Diverse tech stack coverage

**Effort:** Medium (API setup, noise filtering, OAuth complexity)

**Estimated Volume:** 10,000+ quality threads per month

---

### 1.9 Cloudflare, Vercel, AWS Blogs (Official Company Blogs)

**Sources:**
- Cloudflare Blog: https://blog.cloudflare.com/
- Vercel Blog: https://vercel.com/blog
- AWS Blog: https://aws.amazon.com/blogs/
- Supabase Blog: https://supabase.com/blog
- PlanetScale Blog: https://planetscale.com/blog

**API:** RSS feeds (most blogs offer RSS), manual scraping

**Rate Limits:** No formal limits (polite crawling)

**Content Types Available:**
- Product announcements (new features)
- Architecture deep-dives (how systems work)
- Case studies (real-world implementations)
- Performance optimizations (benchmarks)

**Licensing:**
- **Typically:** All Rights Reserved (company blog content)
- **Can:** Reference and cite with attribution
- **Cannot:** Republish full articles without permission

**Data Quality:**
- **Very High:** Written by engineers at leading companies
- **Expert-level:** Deep technical details
- **Production-ready:** Battle-tested patterns

**Collection Strategy:**
```python
# Use RSS feeds for updates
rss_feeds = [
    "https://blog.cloudflare.com/rss/",
    "https://vercel.com/blog/rss.xml",
    # ...
]

# Filter by category:
categories = [
    "Engineering",
    "Architecture",
    "Performance",
    "Security"
]

# Skip:
# - Marketing posts
# - Product announcements (no tech details)
```

**Diversity:**
- Edge computing (Cloudflare, Vercel)
- Cloud infrastructure (AWS, GCP)
- Databases (Supabase, PlanetScale)
- Serverless patterns

**Effort:** Low (RSS-based, well-structured HTML)

**Estimated Volume:** 500+ high-quality articles per year across all blogs

---

## 2. Content Taxonomy

### 2.1 Content Types

| Type | Description | Example Sources | Evaluation Focus |
|------|-------------|-----------------|------------------|
| **Tutorial** | Step-by-step guides | Official docs, Dev.to, YouTube | Implementation Planner, Code Quality |
| **Comparison** | Technology A vs B | GitHub issues, Reddit, HN | Tech Comparator, Security Auditor |
| **Security Audit** | Vulnerability analysis | Stack Overflow, GitHub Security, arXiv | Security Auditor, Best Practices |
| **Performance** | Optimization techniques | Company blogs, arXiv, Stack Overflow | Performance Optimizer, Architecture |
| **Troubleshooting** | Debugging guides | Stack Overflow, GitHub issues, Reddit | Debugging Specialist, Reporter |
| **Architecture** | System design | arXiv papers, company blogs, GitHub | Architecture Reviewer, Integration |

### 2.2 Technical Domains

| Domain | Subtopics | Priority | Current Coverage |
|--------|-----------|----------|------------------|
| **Frontend** | React, Next.js, Svelte, Vue, TypeScript | High | 2/8 docs (25%) |
| **Backend** | FastAPI, Express, Django, Flask, GraphQL | High | 2/8 docs (25%) |
| **Databases** | PostgreSQL, MongoDB, Redis, Vector DBs | Medium | 1/8 docs (12.5%) |
| **AI/ML** | LangChain, LangGraph, RAG, Embeddings | High | 2/8 docs (25%) |
| **DevOps** | Docker, Kubernetes, CI/CD, Monitoring | Medium | 1/8 docs (12.5%) |
| **Security** | OAuth2, JWT, RBAC, Encryption | High | 0/8 docs (0%) |
| **Mobile** | React Native, Flutter, iOS, Android | Low | 0/8 docs (0%) |
| **Data Science** | Pandas, NumPy, Jupyter, ML Ops | Low | 0/8 docs (0%) |

**Gap Analysis:**
- **Security domain:** Completely missing from current fixtures
- **Mobile:** Not represented (consider adding if target audience includes mobile devs)
- **Heavy bias:** Toward web development (6/8 docs)

---

### 2.3 Difficulty Levels

| Level | Characteristics | Target Readers | Example Topics |
|-------|----------------|----------------|----------------|
| **Beginner** | Setup, basics, hello world | New to technology | "Installing React", "First FastAPI endpoint" |
| **Intermediate** | Real-world patterns | 1-2 years experience | "React Context vs Redux", "FastAPI dependency injection" |
| **Advanced** | Optimization, architecture | 3-5 years experience | "React Server Components internals", "FastAPI async patterns" |
| **Expert** | Research, cutting-edge | 5+ years, architects | "Custom React reconciler", "LangGraph advanced routing" |

**Current Distribution (8 docs):**
- Beginner: 0 (0%)
- Intermediate: 6 (75%)
- Advanced: 2 (25%)
- Expert: 0 (0%)

**Recommendation:** Add 2 beginner-level docs (e.g., "Getting Started with FastAPI", "React Basics") and 2 expert-level docs (e.g., arXiv papers on advanced topics).

---

### 2.4 Quality Tiers

| Tier | Criteria | Sources | Use Cases |
|------|----------|---------|-----------|
| **Gold** | Official, maintained, expert-written | Official docs, arXiv, company blogs | Baseline for "perfect" agent output |
| **Silver** | Community-curated, high engagement | Stack Overflow (10+ votes), GitHub (1k+ stars) | Diverse real-world scenarios |
| **Bronze** | User-generated, moderate quality | Dev.to (50+ reactions), Reddit (100+ upvotes) | Edge cases, niche topics |

**Evaluation Strategy:**
- **Gold:** Agents should score ≥90% on gold-tier content
- **Silver:** Agents should score ≥80% on silver-tier content
- **Bronze:** Agents should score ≥70% on bronze-tier content (more forgiving for noisy content)

---

## 3. Data Collection Checklist

### 3.1 What Makes a Good Evaluation Example?

**Content Characteristics:**
- [ ] **Length:** 500-5,000 words (too short = not enough signal, too long = expensive to embed)
- [ ] **Structure:** Clear headings, code blocks, examples
- [ ] **Clarity:** Well-written, not machine-translated
- [ ] **Relevance:** Matches SkillForge's target audience (developers learning new tech)
- [ ] **Freshness:** Published within last 3 years (avoid outdated patterns)

**Metadata Requirements:**
- [ ] **Source URL:** Must be publicly accessible
- [ ] **License:** Clearly identified (MIT, Apache, CC BY-SA, etc.)
- [ ] **Date:** Publication or last updated date
- [ ] **Topics/Tags:** At least 2 relevant tags (e.g., "fastapi", "authentication")
- [ ] **Content Type:** Tutorial, comparison, troubleshooting, etc.

**Diversity Criteria:**
- [ ] **Domain Coverage:** Ensure 10%+ representation of each priority domain
- [ ] **Difficulty Mix:** 20% beginner, 50% intermediate, 25% advanced, 5% expert
- [ ] **Quality Tiers:** 30% gold, 50% silver, 20% bronze

**Avoid:**
- [ ] Marketing content (product pitches, not technical)
- [ ] Personal blogs (unless high-quality, e.g., Dan Abramov's blog)
- [ ] Outdated frameworks (jQuery tutorials, Python 2.x guides)
- [ ] Non-English content (unless multilingual support planned)

---

### 3.2 How to Identify Edge Cases in the Wild?

**Edge Case Categories:**

1. **Ambiguous Content**
   - Articles that mix multiple topics (e.g., "React + FastAPI full-stack tutorial")
   - **Why useful:** Tests agent's ability to identify multiple domains
   - **Where to find:** GitHub repos with multi-language codebases, full-stack tutorials

2. **Controversial Topics**
   - Debates (e.g., "TypeScript vs JavaScript", "REST vs GraphQL")
   - **Why useful:** Tests Tech Comparator's neutrality and balance
   - **Where to find:** Hacker News discussions, Reddit r/programming

3. **Breaking Changes**
   - Articles about major version upgrades (e.g., "Migrating to React 19")
   - **Why useful:** Tests agent's ability to identify migration complexity
   - **Where to find:** Official blog posts, GitHub release notes

4. **Anti-Patterns**
   - "Don't Do This" articles (e.g., "Common FastAPI mistakes")
   - **Why useful:** Tests Security Auditor's ability to flag bad practices
   - **Where to find:** Stack Overflow highly-upvoted answers, Dev.to

5. **Niche Technologies**
   - Uncommon frameworks (e.g., Elm, Gleam, Zig)
   - **Why useful:** Tests agent's ability to handle unfamiliar topics
   - **Where to find:** HN "Show HN", GitHub Trending (less popular languages)

6. **Very Short Content**
   - README badges, one-liner answers, code snippets
   - **Why useful:** Tests chunking and embedding logic on minimal text
   - **Where to find:** GitHub READMEs, Stack Overflow "tl;dr" answers

7. **Very Long Content**
   - 10,000+ word deep dives, entire books
   - **Why useful:** Tests chunking strategy and performance under load
   - **Where to find:** arXiv papers, company engineering blogs (e.g., Uber Engineering)

**Collection Strategy for Edge Cases:**
```python
# Allocate 20% of evaluation set to edge cases
edge_case_quota = {
    "ambiguous": 5,
    "controversial": 5,
    "breaking_changes": 3,
    "anti_patterns": 3,
    "niche_tech": 2,
    "very_short": 2,
    "very_long": 5
}
# Total: 25 edge cases in a 100-document evaluation set
```

---

### 3.3 How to Identify Adversarial/Ambiguous Content?

**Adversarial Content:** Content designed to trick or challenge the system.

1. **Fake Technical Content**
   - Satirical articles (e.g., "How to exit vim" jokes)
   - **Why useful:** Tests agent's ability to detect non-serious content
   - **Where to find:** Reddit r/ProgrammerHumor, Dev.to (April Fools' posts)

2. **Contradictory Information**
   - Two sources with conflicting advice (e.g., "Always use Redux" vs "Avoid Redux")
   - **Why useful:** Tests agent's ability to acknowledge multiple perspectives
   - **Where to find:** Pair Stack Overflow answers with different approaches

3. **Misleading Titles**
   - Clickbait (e.g., "This One Trick Solves All React Performance Issues")
   - **Why useful:** Tests agent's ability to assess content quality vs title
   - **Where to find:** Medium articles (some are clickbait), Dev.to

4. **Outdated but Popular Content**
   - Highly-upvoted old content (e.g., "Angular 2 Guide" from 2016)
   - **Why useful:** Tests agent's awareness of version/date
   - **Where to find:** Stack Overflow (sort by votes, filter old dates)

5. **Code-Heavy with Minimal Explanation**
   - GitHub gists with no comments, Stack Overflow code-only answers
   - **Why useful:** Tests agent's ability to infer intent from code alone
   - **Where to find:** GitHub Gists, Stack Overflow "code dump" answers

**Collection Strategy:**
```python
# Allocate 10% of evaluation set to adversarial content
adversarial_quota = {
    "fake_content": 2,
    "contradictory": 3,
    "misleading_titles": 2,
    "outdated": 2,
    "code_heavy": 3
}
# Total: 12 adversarial examples in a 100-document evaluation set
```

---

### 3.4 How to Ensure Diversity?

**Diversity Dimensions:**

1. **Geographic Diversity**
   - Include non-US sources (EU, Asia, Africa, LATAM)
   - **Why:** Different coding conventions, frameworks popular in specific regions
   - **Example:** Dev.to authors from India, China, Brazil

2. **Company Size Diversity**
   - Mix of FAANG (Google, Meta), startups (Vercel, Supabase), solo devs
   - **Why:** Different scale considerations, resource constraints
   - **Example:** AWS blog (enterprise) + indie dev blog (small scale)

3. **Technology Maturity**
   - Mix of established (React, PostgreSQL) and emerging (Bun, Deno)
   - **Why:** Tests agent's adaptability to new technologies
   - **Example:** React docs (mature) + Deno blog (emerging)

4. **Problem Domains**
   - CRUD apps, real-time systems, batch processing, ML pipelines
   - **Why:** Different architectural patterns
   - **Example:** "Building a chat app" vs "Optimizing batch jobs"

5. **Tone and Style**
   - Formal (academic papers) vs casual (Dev.to tutorials)
   - **Why:** Tests agent's ability to parse different writing styles
   - **Example:** arXiv paper + freeCodeCamp tutorial

**Diversity Scorecard (Target for 100-doc evaluation set):**

| Dimension | Target Distribution | Monitoring Metric |
|-----------|---------------------|-------------------|
| **Source Type** | 40% official docs, 30% community (SO, GitHub), 20% blogs, 10% papers | Count by source |
| **Domain** | 25% frontend, 25% backend, 20% AI/ML, 15% DevOps, 15% other | Count by tags |
| **Difficulty** | 20% beginner, 50% intermediate, 25% advanced, 5% expert | Manual labeling |
| **Content Type** | 40% tutorial, 20% comparison, 15% troubleshooting, 15% architecture, 10% other | Manual labeling |
| **Language/Framework** | Max 20% per language (e.g., no more than 20 Python articles) | Count by tags |
| **Geography** | 60% US/EU, 30% Asia, 10% other | Author location (if available) |
| **Publish Date** | 50% last year, 30% 1-2 years old, 20% 2-3 years old | Date field |

**Quality Control Checklist:**
- [ ] Run diversity report after collecting each batch of 20 documents
- [ ] Flag over-represented categories (e.g., 30% React docs → diversify)
- [ ] Actively search for under-represented categories (e.g., only 5% mobile → add 5 more)

---

## 4. Source Prioritization Matrix

### 4.1 ROI Calculation

**Formula:**
```
ROI = (Quality Score × Quantity Score) / Effort Score

Quality Score: 1-10 (10 = gold standard, 1 = low quality)
Quantity Score: 1-10 (10 = 100k+ docs, 1 = <100 docs)
Effort Score: 1-10 (10 = very hard, 1 = very easy)
```

### 4.2 Priority Matrix

| Rank | Source | Quality | Quantity | Effort | ROI | Priority |
|------|--------|---------|----------|--------|-----|----------|
| 1 | **GitHub READMEs** | 8 | 10 | 2 | **40.0** | IMMEDIATE |
| 2 | **Stack Overflow** | 9 | 10 | 3 | **30.0** | IMMEDIATE |
| 3 | **Official Docs** | 10 | 4 | 6 | **6.7** | IMMEDIATE |
| 4 | **arXiv Papers** | 10 | 8 | 7 | **11.4** | HIGH |
| 5 | **Company Blogs** | 9 | 5 | 3 | **15.0** | HIGH |
| 6 | **Hacker News** | 7 | 8 | 2 | **28.0** | HIGH |
| 7 | **YouTube** | 7 | 7 | 6 | **8.2** | MEDIUM |
| 8 | **Dev.to** | 6 | 8 | 2 | **24.0** | MEDIUM |
| 9 | **Reddit** | 5 | 7 | 5 | **7.0** | LOW |

**Immediate Action (Week 1):**
1. GitHub READMEs (easy, high ROI)
2. Stack Overflow Q&A (easy, high ROI)
3. Official Docs (manual but essential)

**High Priority (Week 2-3):**
4. arXiv Papers (expert-level content)
5. Company Blogs (production patterns)
6. Hacker News (trending topics)

**Medium Priority (Week 4):**
7. YouTube Transcripts (multimedia content)
8. Dev.to (community content)

**Low Priority (Future):**
9. Reddit (noisy, quality filtering required)

---

### 4.3 Recommended First 100 Documents

**Distribution by Source:**
- 30 documents: GitHub READMEs (high-quality repos)
- 25 documents: Stack Overflow Q&A (accepted answers, 10+ votes)
- 15 documents: Official Framework Docs (React, FastAPI, LangChain, Next.js, PostgreSQL)
- 10 documents: arXiv CS Papers (last 2 years, cs.AI, cs.SE)
- 10 documents: Company Blogs (Cloudflare, Vercel, AWS, Supabase)
- 5 documents: Hacker News (Ask HN, Show HN)
- 5 documents: YouTube Transcripts (Fireship, freeCodeCamp)

**Total: 100 documents**

**Domain Coverage:**
- Frontend: 25 docs (React 15, Next.js 5, TypeScript 5)
- Backend: 25 docs (FastAPI 15, GraphQL 5, REST 5)
- AI/ML: 20 docs (LangChain 10, RAG 5, Embeddings 5)
- Databases: 10 docs (PostgreSQL 7, Vector DBs 3)
- DevOps: 10 docs (Docker 5, Kubernetes 5)
- Security: 10 docs (OAuth2 5, JWT 5)

**Difficulty:**
- Beginner: 20 docs
- Intermediate: 50 docs
- Advanced: 25 docs
- Expert: 5 docs

---

## 5. Implementation Roadmap

### Phase 1: Foundation (Week 1)

**Goal:** Collect 40 high-quality documents from easiest sources

**Tasks:**
1. **GitHub READMEs** (2 days)
   - [ ] Set up GitHub API authentication
   - [ ] Create script to fetch READMEs by topic and stars
   - [ ] Filter by license (MIT, Apache 2.0, BSD)
   - [ ] Target: 20 READMEs (React 10, FastAPI 5, LangChain 5)

2. **Stack Overflow** (2 days)
   - [ ] Set up Stack Exchange API authentication
   - [ ] Create script to fetch Q&A by tag and score
   - [ ] Filter: accepted answer, 10+ votes, code blocks
   - [ ] Target: 20 Q&A pairs (Python 10, JavaScript 5, PostgreSQL 5)

**Deliverables:**
- [ ] `backend/tests/smoke/retrieval/fixtures/phase1_documents.json` (40 docs)
- [ ] Collection scripts in `backend/scripts/data_collection/`
- [ ] License compliance documentation

---

### Phase 2: Quality Expansion (Week 2)

**Goal:** Add 30 expert-level documents from curated sources

**Tasks:**
1. **Official Framework Docs** (3 days)
   - [ ] Manually collect 15 tutorial pages
   - [ ] React docs: Hooks, Server Components, Suspense
   - [ ] FastAPI docs: Async, OAuth2, Testing
   - [ ] LangChain docs: Agents, Tools, Memory

2. **arXiv Papers** (2 days)
   - [ ] Set up arXiv API with rate limiting
   - [ ] Create script to search cs.AI, cs.SE categories
   - [ ] Extract abstracts and introduction sections
   - [ ] Target: 10 papers (RAG 5, LLM agents 5)

3. **Company Blogs** (2 days)
   - [ ] Set up RSS feed readers
   - [ ] Manually curate 5 articles from Cloudflare, Vercel, AWS
   - [ ] Focus: Architecture, performance, case studies

**Deliverables:**
- [ ] `backend/tests/smoke/retrieval/fixtures/phase2_documents.json` (30 docs)
- [ ] Updated collection scripts
- [ ] Quality scoring rubric (0-10 scale)

---

### Phase 3: Diversity & Edge Cases (Week 3)

**Goal:** Add 30 documents covering gaps and edge cases

**Tasks:**
1. **Domain Gaps** (2 days)
   - [ ] Security: 10 docs (OAuth2, JWT, OWASP)
   - [ ] DevOps: 10 docs (Docker, K8s, CI/CD)
   - [ ] Source: Stack Overflow, GitHub, official docs

2. **Edge Cases** (2 days)
   - [ ] Ambiguous content: 5 docs (multi-domain tutorials)
   - [ ] Very short: 2 docs (GitHub badges, one-liners)
   - [ ] Very long: 3 docs (10k+ word deep dives)

3. **Adversarial Content** (1 day)
   - [ ] Outdated: 2 docs (Angular 2 guides from 2016)
   - [ ] Contradictory: 3 docs (React class vs hooks debates)
   - [ ] Misleading titles: 2 docs (clickbait)

**Deliverables:**
- [ ] `backend/tests/smoke/retrieval/fixtures/phase3_documents.json` (30 docs)
- [ ] Edge case annotations (JSON metadata field: `edge_case_type`)
- [ ] Adversarial test suite documentation

---

### Phase 4: Validation & Metrics (Week 4)

**Goal:** Validate collection, generate baseline metrics

**Tasks:**
1. **Diversity Audit** (1 day)
   - [ ] Run diversity scorecard on all 100 documents
   - [ ] Identify over/under-represented categories
   - [ ] Fill gaps if needed

2. **Quality Review** (2 days)
   - [ ] Manually review 20% of documents (stratified sample)
   - [ ] Score on 10-point scale (clarity, relevance, freshness)
   - [ ] Flag low-quality docs for replacement

3. **Baseline Metrics** (2 days)
   - [ ] Run retrieval smoke tests on 100 documents
   - [ ] Measure Recall@5, MRR, NDCG@10
   - [ ] Document baseline performance (target: Recall@5 ≥0.70)

**Deliverables:**
- [ ] `backend/tests/smoke/retrieval/fixtures/real_data_v1.0.json` (100 docs)
- [ ] Diversity report (`docs/issues/224-real-data-collection/DIVERSITY_REPORT.md`)
- [ ] Baseline metrics report (`docs/issues/224-real-data-collection/BASELINE_METRICS.md`)

---

### Ongoing Maintenance

**Quarterly Updates (Every 3 months):**
- [ ] Refresh 10% of documents (remove outdated, add new)
- [ ] Add emerging technologies (new frameworks, tools)
- [ ] Re-run diversity audit and adjust

**Expansion Targets:**
- 100 docs → 200 docs (6 months)
- 200 docs → 500 docs (12 months)
- Add non-English content (if multilingual support added)

---

## Appendix: API Details & Code Examples

### A1. GitHub API Example

```python
# backend/scripts/data_collection/github_collector.py

import os
import time
from github import Github
from typing import List, Dict

# Authentication
g = Github(os.getenv("GITHUB_TOKEN"))

def collect_readmes(topic: str, min_stars: int = 1000, max_results: int = 10) -> List[Dict]:
    """Collect high-quality READMEs by topic."""

    repos = g.search_repositories(
        query=f"topic:{topic} stars:>={min_stars}",
        sort="stars",
        order="desc"
    )

    results = []
    for repo in repos[:max_results]:
        # Check license
        if repo.license and repo.license.spdx_id in ["MIT", "Apache-2.0", "BSD-3-Clause"]:
            try:
                readme = repo.get_readme().decoded_content.decode("utf-8")

                results.append({
                    "id": f"github-{repo.full_name}",
                    "title": repo.full_name,
                    "content": readme,
                    "source": "github",
                    "url": repo.html_url,
                    "license": repo.license.spdx_id,
                    "stars": repo.stargazers_count,
                    "tags": [topic] + list(repo.get_topics()[:5]),
                    "date": repo.updated_at.isoformat()
                })

                # Respect rate limits (5000/hour = ~1.4 req/sec)
                time.sleep(1)

            except Exception as e:
                print(f"Error fetching README for {repo.full_name}: {e}")

    return results

# Example usage
if __name__ == "__main__":
    topics = ["fastapi", "react", "langchain"]

    for topic in topics:
        docs = collect_readmes(topic, min_stars=1000, max_results=5)
        print(f"Collected {len(docs)} READMEs for topic '{topic}'")
```

---

### A2. Stack Overflow API Example

```python
# backend/scripts/data_collection/stackoverflow_collector.py

import os
import time
from stackapi import StackAPI
from typing import List, Dict

# Initialize Stack Overflow API
SITE = StackAPI("stackoverflow")
SITE.key = os.getenv("STACK_OVERFLOW_KEY")  # Optional, increases rate limit

def collect_qa(tag: str, min_score: int = 10, max_results: int = 10) -> List[Dict]:
    """Collect high-quality Q&A by tag."""

    questions = SITE.fetch(
        "questions",
        tagged=tag,
        sort="votes",
        order="desc",
        filter="withbody",
        max_pages=1,
        pagesize=max_results
    )

    results = []
    for q in questions["items"]:
        # Only include questions with accepted answers
        if q.get("accepted_answer_id"):
            # Fetch accepted answer
            answers = SITE.fetch(
                "answers",
                ids=[q["accepted_answer_id"]],
                filter="withbody"
            )

            if answers["items"]:
                answer = answers["items"][0]

                results.append({
                    "id": f"so-{q['question_id']}",
                    "title": q["title"],
                    "question": q["body"],
                    "answer": answer["body"],
                    "source": "stackoverflow",
                    "url": q["link"],
                    "license": "CC BY-SA 4.0",
                    "score": q["score"],
                    "tags": q["tags"],
                    "date": time.strftime("%Y-%m-%d", time.localtime(q["creation_date"]))
                })

                # Respect rate limits (10k/day = ~7 req/min)
                time.sleep(10)

    return results

# Example usage
if __name__ == "__main__":
    tags = ["fastapi", "react-hooks", "postgresql"]

    for tag in tags:
        docs = collect_qa(tag, min_score=10, max_results=5)
        print(f"Collected {len(docs)} Q&A pairs for tag '{tag}'")
```

---

### A3. arXiv API Example

```python
# backend/scripts/data_collection/arxiv_collector.py

import os
import time
import arxiv
from typing import List, Dict

def collect_papers(category: str, search_query: str, max_results: int = 10) -> List[Dict]:
    """Collect recent CS papers from arXiv."""

    # Search papers
    search = arxiv.Search(
        query=f"cat:{category} AND {search_query}",
        max_results=max_results,
        sort_by=arxiv.SortCriterion.SubmittedDate,
        sort_order=arxiv.SortOrder.Descending
    )

    results = []
    for paper in search.results():
        results.append({
            "id": f"arxiv-{paper.entry_id.split('/')[-1]}",
            "title": paper.title,
            "abstract": paper.summary,
            "content": paper.summary,  # Could download PDF and extract full text
            "source": "arxiv",
            "url": paper.entry_id,
            "license": "arXiv-default",  # Most papers use default arXiv license
            "authors": [author.name for author in paper.authors],
            "tags": paper.categories,
            "date": paper.published.strftime("%Y-%m-%d")
        })

        # Respect rate limits (1 request per 3 seconds)
        time.sleep(3)

    return results

# Example usage
if __name__ == "__main__":
    categories = ["cs.AI", "cs.SE", "cs.LG"]
    queries = ["LLM agent", "RAG retrieval", "vector database"]

    for category in categories:
        for query in queries:
            docs = collect_papers(category, query, max_results=3)
            print(f"Collected {len(docs)} papers for {category} + '{query}'")
```

---

### A4. Hacker News API Example

```python
# backend/scripts/data_collection/hackernews_collector.py

import requests
import time
from typing import List, Dict

HN_API_BASE = "https://hacker-news.firebaseio.com/v0"

def collect_top_stories(min_score: int = 100, max_results: int = 10) -> List[Dict]:
    """Collect top Hacker News stories."""

    # Fetch top story IDs
    response = requests.get(f"{HN_API_BASE}/topstories.json")
    story_ids = response.json()[:max_results * 2]  # Over-fetch to filter by score

    results = []
    for story_id in story_ids:
        # Fetch story details
        response = requests.get(f"{HN_API_BASE}/item/{story_id}.json")
        story = response.json()

        if story and story.get("score", 0) >= min_score and story.get("type") == "story":
            # Fetch top comment (for context)
            top_comment = None
            if story.get("kids"):
                comment_response = requests.get(f"{HN_API_BASE}/item/{story['kids'][0]}.json")
                top_comment = comment_response.json()

            results.append({
                "id": f"hn-{story_id}",
                "title": story.get("title", ""),
                "url": story.get("url", f"https://news.ycombinator.com/item?id={story_id}"),
                "text": story.get("text", ""),
                "top_comment": top_comment.get("text", "") if top_comment else "",
                "source": "hackernews",
                "score": story.get("score", 0),
                "date": time.strftime("%Y-%m-%d", time.localtime(story.get("time", 0)))
            })

            if len(results) >= max_results:
                break

        # No rate limit, but be respectful
        time.sleep(0.5)

    return results

# Example usage
if __name__ == "__main__":
    docs = collect_top_stories(min_score=100, max_results=10)
    print(f"Collected {len(docs)} HN stories")
```

---

### A5. YouTube Transcript Example

```python
# backend/scripts/data_collection/youtube_collector.py

from youtube_transcript_api import YouTubeTranscriptApi
from googleapiclient.discovery import build
import os
from typing import List, Dict

# YouTube API
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)

def collect_video_transcripts(channel_id: str, max_results: int = 5) -> List[Dict]:
    """Collect transcripts from educational YouTube channels."""

    # Search channel for popular videos
    search_response = youtube.search().list(
        channelId=channel_id,
        part="id,snippet",
        order="viewCount",
        type="video",
        maxResults=max_results
    ).execute()

    results = []
    for item in search_response["items"]:
        video_id = item["id"]["videoId"]

        try:
            # Fetch transcript
            transcript = YouTubeTranscriptApi.get_transcript(video_id)

            # Combine transcript segments
            full_text = " ".join([segment["text"] for segment in transcript])

            results.append({
                "id": f"youtube-{video_id}",
                "title": item["snippet"]["title"],
                "content": full_text,
                "transcript": transcript,  # Keep timestamps for reference
                "source": "youtube",
                "url": f"https://www.youtube.com/watch?v={video_id}",
                "channel": item["snippet"]["channelTitle"],
                "date": item["snippet"]["publishedAt"][:10]
            })

        except Exception as e:
            print(f"Could not fetch transcript for {video_id}: {e}")

    return results

# Example usage
if __name__ == "__main__":
    channels = {
        "Fireship": "UCsBjURrPoezykLs9EqgamOA",
        "freeCodeCamp": "UC8butISFwT-Wl7EV0hUK0BQ"
    }

    for name, channel_id in channels.items():
        docs = collect_video_transcripts(channel_id, max_results=3)
        print(f"Collected {len(docs)} transcripts from {name}")
```

---

## Summary & Next Steps

### Key Takeaways

1. **Top 3 Sources for Immediate Collection:**
   - GitHub READMEs (40.0 ROI)
   - Stack Overflow Q&A (30.0 ROI)
   - Official Framework Docs (6.7 ROI, but essential)

2. **Target First 100 Documents:**
   - 30 GitHub READMEs
   - 25 Stack Overflow Q&A
   - 15 Official Docs
   - 10 arXiv Papers
   - 10 Company Blogs
   - 10 Mixed (HN, YouTube, Dev.to)

3. **Critical Success Factors:**
   - License compliance (check every source)
   - Diversity across domains, difficulty, and content types
   - Edge cases and adversarial examples (30% of set)
   - Quality over quantity (gold > bronze)

### Immediate Action Items

**Week 1:**
- [ ] Set up GitHub API authentication
- [ ] Set up Stack Exchange API authentication
- [ ] Create collection scripts (use code examples in Appendix)
- [ ] Collect first 40 documents (20 GitHub + 20 Stack Overflow)

**Week 2:**
- [ ] Manually curate 15 official docs
- [ ] Set up arXiv API and collect 10 papers
- [ ] Add 5 company blog posts

**Week 3:**
- [ ] Fill domain gaps (security, DevOps)
- [ ] Add edge cases and adversarial examples

**Week 4:**
- [ ] Run diversity audit
- [ ] Generate baseline metrics
- [ ] Document findings

### Success Metrics

- **Quantity:** 100 real-world documents by end of Week 4
- **Diversity:** ≥80% scorecard compliance (see Section 3.4)
- **Quality:** ≥70% gold/silver tier (see Section 2.4)
- **Performance:** Retrieval metrics ≥ current synthetic fixtures (Recall@5 ≥0.70)

---

## Sources

- [GitHub API Rate Limits](https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api)
- [Updated rate limits for unauthenticated requests - GitHub Changelog](https://github.blog/changelog/2025-05-08-updated-rate-limits-for-unauthenticated-requests/)
- [Stack Overflow Data Licensing](https://stackoverflow.co/data-licensing/)
- [Best practices for third-party data acquisition - Stack Overflow](https://stackoverflow.blog/2025/05/08/best-practices-third-party-data-acquisition-powering-ai-context/)
- [arXiv API Access](https://info.arxiv.org/help/api/index.html)
- [Terms of Use for arXiv APIs](https://info.arxiv.org/help/api/tou.html)
- [License and copyright - arXiv](https://info.arxiv.org/help/license/index.html)
- [YouTube Transcript APIs](https://pypi.org/project/youtube-transcript-api/)
- [Best YouTube Transcript APIs in 2025](https://dev.to/geiger01/best-youtube-transcript-apis-in-2025-45d6)
- [Hacker News API](https://github.com/HackerNews/API)
- [Exploring the Hacker News API: A Guide for Developers](https://www.devzery.com/post/exploring-the-hacker-news-api-a-guide-for-developers)

---

**Document Version:** 1.0
**Author:** UX Researcher Agent
**Review Status:** Ready for Engineering Review
**Next Review Date:** January 10, 2026
