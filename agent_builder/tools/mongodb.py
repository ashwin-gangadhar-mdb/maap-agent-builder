from langchain_core.tools import tool, ToolException
from langchain_mongodb import MongoDBAtlasVectorSearch
from langchain_mongodb.agent_toolkit import (
    MongoDBDatabase, MongoDBDatabaseToolkit, MONGODB_AGENT_SYSTEM_PROMPT
)
from typing import List, Optional, Union, Any, Dict, Tuple
from langgraph.prebuilt import create_react_agent
from pymongo import MongoClient
import certifi
import logging
from langchain_core.embeddings import Embeddings

# Create module-level logger
logger = logging.getLogger(__name__)

class MongoDBTools:
    """
    Tool for retrieving relevant products and their information from a vector store,
    and for natural language to MQL conversion and execution.
    """

    def __init__(
        self,
        connection_str: str,
        namespace: str,
        embedding_model: Optional[Embeddings],
        name: str = "mongodb_toolkit",
        index_name: Optional[str] = "vector_index",
        embedding_field: Optional[str] = "embedding",
        text_field: Optional[str] = "text",
        top_k: Optional[int] = 5,
        num_candidates: Optional[int] = 100,
        min_score: Optional[float] = 0.7
    ):
        # Create class logger with appropriate name
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.logger.info(f"Initializing MongoDB tools for namespace: {namespace}")
        self.name = name
        self.top_k = top_k
        self.connection_str = connection_str
        self.namespace = namespace
        self.embedding_model = embedding_model
        self.index_name = index_name
        self.embedding_field = embedding_field
        self.text_field = text_field
        self.min_score = min_score

        try:
            self.client = MongoClient(connection_str, tlsCAFile=certifi.where())
            self.logger.info("Successfully connected to MongoDB")
        except Exception as e:
            self.logger.error(f"Failed to connect to MongoDB: {e}")
            raise ConnectionError(f"Could not connect to MongoDB: {e}")

        self.database_name, self.collection_name = namespace.split('.', 1)
        self.logger.debug(f"Connected to MongoDB database: {self.database_name}, collection: {self.collection_name}")

    def _init_vector_retriever(self):
        self.logger.debug(f"Initializing vector retriever with index: {self.index_name}")
        vector_store = MongoDBAtlasVectorSearch.from_connection_string(
            connection_string=self.connection_str,
            namespace=self.namespace,
            embedding=self.embedding_model,
            embedding_field=self.embedding_field,
            index_name=self.index_name,
            text_field=self.text_field
        )
        self.logger.debug(f"Vector store initialized, creating retriever with top_k={self.top_k}")
        return vector_store.as_retriever(search_kwargs={"k": self.top_k, "score_threshold": self.min_score})

    def get_vector_retriever_tool(self):
        # Create tool-specific logger with tool name
        tool_logger_name = f"{__name__}.{self.__class__.__name__}.{self.name}"
        tool_logger = logging.getLogger(tool_logger_name)
        tool_logger.info(f"Creating vector retriever tool: {self.name}")
        
        vector_retriever = self._init_vector_retriever()

        @tool
        def vector_retriever_tool(search_query: str) -> str:
            """
            Retrieve relevant documents and their information from a vector store based on provided search query.
            Args:
                search_query (str): The query to search for relevant documents.
            Returns:
                str: A formatted string containing the retrieved documents and their sources.
            """
            tool_logger.info(f"Tool {self.name}: Retrieving documents for query")
            tool_logger.debug(f"Tool {self.name}: Query: {search_query}")
            try:
                results = vector_retriever.invoke(search_query)
                if not results:
                    tool_logger.warning(f"Tool {self.name}: No results found for the query")
                    raise ToolException("No results found for the query.")

                tool_logger.info(f"Tool {self.name}: Found {len(results)} relevant documents")
                context = "Retrieved Documents:\n\n" + "\n\n".join(
                    f"text_{i}: {doc.page_content} \nsource_{i}: {doc.metadata.get('source', 'N/A')}"
                    for i, doc in enumerate(results)
                )
                return context
            except Exception as e:
                tool_logger.error(f"Tool {self.name}: Failed to retrieve relevant information")
                tool_logger.exception(f"Tool {self.name}: Error during retrieval: {e}")
                return "Retrieval failed."
        return vector_retriever_tool

    def get_mdb_toolkit(self, llm):
        name = self.name
        toolkit_logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}.{name}")
        toolkit_logger.info(f"Creating MongoDB toolkit: {name}")        
        if llm is None:
            toolkit_logger.error("LLM must be provided to create the toolkit")
            raise ValueError("A language model (llm) must be provided to create the toolkit.")
        db = MongoDBDatabase(self.client, self.database_name)
        toolkit = MongoDBDatabaseToolkit(db=db, llm=llm)
        toolkit_logger.debug("MongoDB toolkit created with database: %s", self.database_name)
        return toolkit.get_tools()

    def get_nl_to_mql_tool(self, llm):
        """
        Returns a tool that converts natural language to MongoDB queries (MQL) and executes them.
        Requires a language model (llm) as input.
        """
        # Create tool-specific logger with tool name
        name = self.name
        tool_logger_name = f"{__name__}.{self.__class__.__name__}.{name}"
        tool_logger = logging.getLogger(tool_logger_name)
        tool_logger.info(f"Creating NL to MQL tool: {name}")
        
        if llm is None:
            tool_logger.error("LLM must be provided to create the NL to MQL tool")
            raise ValueError("A language model (llm) must be provided to create the NL to MQL tool.")
        
        tools = self.get_mdb_toolkit(llm)
        system_message = MONGODB_AGENT_SYSTEM_PROMPT.format(top_k=self.top_k)
        tool_logger.debug("Creating React agent for NL to MQL conversion")
        agent = create_react_agent(model=llm, tools=tools, prompt=system_message)

        @tool
        def nl_to_mql_tool(nl_query: str) -> str:
            """
            Convert a natural language query to MongoDB MQL and execute it.
            Args:
                nl_query (str): The user's natural language query.
            Returns:
                str: The result of the MongoDB query.
            """
            tool_logger.info(f"Tool {name}: Processing natural language query")
            tool_logger.debug(f"Tool {name}: NL Query: {nl_query}")
            
            try:
                events = agent.invoke({
                    "messages": [("user", f"Input: {nl_query}")]
                })
                messages = events.get("messages", [])
                
                if messages:
                    tool_logger.info(f"Tool {name}: Successfully processed query")
                    return messages[-1].content
                
                tool_logger.warning(f"Tool {name}: No response from agent after processing")
                raise ToolException("No response from the agent after processing the query.")
            except Exception as e:
                tool_logger.error(f"Tool {name}: Failed to convert NL to MQL or execute query")
                tool_logger.exception(f"Tool {name}: Error: {e}")
                return "Natural language to MQL conversion or execution failed."
        
        return nl_to_mql_tool
