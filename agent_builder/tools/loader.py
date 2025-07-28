"""
Tool loader for MDB Agent Builder.

This module provides functionality to load different types of tools
including MongoDB tools, MCP tools, and other LangChain tools.
"""

from typing import Dict, Any, List, Optional, Union
import logging
from dataclasses import dataclass, field
from enum import Enum

from langchain_core.language_models import BaseLLM
from langchain_core.tools import BaseTool

from agent_builder.utils.logging_config import get_logger
from agent_builder.tools.mongodb import MongoDBTools
from agent_builder.tools.mcp import get_mcp_tools

# Set up module logger
logger = get_logger(__name__)

class ToolType(str, Enum):
    """Supported tool types."""
    VECTOR_SEARCH = "vector_search"
    MONGODB_TOOLKIT = "mongodb_toolkit"
    NL_TO_MQL = "nl_to_mql"
    MCP = "mcp"

@dataclass
class ToolConfig:
    """Configuration for tool setup."""
    tool_type: str
    name: str
    description: Optional[str] = None
    connection_str: Optional[str] = None
    namespace: Optional[str] = None
    embedding_model: Optional[Any] = None
    llm: Optional[BaseLLM] = None
    servers_config: Optional[Dict[str, Dict[str, Any]]] = None
    additional_kwargs: Optional[Dict[str, Any]] = field(default_factory=dict)

def load_tool(config: ToolConfig) -> BaseTool:
    """
    Load a tool based on the provided configuration.
    
    Args:
        config: ToolConfig containing tool type and other parameters
        
    Returns:
        An initialized LangChain tool instance
        
    Raises:
        ValueError: If the tool type is not supported or required configuration is missing
    """
    tool_type = config.tool_type.lower()
    tool_name = config.name or f"{tool_type}_tool"
    logger.info(f"Loading tool of type: {tool_type}, name: {tool_name}")
    
    if tool_type == ToolType.VECTOR_SEARCH:
        _check_required_fields(config, ["connection_str", "namespace", "embedding_model"], tool_type)
        
        # Create MongoDB tools instance
        mongodb_tools = MongoDBTools(
            name=tool_name,
            connection_str=config.connection_str,
            namespace=config.namespace,
            embedding_model=config.embedding_model,
            **config.additional_kwargs
        )
        
        # Get vector retriever tool
        return mongodb_tools.get_vector_retriever_tool()
    
    elif tool_type == ToolType.MONGODB_TOOLKIT:
        _check_required_fields(config, ["connection_str", "namespace", "llm"], tool_type)
        
        # Create MongoDB tools instance
        mongodb_tools = MongoDBTools(
            connection_str=config.connection_str,
            namespace=config.namespace,
            embedding_model=None  # Not needed for MongoDB toolkit
        )
        
        # Get MongoDB toolkit tools
        return mongodb_tools.get_mdb_toolkit(config.llm)
    
    elif tool_type == ToolType.NL_TO_MQL:
        _check_required_fields(config, ["connection_str", "namespace", "llm"], tool_type)
        
        # Create MongoDB tools instance
        mongodb_tools = MongoDBTools(
            connection_str=config.connection_str,
            namespace=config.namespace,
            embedding_model=None  # Not needed for NL to MQL
        )
        
        # Get NL to MQL tool
        return mongodb_tools.get_nl_to_mql_tool(config.llm)
    
    elif tool_type == ToolType.MCP:
        _check_required_fields(config, ["servers_config"], tool_type)
        
        # Get MCP tools
        server_name = config.additional_kwargs.get("server_name")
        return get_mcp_tools(config.servers_config, server_name)
    
    else:
        logger.error(f"Unsupported tool type: {tool_type}")
        raise ValueError(f"Unsupported tool type: {tool_type}")

def _check_required_fields(config: ToolConfig, fields: List[str], tool_type: str):
    """Check if required fields are present in the configuration."""
    missing_fields = [field for field in fields if not getattr(config, field)]
    if missing_fields:
        error_msg = f"Missing required field(s) for {tool_type} tool: {', '.join(missing_fields)}"
        logger.error(error_msg)
        raise ValueError(error_msg)

def load_tools(configs: List[ToolConfig]) -> List[BaseTool]:
    """
    Load multiple tools based on the provided configurations.
    
    Args:
        configs: List of ToolConfig objects
        
    Returns:
        List of initialized LangChain tool instances
    """
    logger.info(f"Loading {len(configs)} tools")
    tools = []
    
    for config in configs:
        try:
            tool = load_tool(config)
            if isinstance(tool, list):
                # Some tools like MongoDB toolkit return a list of tools
                tools.extend(zip([config.name]*len(tool), tool))
                logger.info(f"Added {len(tool)} tools from {config.tool_type}")
            else:
                tools.append((config.name, tool))
                logger.info(f"Added tool: {config.name or config.tool_type}")
        except Exception as e:
            logger.error(f"Failed to load tool {config.name or config.tool_type}: {str(e)}")

    return dict(tools)
