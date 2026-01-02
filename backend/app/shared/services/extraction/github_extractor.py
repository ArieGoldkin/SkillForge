"""GitHub repository content extraction service.

Issue: ROADMAP claims GitHub extractor is implemented, but it's not.
This extractor uses PyGithub to extract README and repository content.
"""

import re

try:
    from github import Github, GithubException
    from github.ContentFile import ContentFile
    from github.Repository import Repository
except ImportError:
    # Fallback if PyGithub is not installed
    Github = None
    GithubException = Exception
    ContentFile = None
    Repository = None

from app.core.config import settings
from app.core.exceptions import ExtractionErrorCode, JinaReaderError
from app.core.logging import get_logger
from app.core.types import ExtractionResult

logger = get_logger(__name__)

# GitHub URL pattern
GITHUB_URL_PATTERN = re.compile(
    r"github\.com/([a-zA-Z0-9](?:[a-zA-Z0-9]|-(?=[a-zA-Z0-9])){0,38})/([a-zA-Z0-9._-]+)(?:/.*)?"
)


def extract_github_repo_info(url: str) -> tuple[str, str] | None:
    """Extract owner and repo name from GitHub URL.

    Args:
        url: GitHub repository URL

    Returns:
        Tuple of (owner, repo_name) or None if not a GitHub repo URL

    Examples:
        >>> extract_github_repo_info("https://github.com/user/repo")
        ("user", "repo")
        >>> extract_github_repo_info("https://github.com/user/repo/blob/main/README.md")
        ("user", "repo")

    """
    match = GITHUB_URL_PATTERN.search(url)
    if match:
        return (match.group(1), match.group(2))
    return None


def is_github_url(url: str) -> bool:
    """Check if URL is a GitHub repository URL.

    Args:
        url: URL to check

    Returns:
        True if URL matches GitHub patterns

    """
    return extract_github_repo_info(url) is not None


class GitHubExtractor:
    """Extracts content from GitHub repositories.

    Uses PyGithub to fetch README and repository information.
    Supports public repositories (no auth required for read access).
    """

    def __init__(self) -> None:
        """Initialize GitHub extractor."""
        if Github is None:
            raise ImportError("PyGithub is not installed. Install it with: poetry add PyGithub")

        # Use GitHub token if available (increases rate limits)
        github_token = getattr(settings, "GITHUB_TOKEN", None)
        self.client = Github(github_token) if github_token else Github()

    async def extract_article(self, url: str) -> ExtractionResult:
        """Extract README and repository content from GitHub URL.

        Args:
            url: GitHub repository URL

        Returns:
            Dictionary with title (repo name), content (README + description),
            word_count, and metadata

        Raises:
            JinaReaderError: If extraction fails

        """
        repo_info = extract_github_repo_info(url)
        if not repo_info:
            error_msg = f"Invalid GitHub URL format: {url}"
            logger.error("github_invalid_url", url=url)
            raise JinaReaderError(error_msg, error_code=ExtractionErrorCode.INVALID_URL)

        owner, repo_name = repo_info

        logger.info(
            "github_extraction_started",
            url=url,
            owner=owner,
            repo_name=repo_name,
        )

        try:
            # Get repository
            repo: Repository = self.client.get_repo(f"{owner}/{repo_name}")

            # Extract repository metadata
            repo_description = repo.description or ""
            repo_full_name = repo.full_name
            repo_url = repo.html_url

            # Try to get README
            readme_content = ""
            try:
                readme_file: ContentFile = repo.get_readme()
                # Decode base64 content
                import base64

                readme_content = base64.b64decode(readme_file.content).decode("utf-8")
                logger.info(
                    "github_readme_found",
                    owner=owner,
                    repo_name=repo_name,
                    readme_length=len(readme_content),
                )
            except GithubException as e:
                if e.status == 404:
                    logger.warning(
                        "github_no_readme",
                        owner=owner,
                        repo_name=repo_name,
                    )
                else:
                    raise

            # Combine description and README
            content_parts = []
            if repo_description:
                content_parts.append(f"# {repo_full_name}\n\n{repo_description}\n")
            if readme_content:
                content_parts.append(readme_content)

            content = "\n\n".join(content_parts)
            if not content:
                # Fallback: just use repo name and URL
                content = f"# {repo_full_name}\n\nGitHub Repository: {repo_url}"

            # Use repo full name as title
            title = repo_full_name

            word_count = len(content.split())

            logger.info(
                "github_extraction_success",
                url=url,
                owner=owner,
                repo_name=repo_name,
                content_length=len(content),
                word_count=word_count,
                has_readme=bool(readme_content),
            )

            return {
                "title": title,
                "content": content,
                "word_count": word_count,
                "metadata": {
                    "extractor": "github_api",
                    "source_url": url,
                    "owner": owner,
                    "repo_name": repo_name,
                    "repo_url": repo_url,
                    "has_readme": bool(readme_content),
                    "raw_content_length": len(content),
                    "cleaned_content_length": len(content),
                },
            }

        except GithubException as e:
            if e.status == 404:
                error_msg = f"Repository not found: {url}"
                logger.error(
                    "github_repo_not_found",
                    url=url,
                    owner=owner,
                    repo_name=repo_name,
                    status_code=e.status,
                )
                raise JinaReaderError(error_msg, error_code=ExtractionErrorCode.HTTP_404) from e

            error_msg = f"GitHub API error ({e.status}): {url}"
            logger.error(
                "github_api_error",
                url=url,
                owner=owner,
                repo_name=repo_name,
                status_code=e.status,
                error=str(e),
            )
            raise JinaReaderError(error_msg, error_code=ExtractionErrorCode.HTTP_5XX) from e

        except Exception as e:
            error_msg = f"GitHub extraction failed for {url}: {type(e).__name__}: {e!s}"
            logger.exception(
                "github_extraction_failed",
                url=url,
                owner=owner,
                repo_name=repo_name,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise JinaReaderError(error_msg) from e

    async def close(self) -> None:
        """Close any resources (GitHub extractor doesn't need cleanup)."""
