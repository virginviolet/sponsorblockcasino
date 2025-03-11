# region Imports
# Standard Library
from pathlib import Path
# endregion

# region Get project root
def get_project_root() -> Path:
    """
    Get the project root directory path.
    """
    project_root_marker_files: list[str] = [
        ".gitignore", ".gitattributes", ".git", ".github", ".vscode", "README.md",
        "LICENSE", "requirements.txt"]
    script_path: Path = Path(__file__).resolve()
    script_dir_path: Path = script_path.parent
    script_dir_parents: list[Path] = list(script_dir_path.parents)
    dir_paths_to_check: list[Path] = [script_dir_path] + script_dir_parents
    project_root_path: Path | None = None
    # iterate parents
    for path in dir_paths_to_check:
        for marker_file in project_root_marker_files:
            if (path / marker_file).exists():
                project_root_path = path
                break
        if project_root_path:
            break

    if not project_root_path:
        raise FileNotFoundError("Project root path not found.")
    
    return project_root_path
# endregion