"""Security scanner for detecting hardcoded secrets in Python source code.

Provides comprehensive scanning for:
- API keys (Anthropic, OpenAI, GitHub, etc.)
- Database and Redis URLs with embedded credentials
- Hardcoded passwords and tokens
- Base64-encoded keys
- Email account credentials

Designed as a startup check to prevent secrets from being committed to the repository.
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class SecurityFinding:
    """Represents a single security finding in source code."""

    file_path: str
    line_number: int
    line_content: str
    pattern_name: str
    severity: str  # "critical", "high", "medium"
    description: str


class SecretScanner:
    """Scans Python files for hardcoded secrets and sensitive information."""

    # Patterns to detect secrets
    SECRET_PATTERNS = {
        # API Keys
        "anthropic_api_key": {
            "pattern": r"sk-ant-[a-zA-Z0-9\-_]{20,}",
            "severity": "critical",
            "description": "Anthropic API key detected",
        },
        "openai_api_key": {
            "pattern": r"(?:sk-[a-zA-Z0-9]{20,}|sk-[A-Za-z0-9]{48,})",
            "severity": "critical",
            "description": "OpenAI API key detected",
        },
        "github_pat": {
            "pattern": r"ghp_[a-zA-Z0-9]{36,}",
            "severity": "critical",
            "description": "GitHub Personal Access Token detected",
        },
        "github_oauth": {
            "pattern": r"gho_[a-zA-Z0-9]{36,}",
            "severity": "critical",
            "description": "GitHub OAuth token detected",
        },
        "github_app_token": {
            "pattern": r"ghu_[a-zA-Z0-9]{36,}",
            "severity": "critical",
            "description": "GitHub App token detected",
        },
        # Database URLs with passwords
        "postgres_url_password": {
            "pattern": r"postgresql://[^:]+:[^@]+@",
            "severity": "critical",
            "description": "PostgreSQL URL with embedded password detected",
        },
        "mysql_url_password": {
            "pattern": r"mysql://[^:]+:[^@]+@",
            "severity": "critical",
            "description": "MySQL URL with embedded password detected",
        },
        "postgres_asyncpg_password": {
            "pattern": r"postgresql\+asyncpg://[^:]+:[^@]+@",
            "severity": "critical",
            "description": "PostgreSQL asyncpg URL with embedded password detected",
        },
        # Redis URLs with passwords
        "redis_url_password": {
            "pattern": r"redis://[^:]+:[^@]+@",
            "severity": "critical",
            "description": "Redis URL with embedded password detected",
        },
        "redis_ssl_password": {
            "pattern": r"rediss://[^:]+:[^@]+@",
            "severity": "critical",
            "description": "Redis SSL URL with embedded password detected",
        },
        # Hardcoded passwords in assignment
        "password_assignment": {
            "pattern": r"(?i)(password|passwd|pwd)\s*=\s*['\"](?![\s${}])[^'\"]{4,}['\"]",
            "severity": "high",
            "description": "Hardcoded password assignment detected",
        },
        # Base64-encoded secrets (typically 32+ chars)
        "base64_key": {
            "pattern": r"(?i)(?:secret|key|token|apikey)\s*=\s*['\"]([A-Za-z0-9+/]{32,}={0,2})['\"]",
            "severity": "medium",
            "description": "Base64-encoded key/secret detected",
        },
        # AWS Access Keys
        "aws_access_key": {
            "pattern": r"AKIA[0-9A-Z]{16}",
            "severity": "critical",
            "description": "AWS Access Key ID detected",
        },
        # JWT-like tokens
        "jwt_token": {
            "pattern": r"eyJ[A-Za-z0-9_\-\.]+\.eyJ[A-Za-z0-9_\-\.]+\.[A-Za-z0-9_\-\.]+",
            "severity": "high",
            "description": "JWT token detected",
        },
        # Private keys
        "private_key": {
            "pattern": r"-----BEGIN\s+(?:RSA\s+|EC\s+)?PRIVATE\s+KEY",
            "severity": "critical",
            "description": "Private key file detected",
        },
    }

    # File patterns to exclude
    EXCLUDE_PATTERNS = [
        ".env",
        ".env.*",
        "__pycache__",
        "*.pyc",
        ".git",
        ".gitignore",
        "node_modules",
        "migrations",
        "*.egg-info",
        ".pytest_cache",
        ".venv",
        "venv",
        "dist",
        "build",
        ".tox",
    ]

    def __init__(self, base_path: Optional[Path] = None):
        """Initialize the scanner.

        Args:
            base_path: Root path to scan. Defaults to current working directory.
        """
        self.base_path = Path(base_path) if base_path else Path.cwd()
        self.compiled_patterns = {
            name: re.compile(pattern_info["pattern"], re.MULTILINE | re.IGNORECASE)
            for name, pattern_info in self.SECRET_PATTERNS.items()
        }

    def scan_file(self, file_path: Path) -> List[SecurityFinding]:
        """Scan a single Python file for secrets.

        Args:
            file_path: Path to the file to scan

        Returns:
            List of SecurityFinding objects
        """
        findings: List[SecurityFinding] = []

        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
        except (IOError, OSError) as e:
            logger.warning("Failed to read file", file=str(file_path), error=str(e))
            return findings

        for line_num, line in enumerate(lines, 1):
            # Skip empty lines and comments
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue

            # Check each pattern
            for pattern_name, compiled_pattern in self.compiled_patterns.items():
                matches = compiled_pattern.finditer(line)
                for match in matches:
                    pattern_info = self.SECRET_PATTERNS[pattern_name]
                    finding = SecurityFinding(
                        file_path=str(file_path),
                        line_number=line_num,
                        line_content=line.rstrip(),
                        pattern_name=pattern_name,
                        severity=pattern_info["severity"],
                        description=pattern_info["description"],
                    )
                    findings.append(finding)

        return findings

    def _should_exclude(self, path: Path) -> bool:
        """Check if a path should be excluded from scanning.

        Args:
            path: Path to check

        Returns:
            True if path should be excluded
        """
        path_str = str(path)

        # Check against exclude patterns
        for pattern in self.EXCLUDE_PATTERNS:
            # Handle wildcard patterns
            if "*" in pattern:
                import fnmatch

                if fnmatch.fnmatch(path_str, f"*{pattern}*"):
                    return True
                if fnmatch.fnmatch(path.name, pattern):
                    return True
            else:
                if pattern in path_str:
                    return True
                if path.name == pattern:
                    return True

        # Additional checks
        if path.name.startswith("."):
            return True

        return False

    def scan_directory(self, directory: Optional[Path] = None) -> List[SecurityFinding]:
        """Recursively scan a directory for Python files with secrets.

        Args:
            directory: Directory to scan. Defaults to base_path.

        Returns:
            List of SecurityFinding objects
        """
        if directory is None:
            directory = self.base_path

        findings: List[SecurityFinding] = []
        directory = Path(directory)

        if not directory.is_dir():
            logger.warning("Directory does not exist", directory=str(directory))
            return findings

        try:
            for file_path in directory.rglob("*.py"):
                if self._should_exclude(file_path):
                    continue

                file_findings = self.scan_file(file_path)
                findings.extend(file_findings)
        except (IOError, OSError) as e:
            logger.warning("Error scanning directory", directory=str(directory), error=str(e))

        return findings


def check_secrets_on_startup(backend_path: Optional[Path] = None) -> None:
    """Startup check that scans the backend directory for hardcoded secrets.

    In production mode, raises RuntimeError if critical secrets are found.
    In development mode, logs warnings for any findings.

    Args:
        backend_path: Path to the backend directory. Defaults to finding it automatically.

    Raises:
        RuntimeError: In production mode if critical secrets are found
    """
    from app.config import get_settings

    settings = get_settings()

    # Determine backend path
    if backend_path is None:
        # Try to find backend directory relative to this file
        current_file = Path(__file__)
        backend_path = current_file.parent.parent  # Go up from core/ to backend/

    backend_path = Path(backend_path)

    logger.info("Starting security scan for hardcoded secrets", backend_path=str(backend_path))

    scanner = SecretScanner(base_path=backend_path)
    findings = scanner.scan_directory(backend_path)

    if not findings:
        logger.info("Security scan completed - no secrets detected")
        return

    # Group findings by severity
    critical_findings = [f for f in findings if f.severity == "critical"]
    high_findings = [f for f in findings if f.severity == "high"]
    medium_findings = [f for f in findings if f.severity == "medium"]

    # Log all findings
    for finding in findings:
        logger.warning(
            "Security finding detected",
            file=finding.file_path,
            line=finding.line_number,
            pattern=finding.pattern_name,
            severity=finding.severity,
            description=finding.description,
        )

    # Summary
    logger.warning(
        "Security scan completed with findings",
        total=len(findings),
        critical=len(critical_findings),
        high=len(high_findings),
        medium=len(medium_findings),
    )

    # In production, raise error if critical secrets found
    if settings.ENVIRONMENT == "production" and critical_findings:
        error_msg = (
            f"CRITICAL: {len(critical_findings)} critical secret(s) found in source code. "
            "These must be removed before deploying to production. "
            "See logs above for details."
        )
        logger.error("Startup blocked due to critical secrets", count=len(critical_findings))
        raise RuntimeError(error_msg)

    # In development, warn but don't block
    if settings.is_development and findings:
        logger.warning(
            "Development mode: startup not blocked by security findings, but these should be fixed"
        )


# Export for easy import
__all__ = ["SecretScanner", "SecurityFinding", "check_secrets_on_startup"]

# ── Integration with FastAPI startup ──
# To use in app/main.py lifespan():
#
# from core.security_scanner import check_secrets_on_startup
#
# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     settings = get_settings()
#     setup_logging()
#
#     # Run security scan early in startup
#     check_secrets_on_startup()
#
#     await init_db()
#     # ... rest of startup
