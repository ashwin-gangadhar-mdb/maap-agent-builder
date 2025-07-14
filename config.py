# Config loader for MAAP Agent Builder
import yaml
from pydantic import BaseModel
from typing import Any, Optional, List, Union, Dict, Literal, Tuple


class CheckpointerConfig(BaseModel):
    connection_str: str
    db_name: Optional[str] = "langgraph"
    collection_name: Optional[str] = "checkpoints"
    name: Optional[str] = "mongodb_checkpointer"
