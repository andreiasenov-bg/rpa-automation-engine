"""
Workflow Storage Service — manages per-workflow folder structure.

Each workflow gets its own organized folder:
  /storage/workflows/{workflow_slug}/
    ├── results/       # Execution results (XLSX, CSV, JSON)
    ├── icons/         # Workflow icon / thumbnail
    ├── screenshots/   # Step screenshots during execution
    ├── docs/          # Documentation, explanations
    ├── config/        # Exported configurations
    ├── logs/          # Execution log exports
    └── README.md      # Auto-generated workflow description
"""

import os
import re
import json
import shutil
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

from app.config import get_settings

logger = logging.getLogger(__name__)

# Subdirectories every workflow folder gets
WORKFLOW_SUBDIRS = [
    "results",
    "icons",
    "screenshots",
    "docs",
    "config",
    "logs",
]


def _slugify(name: str) -> str:
    """Convert workflow name to a filesystem-safe slug."""
    # Transliterate common chars, lowercase, replace non-alphanum with hyphen
    slug = name.lower().strip()
    slug = re.sub(r'[äöüß]', lambda m: {'ä': 'ae', 'ö': 'oe', 'ü': 'ue', 'ß': 'ss'}.get(m.group(), m.group()), slug)
    slug = re.sub(r'[^a-z0-9]+', '-', slug)
    slug = slug.strip('-')
    return slug[:80] or 'unnamed'


