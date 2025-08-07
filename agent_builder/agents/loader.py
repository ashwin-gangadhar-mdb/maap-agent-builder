import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Type, Union

from langchain_core.language_models import BaseLLM
from langchain_core.tools import BaseTool

from agent_builder.agents.agent_gen import AgentFactory, AgentType
from agent_builder.utils.checkpointer import get_mongodb_checkpointer
from agent_builder.utils.logger import logger
from agent_builder.utils.logging_config import get_logger

"""
Agent loader for various agent types using the MAAP Agent Builder.
This module provides functionality to load different types of agents
including React, Reflection, Plan-Execute-Replan, and Long-Term Memory agents.
"""

# # Set up module logger
# logger = get_logger(__name__)


@dataclass
class AgentConfig:
    """Configuration for Agent setup."""

    agent_type: str
    name: str = "default_agent"
    system_prompt: Optional[str] = None
    reflection_prompt: Optional[str] = None
    system_prompt_path: Optional[str] = None
    reflection_prompt_path: Optional[str] = None
    llm: Optional[BaseLLM] = None
    tools: List[BaseTool] = field(default_factory=list)
    verbose: bool = False
    checkpointer_config: Optional[Dict[str, Any]] = None
    connection_str: Optional[str] = None
    namespace: Optional[str] = None
    additional_kwargs: Optional[Dict[str, Any]] = None


# Agent type configuration map
AGENT_CONFIG = {
    "react": {
        "agent_type": AgentType.REACT,
        "required_fields": ["llm", "system_prompt"],
        "optional_fields": ["tools", "system_prompt_path", "checkpointer_config"],
        "description": "ReAct agent that thinks step-by-step and uses tools",
    },
    "tool_call": {
        "agent_type": AgentType.TOOL_CALL,
        "required_fields": ["llm"],
        "optional_fields": [
            "tools",
            "system_prompt",
            "system_prompt_path",
            "checkpointer_config",
        ],
        "description": "Agent that uses OpenAI-style tool calling",
    },
    "reflect": {
        "agent_type": AgentType.REFLECT,
        "required_fields": ["llm", "system_prompt", "reflection_prompt"],
        "optional_fields": [
            "tools",
            "checkpointer_config",
            "system_prompt_path",
            "reflection_prompt_path",
        ],
        "description": "Agent that uses a generate-reflect loop for improved reasoning",
    },
    "plan_execute_replan": {
        "agent_type": AgentType.PLAN_EXECUTE_REPLAN,
        "required_fields": ["llm", "system_prompt"],
        "optional_fields": ["tools", "checkpointer_config", "system_prompt_path"],
        "description": "Agent that plans, executes steps, and replans as needed",
    },
    "long_term_memory": {
        "agent_type": AgentType.LONG_TERM_MEMORY,
        "required_fields": ["llm", "connection_str", "namespace"],
        "optional_fields": ["tools", "checkpointer_config"],
        "description": "Agent with vector store-backed long-term memory",
    },
}


def load_agent(config: AgentConfig) -> Any:
    """
    Load an agent based on the provided configuration.

    Args:
        config: AgentConfig containing agent type, LLM, tools, and other parameters

    Returns:
        An initialized agent instance

    Raises:
        ValueError: If the agent type is not supported or required configuration is missing
    """
    agent_type = config.agent_type.lower()
    logger.info(f"Loading agent of type: {agent_type}, name: {config.name}")

    # Check if agent type is supported
    if agent_type not in AGENT_CONFIG:
        available_types = list(AGENT_CONFIG.keys())
        logger.error(
            f"Unsupported agent type: {agent_type}. Available types: {available_types}"
        )
        raise ValueError(
            f"Unsupported agent type: {agent_type}. Available types: {available_types}"
        )

    agent_info = AGENT_CONFIG[agent_type]

    # Load prompts from files if paths are provided
    def load_prompt_from_file(prompt, path, prompt_type="system"):
        """Helper function to load prompt from file"""
        if not prompt and path:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    loaded_prompt = f.read()
                    logger.info(f"Loaded {prompt_type} prompt from: {path}")
                    return loaded_prompt
            except Exception as e:
                logger.error(
                    f"Failed to load {prompt_type} prompt from {path}: {str(e)}"
                )
                raise ValueError(
                    f"Failed to load {prompt_type} prompt from {path}: {str(e)}"
                )
        return prompt

    # Load prompts if needed
    config.system_prompt = load_prompt_from_file(
        config.system_prompt, config.system_prompt_path, "system"
    )

    config.reflection_prompt = load_prompt_from_file(
        config.reflection_prompt, config.reflection_prompt_path, "reflection"
    )

    # Verify required fields
    missing_fields = [
        field for field in agent_info["required_fields"] if not getattr(config, field)
    ]

    if missing_fields:
        error_msg = f"Missing required field(s) for {agent_type} agent: {', '.join(missing_fields)}"
        logger.error(error_msg)
        raise ValueError(error_msg)

    # Set up checkpointer if provided
    checkpointer = None
    if config.checkpointer_config:
        logger.info(f"Setting up checkpointer for agent {config.name}")
        try:
            checkpointer = get_mongodb_checkpointer(**config.checkpointer_config)
        except Exception as e:
            logger.warning(
                f"Failed to create checkpointer, using in-memory default: {str(e)}"
            )

    # Get system prompt from file if provided
    system_prompt = config.system_prompt
    reflection_prompt = config.reflection_prompt

    # Prepare kwargs for agent creation
    agent_kwargs = {
        "name": config.name,
        "model": config.llm,
        "tools": config.tools or [],
    }

    # Add specific parameters based on agent type
    if agent_type in ["react", "tool_call"]:
        agent_kwargs["prompt"] = system_prompt
    elif agent_type == "reflect":
        # Basic reflection agent needs both generate and reflection prompts
        if config.additional_kwargs and "reflection_prompt" in config.additional_kwargs:
            agent_kwargs["generate_prompt"] = system_prompt
            agent_kwargs["reflection_prompt"] = reflection_prompt
        else:
            logger.error(
                "Reflection agent requires a reflection_prompt in additional_kwargs"
            )
            raise ValueError(
                "Reflection agent requires a reflection_prompt in additional_kwargs"
            )
    elif agent_type == "plan_execute_replan":
        agent_kwargs["execute_prompt"] = system_prompt
    elif agent_type == "long_term_memory":
        agent_kwargs["connection_str"] = config.connection_str
        agent_kwargs["namespace"] = config.namespace

    # Add checkpointer if available
    if checkpointer:
        agent_kwargs["checkpointer"] = checkpointer

    # Add any additional kwargs
    if config.additional_kwargs:
        for key, value in config.additional_kwargs.items():
            if key not in agent_kwargs:
                agent_kwargs[key] = value

    logger.debug(f"Creating {agent_type} agent with parameters: {agent_kwargs}")

    # Create the agent using AgentFactory
    try:
        return AgentFactory.create_agent(agent_info["agent_type"], **agent_kwargs)
    except Exception as e:
        logger.error(f"Failed to create agent: {str(e)}")
        raise RuntimeError(f"Failed to create agent: {str(e)}")
