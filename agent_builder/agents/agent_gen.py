"""
Agent generator module for creating various types of agents.

This module provides factory functions to create different types of agents
based on their functionality and architecture. It supports lazy loading
of agent modules to avoid circular dependencies.
"""

from enum import Enum
from typing import Any, Dict, TypeVar, cast

from langgraph.prebuilt import create_react_agent  # type:ignore

from agent_builder.utils.logging_config import get_logger

# Create a module-level logger
logger = get_logger(__name__)

AgentReturnType = TypeVar("AgentReturnType")


class AgentType(Enum):
    TOOL_CALL = "tool_call"
    REACT = "react"
    REFLECT = "reflect"
    PLAN_EXECUTE_REPLAN = "plan_execute_replan"
    LONG_TERM_MEMORY = "long_term_memory"

    @classmethod
    def get_available_types(cls) -> list[str]:
        """Return a list of all available agent types as strings."""
        return [agent_type.value for agent_type in cls]


class AgentFactory:
    """
    Factory class to create agents based on the specified type.
    Lazily imports agent modules to avoid circular dependencies.
    """

    # Map agent types to their creator function modules and names
    _AGENT_CREATORS: Dict[AgentType, tuple[str, str]] = {
        AgentType.TOOL_CALL: ("agent_builder.agents.agent_gen", "create_react_agent"),
        AgentType.REACT: ("agent_builder.agents.agent_gen", "create_react_agent"),
        AgentType.REFLECT: (
            "agent_builder.agents.reflection",
            "create_basic_reflection_agent",
        ),
        AgentType.PLAN_EXECUTE_REPLAN: (
            "agent_builder.agents.plan_execute_replan",
            "create_plan_execute_replan_agent",
        ),
        AgentType.LONG_TERM_MEMORY: (
            "agent_builder.agents.long_term_memory",
            "create_long_term_memory_agent",
        ),
    }

    @classmethod
    def create_agent(cls, agent_type: AgentType, **kwargs: Any) -> AgentReturnType:
        """
        Create an agent instance based on the specified type.

        Args:
            agent_type: The type of agent to create
            **kwargs: Arguments to pass to the agent creator function

        Returns:
            An instance of the requested agent type

        Raises:
            ValueError: If the agent type is not supported
            ImportError: If there's an issue importing the agent module
        """
        # Ensure a name is provided for logging purposes
        agent_name = kwargs.get("name", f"{agent_type.value}_agent")
        kwargs["name"] = agent_name

        logger.info(
            "Creating agent of type %s with name '%s'", agent_type.value, agent_name
        )

        if agent_type not in cls._AGENT_CREATORS:
            available_types = AgentType.get_available_types()
            logger.error(
                "Unknown agent type: %s. Available types: %s",
                agent_type,
                available_types,
            )
            raise ValueError(
                f"Unknown agent type: {agent_type}. Available types: {available_types}"
            )

        try:
            module_path, function_name = cls._AGENT_CREATORS[agent_type]
            logger.debug("Importing %s from %s", function_name, module_path)

            # Lazily import the module only when needed
            module = __import__(module_path, fromlist=[function_name])
            creator_func = getattr(module, function_name)

            logger.info(
                "Successfully created agent %s of type %s", agent_name, agent_type.value
            )
            return cast(AgentReturnType, creator_func(**kwargs))
        except ImportError as e:
            logger.exception("Failed to import agent module for %s", agent_type)
            raise ImportError(
                f"Failed to import agent module for {agent_type}: {str(e)}"
            ) from e
        except AttributeError as e:
            logger.exception("Failed to find creator function for %s", agent_type)
            raise ImportError(
                f"Failed to find creator function for {agent_type}: {str(e)}"
            ) from e
        except Exception as e:
            logger.exception("Error creating agent of type %s", agent_type)
            raise RuntimeError(
                f"Error creating agent of type {agent_type}: {str(e)}"
            ) from e

    @classmethod
    def register_agent_type(
        cls, agent_type: AgentType, module_path: str, function_name: str
    ) -> None:
        """
        Register a new agent type with the factory.

        Args:
            agent_type: The agent type to register
            module_path: The module path where the creator function is defined
            function_name: The name of the creator function
        """
        logger.info(
            "Registering new agent type %s to %s.%s",
            agent_type.name,
            module_path,
            function_name,
        )
        cls._AGENT_CREATORS[agent_type] = (module_path, function_name)


# if __name__=="__main__":
#     # Example usage
#     factory = AgentFactory()
#     agent = factory.create_agent(AgentType.REACT, llm="example_llm", tools=["example_tool"])
