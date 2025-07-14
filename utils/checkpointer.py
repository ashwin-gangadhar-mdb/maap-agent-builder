from langgraph.checkpoint.mongodb import MongoDBSaver
from pymongo import MongoClient
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)



def get_mongodb_checkpointer(
    connection_str: str,
    db_name: str = "langgraph",
    collection_name: str = "checkpoints",
    name: str = "mongodb_checkpointer"
) -> MongoDBSaver:
    """
    Create a MongoDB checkpointer for saving agent state.
    
    Args:
        connection_str: MongoDB connection string
        database: Database name for storing checkpoints
        collection: Collection name for storing checkpoints
        name: Name of the checkpointer for logging purposes
    """
    logger.info(f"Creating MongoDB checkpointer: {name}")
    
    client = MongoClient(connection_str)
    db = client[db_name]
    return MongoDBSaver(db, collection_name, name=name)