import os
from pathlib import Path
from typing import Optional
from logger_config import LogConfig

# Setup logging
log_config = LogConfig()
logger = log_config.get_logger("path_resolver")


class PathResolver:
    """Utility class for resolving file paths in the project"""

    @staticmethod
    def get_project_root() -> Path:
        """Get the project root directory"""
        # Start from the current file's directory
        current_dir = Path(__file__).resolve().parent

        # Go up the directory tree until we find a marker file/directory
        # You can adjust these markers based on your project structure
        root_markers = [
            'requirements.txt',
            'setup.py',
            '.git',
            'README.md',
            'break_even_template.xlsx'  # Add your template as a marker
        ]

        while current_dir != current_dir.parent:
            if any((current_dir / marker).exists() for marker in root_markers):
                return current_dir
            current_dir = current_dir.parent

        # If we couldn't find the root, return the current working directory
        return Path.cwd()

    @classmethod
    def resolve_template_path(cls, template_name: str) -> Path:
        """
        Resolve the template path by checking multiple locations

        Args:
            template_name: Name of the template file

        Returns:
            Path: Resolved path to the template

        Raises:
            FileNotFoundError: If template cannot be found
        """
        # Get the project root
        project_root = cls.get_project_root()

        # List of possible locations to check
        search_paths = [
            project_root / template_name,  # Project root
            project_root / 'templates' / template_name,  # Templates directory
            project_root / 'data' / template_name,  # Data directory
            project_root / 'resources' / template_name,  # Resources directory
            Path.cwd() / template_name,  # Current working directory
        ]

        # Log the search process
        logger.debug(f"Searching for template '{template_name}' in:")
        for path in search_paths:
            logger.debug(f"  - {path}")
            if path.exists():
                logger.info(f"Found template at: {path}")
                return path

        # If we get here, we couldn't find the template
        error_msg = f"Template '{template_name}' not found. Searched in:\n"
        error_msg += "\n".join(f"  - {path}" for path in search_paths)
        logger.error(error_msg)
        raise FileNotFoundError(error_msg)


# Usage example:
if __name__ == "__main__":
    try:
        template_path = PathResolver.resolve_template_path('break_even_template.xlsx')
        print(f"Found template at: {template_path}")
    except FileNotFoundError as e:
        print(e)
