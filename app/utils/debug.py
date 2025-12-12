"""Debug utilities for saving intermediate pipeline data."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from app.utils.logging import get_logger

logger = get_logger(__name__)

# Debug output directory
DEBUG_OUTPUT_DIR = Path(".debug")


def save_debug_data(
    project_id: str,
    stage: str,
    data: dict[str, Any],
    pretty: bool = True,
) -> Path:
    """Save debug data to a local file.
    
    Args:
        project_id: The project ID
        stage: The pipeline stage (e.g., "pre_code_gen", "spec_analysis")
        data: The data to save
        pretty: Whether to pretty-print the JSON
        
    Returns:
        Path to the saved file
    """
    # Create debug directory if it doesn't exist
    debug_dir = DEBUG_OUTPUT_DIR / project_id
    debug_dir.mkdir(parents=True, exist_ok=True)
    
    # Create filename with timestamp
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"{stage}_{timestamp}.json"
    filepath = debug_dir / filename
    
    # Save the data
    with open(filepath, "w") as f:
        if pretty:
            json.dump(data, f, indent=2, default=str)
        else:
            json.dump(data, f, default=str)
    
    logger.info(
        "debug.data_saved",
        project_id=project_id,
        stage=stage,
        filepath=str(filepath),
    )
    
    return filepath


def save_pre_codegen_debug(
    project_id: str,
    user_request: dict[str, Any],
    structured_spec: dict[str, Any],
    codegen_options: dict[str, Any],
) -> Path:
    """Save all data before code generation for debugging.
    
    Args:
        project_id: The project ID
        user_request: Original user request data
        structured_spec: The analyzed specification
        codegen_options: Code generation options
        
    Returns:
        Path to the saved file
    """
    data = {
        "project_id": project_id,
        "saved_at": datetime.utcnow().isoformat(),
        "user_request": user_request,
        "structured_spec": structured_spec,
        "codegen_options": codegen_options,
    }
    
    return save_debug_data(project_id, "pre_code_gen", data)
