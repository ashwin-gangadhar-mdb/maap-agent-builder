"""
MCP (Model Context Protocol) tools for MDB Agent Builder.

This module provides integration with MCP servers using langchain-mcp-adapters.
It supports connecting to MCP servers using various transports (stdio, streamable-http, etc.)
and loading MCP tools for use with agents.
"""

import os
from agent_builder.utils.logger import logger
import asyncio
from typing import Dict, Any, List, Optional, Union, Callable

from agent_builder.utils.logging_config import get_logger

# Import MCP-related libraries
try:
    from langchain_mcp_adapters.client import MultiServerMCPClient
    from langchain_mcp_adapters.tools import load_mcp_tools, to_fastmcp
    from mcp import ClientSession
    from mcp.client.stdio import stdio_client
    from mcp.client.streamable_http import streamablehttp_client
except ImportError:
    raise ImportError(
        "MCP integration requires additional dependencies. "
        "Please install them with: pip install langchain-mcp-adapters mcp"
    )

# Set up module logger
logger = get_logger(__name__)

class MCPToolManager:
    """
    Tool manager for Model Context Protocol (MCP) servers.
    
    This class provides functionality to connect to MCP servers and load tools from them.
    It supports both single-server connections and multi-server setups.
    """
    
    def __init__(self):
        """Initialize the MCP tool manager."""
        self.clients = {}
        self.tools = {}
        
    async def get_tools_from_server(self, 
                              server_name: str, 
                              config: Dict[str, Any]) -> List[Any]:
        """
        Get tools from a specific MCP server.
        
        Args:
            server_name: Name of the server
            config: Server configuration dictionary
            
        Returns:
            List of LangChain tools from the MCP server
            
        Raises:
            ValueError: If the transport is not supported or configuration is invalid
        """
        transport = config.get("transport", "stdio").lower()
        logger.info(f"Loading MCP tools from server '{server_name}' using {transport} transport")
        
        if transport == "stdio":
            if not config.get("command"):
                raise ValueError(f"Server '{server_name}' config must include 'command'")
            
            command = config["command"]
            args = config.get("args", [])
            
            logger.debug(f"Connecting to MCP server '{server_name}' with command: {command} {' '.join(args)}")
            
            async with stdio_client({"command": command, "args": args}) as (read, write):
                async with ClientSession(read, write) as session:
                    # Initialize the connection
                    await session.initialize()
                    
                    # Get tools
                    tools = await load_mcp_tools(session)
                    logger.info(f"Loaded {len(tools)} tools from MCP server '{server_name}'")
                    return tools
                    
        elif transport in ["streamable_http", "streamable-http"]:
            if not config.get("url"):
                raise ValueError(f"Server '{server_name}' config must include 'url'")
            
            url = config["url"]
            headers = config.get("headers", {})
            
            logger.debug(f"Connecting to MCP server '{server_name}' at URL: {url}")
            
            async with streamablehttp_client(url, headers=headers) as (read, write, _):
                async with ClientSession(read, write) as session:
                    # Initialize the connection
                    await session.initialize()
                    
                    # Get tools
                    tools = await load_mcp_tools(session)
                    logger.info(f"Loaded {len(tools)} tools from MCP server '{server_name}'")
                    return tools
        else:
            raise ValueError(f"Unsupported transport '{transport}' for server '{server_name}'")
    
    async def load_tools_from_servers(self, 
                                servers_config: Dict[str, Dict[str, Any]]) -> List[Any]:
        """
        Load tools from multiple MCP servers using MultiServerMCPClient.
        
        Args:
            servers_config: Dictionary mapping server names to their configurations
            
        Returns:
            List of LangChain tools from all MCP servers
        """
        logger.info(f"Loading MCP tools from {len(servers_config)} servers")
        
        client = MultiServerMCPClient(servers_config)
        all_tools = await client.get_tools()
        
        logger.info(f"Loaded a total of {len(all_tools)} tools from all MCP servers")
        return all_tools
    
    def run_async(self, coro):
        """Run an async coroutine in a synchronous context."""
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(coro)
    
    def get_tools(self, 
                  servers_config: Dict[str, Dict[str, Any]], 
                  server_name: Optional[str] = None) -> List[Any]:
        """
        Synchronous method to get tools from MCP servers.
        
        Args:
            servers_config: Dictionary mapping server names to their configurations
            server_name: Optional specific server to load tools from
            
        Returns:
            List of LangChain tools from the MCP servers
        """
        if server_name:
            if server_name not in servers_config:
                raise ValueError(f"Server '{server_name}' not found in configuration")
            
            logger.info(f"Loading tools from specific server: {server_name}")
            return self.run_async(self.get_tools_from_server(server_name, servers_config[server_name]))
        
        return self.run_async(self.load_tools_from_servers(servers_config))


def get_mcp_tools(servers_config: Dict[str, Dict[str, Any]], 
                  server_name: Optional[str] = None) -> List[Any]:
    """
    Get tools from MCP servers.
    
    Args:
        servers_config: Dictionary mapping server names to their configurations
        server_name: Optional specific server to load tools from
        
    Returns:
        List of LangChain tools from the MCP servers
        
    Example:
        ```python
        servers = {
            "math": {
                "transport": "stdio",
                "command": "python",
                "args": ["/path/to/math_server.py"]
            },
            "weather": {
                "transport": "streamable_http",
                "url": "http://localhost:8000/mcp/"
            }
        }
        
        tools = get_mcp_tools(servers)
        ```
    """
    manager = MCPToolManager()
    return manager.get_tools(servers_config, server_name)


def convert_langchain_tool_to_mcp(langchain_tool) -> Any:
    """
    Convert a LangChain tool to an MCP-compatible tool.
    
    Args:
        langchain_tool: A LangChain tool to convert
        
    Returns:
        MCP-compatible tool object
        
    Example:
        ```python
        from langchain_core.tools import tool
        
        @tool
        def add(a: int, b: int) -> int:
            '''Add two numbers'''
            return a + b
            
        mcp_tool = convert_langchain_tool_to_mcp(add)
        ```
    """
    return to_fastmcp(langchain_tool)
