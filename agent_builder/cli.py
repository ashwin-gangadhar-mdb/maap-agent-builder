#!/usr/bin/env python3
import argparse
import os
import sys
from agent_builder.utils.logger import logger

from agent_builder.app import AgentApp
from agent_builder.utils.logging_config import get_logger, configure_logging

# Initialize logger
logger = get_logger(__name__)

def main():
    """Main entry point for the MAAP Agent Builder CLI."""
    parser = argparse.ArgumentParser(description="MAAP Agent Builder Command Line Interface")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Server command
    server_parser = subparsers.add_parser("serve", help="Run the agent as a web server")
    server_parser.add_argument("--config", "-c", required=True, help="Path to the YAML configuration file")
    server_parser.add_argument("--host", default="0.0.0.0", help="Host to run the server on (default: 0.0.0.0)")
    server_parser.add_argument("--port", "-p", type=int, default=5000, help="Port to run the server on (default: 5000)")
    server_parser.add_argument("--debug", "-d", action="store_true", help="Run in debug mode")
    server_parser.add_argument("--log-level", "-l", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                              default="INFO", help="Set the logging level")
    server_parser.add_argument("--env-file", "-e", help="Path to a .env file to load environment variables")
    
    # Parse arguments
    args = parser.parse_args()
    
    # Configure logging based on command-line arguments
    # Pass the string log level directly, not the numeric value
    log_level = args.log_level if hasattr(args, "log_level") else "INFO"
    configure_logging(level=log_level)
    
    # Execute the command
    if not args.command:
        parser.print_help()
        return 1
    
    if args.command == "serve":
        try:
            logger.info(f"Starting agent server with configuration: {args.config}")
            if args.env_file:
                from dotenv import load_dotenv
                load_dotenv(args.env_file)
                logger.info(f"Loaded environment variables from {args.env_file}")
            agent_app = AgentApp(args.config)
            agent_app.run(host=args.host, port=args.port, debug=args.debug)
        except Exception as e:
            logger.exception(f"Failed to start server: {str(e)}")
            return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