class WorkflowStorageService:
    """Manages filesystem storage for workflow assets."""

    def __init__(self):
        settings = get_settings()
        self.base_path = Path(settings.STORAGE_PATH).resolve()
        self.workflows_path = self.base_path / "workflows"

    def _ensure_base(self):
        """Create base storage directories if missing."""
        self.workflows_path.mkdir(parents=True, exist_ok=True)

    def get_workflow_dir(self, workflow_id: str, workflow_name: str = "") -> Path:
        """
        Get the folder path for a workflow.
        Uses {slug}_{short_id} to be human-readable AND unique.
        """
        short_id = workflow_id[:8]
        slug = _slugify(workflow_name) if workflow_name else "workflow"
        folder_name = f"{slug}_{short_id}"
        return self.workflows_path / folder_name

    def find_workflow_dir(self, workflow_id: str) -> Optional[Path]:
        """Find existing workflow folder by its ID suffix."""
        short_id = workflow_id[:8]
        if not self.workflows_path.exists():
            return None
        for entry in self.workflows_path.iterdir():
            if entry.is_dir() and entry.name.endswith(f"_{short_id}"):
                return entry
        return None

    def init_workflow_folder(self, workflow_id: str, workflow_name: str, description: str = "") -> Path:
        """
        Create the full folder structure for a workflow.
        Returns the workflow directory path.
        """
        self._ensure_base()
        wf_dir = self.get_workflow_dir(workflow_id, workflow_name)

        # If folder already exists (e.g. from previous creation), skip
        if wf_dir.exists():
            logger.info(f"Workflow folder already exists: {wf_dir}")
            return wf_dir

        # Create main dir and all subdirs
        wf_dir.mkdir(parents=True, exist_ok=True)
        for subdir in WORKFLOW_SUBDIRS:
            (wf_dir / subdir).mkdir(exist_ok=True)

        # Create README.md with workflow info
        readme_content = f"""# {workflow_name}

{description or 'No description provided.'}

---

**Workflow ID:** `{workflow_id}`
**Created:** {datetime.now().strftime('%Y-%m-%d %H:%M')}

## Folder Structure

| Folder | Contents |
|--------|----------|
| `results/` | Execution results — XLSX, CSV, JSON exports |
| `icons/` | Workflow icon and thumbnails |
| `screenshots/` | Execution screenshots |
| `docs/` | Documentation and explanations |
| `config/` | Configuration exports |
| `logs/` | Execution log files |
"""
        (wf_dir / "README.md").write_text(readme_content, encoding="utf-8")

        logger.info(f"Initialized workflow folder: {wf_dir}")
        return wf_dir

    def rename_workflow_folder(self, workflow_id: str, new_name: str) -> Optional[Path]:
        """Rename workflow folder when the workflow name changes."""
        existing = self.find_workflow_dir(workflow_id)
        if not existing:
            return None

        new_dir = self.get_workflow_dir(workflow_id, new_name)
        if existing == new_dir:
            return existing  # No change needed

        if new_dir.exists():
            logger.warning(f"Cannot rename, target exists: {new_dir}")
            return existing

        existing.rename(new_dir)
        logger.info(f"Renamed workflow folder: {existing.name} → {new_dir.name}")
        return new_dir

    def save_execution_result(
        self,
        workflow_id: str,
        execution_id: str,
        data: dict,
        format: str = "json",
    ) -> Optional[Path]:
        """
        Save execution results to the workflow's results/ folder.
        REPLACE mode: clears old results and saves only the latest as latest_results.json.
        """
        wf_dir = self.find_workflow_dir(workflow_id)
        if not wf_dir:
            return None

        results_dir = wf_dir / "results"
        results_dir.mkdir(exist_ok=True)

        # ── Replace mode: delete all old result files ──
        for old_file in results_dir.iterdir():
            if old_file.is_file():
                old_file.unlink()
                logger.debug(f"Deleted old result: {old_file.name}")

        # ── Save as fixed name for easy access ──
        filepath = results_dir / "latest_results.json"

        # Build a clean result envelope with metadata
        result_envelope = {
            "execution_id": execution_id,
            "saved_at": datetime.now().isoformat(),
            "data": data,
        }

        filepath.write_text(
            json.dumps(result_envelope, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        logger.info(f"Saved latest execution result: {filepath} (replaced old files)")
        return filepath

    def _find_latest_result_file(self, wf_dir: Path) -> Optional[Path]:
        """Find the latest results file — prefers latest_results.json, falls back to newest .json."""
        results_dir = wf_dir / "results"
        if not results_dir.exists():
            return None
        # Prefer canonical name
        canonical = results_dir / "latest_results.json"
        if canonical.exists():
            return canonical
        # Fallback: find newest JSON file in results/
        json_files = sorted(results_dir.glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True)
        return json_files[0] if json_files else None

    def get_latest_results(self, workflow_id: str) -> Optional[dict]:
        """Read the latest results JSON for a workflow. Returns parsed dict or None."""
        wf_dir = self.find_workflow_dir(workflow_id)
        if not wf_dir:
            return None
        filepath = self._find_latest_result_file(wf_dir)
        if not filepath:
            return None
        try:
            return json.loads(filepath.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning(f"Failed to read latest results: {e}")
            return None

    def get_latest_results_path(self, workflow_id: str) -> Optional[Path]:
        """Get the path to the latest results file for direct download."""
        wf_dir = self.find_workflow_dir(workflow_id)
        if not wf_dir:
            return None
        filepath = self._find_latest_result_file(wf_dir)
        return filepath if filepath.exists() else None

    def save_execution_log(self, workflow_id: str, execution_id: str, log_text: str) -> Optional[Path]:
        """Save execution logs to the workflow's logs/ folder."""
        wf_dir = self.find_workflow_dir(workflow_id)
        if not wf_dir:
            return None

        logs_dir = wf_dir / "logs"
        logs_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        short_exec = execution_id[:8]
        filename = f"log_{short_exec}_{timestamp}.txt"
        filepath = logs_dir / filename
        filepath.write_text(log_text, encoding="utf-8")
        logger.info(f"Saved execution log: {filepath}")
        return filepath

    def list_workflow_files(self, workflow_id: str) -> dict:
        """
        List all files in a workflow's folder, organized by subfolder.
        Returns: { "results": [...], "icons": [...], "docs": [...], ... }
        """
        wf_dir = self.find_workflow_dir(workflow_id)
        if not wf_dir:
            return {}

        result = {}
        for subdir in WORKFLOW_SUBDIRS:
            subdir_path = wf_dir / subdir
            if subdir_path.exists():
                files = []
                for f in sorted(subdir_path.iterdir()):
                    if f.is_file():
                        stat = f.stat()
                        files.append({
                            "name": f.name,
                            "size": stat.st_size,
                            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                            "path": str(f.relative_to(self.base_path)),
                        })
                result[subdir] = files

        # Also include root files (README.md, etc.)
        root_files = []
        for f in sorted(wf_dir.iterdir()):
            if f.is_file():
                stat = f.stat()
                root_files.append({
                    "name": f.name,
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "path": str(f.relative_to(self.base_path)),
                })
        if root_files:
            result["root"] = root_files

        return result

    def get_file_path(self, relative_path: str) -> Optional[Path]:
        """
        Resolve a relative storage path to absolute, with safety checks.
        Prevents directory traversal attacks.
        """
        target = (self.base_path / relative_path).resolve()
        # Ensure the resolved path is within base_path
        if not str(target).startswith(str(self.base_path)):
            logger.warning(f"Path traversal attempt: {relative_path}")
            return None
        if not target.exists() or not target.is_file():
            return None
        return target

    def delete_workflow_folder(self, workflow_id: str) -> bool:
        """Delete the entire workflow folder (soft-delete: rename with .deleted suffix)."""
        wf_dir = self.find_workflow_dir(workflow_id)
        if not wf_dir:
            return False

        deleted_name = f"{wf_dir.name}.deleted_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        wf_dir.rename(wf_dir.parent / deleted_name)
        logger.info(f"Soft-deleted workflow folder: {wf_dir.name} → {deleted_name}")
        return True

    def get_storage_stats(self) -> dict:
        """Get overall storage statistics."""
        if not self.workflows_path.exists():
            return {"total_workflows": 0, "total_size_mb": 0}

        total_size = 0
        workflow_count = 0
        for entry in self.workflows_path.iterdir():
            if entry.is_dir() and not entry.name.endswith('.deleted'):
                workflow_count += 1
                for f in entry.rglob("*"):
                    if f.is_file():
                        total_size += f.stat().st_size

        return {
            "total_workflows": workflow_count,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
        }


# Singleton instance
_storage_service: Optional[WorkflowStorageService] = None


def get_storage_service() -> WorkflowStorageService:
    """Get or create the storage service singleton."""
    global _storage_service
    if _storage_service is None:
        _storage_service = WorkflowStorageService()
    return _storage_service
