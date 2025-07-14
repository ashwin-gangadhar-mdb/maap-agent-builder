from flask import Flask, request, jsonify, session
import os
import uuid
import logging
from typing import Dict, Any, Optional

from mdb_agent_builder.yaml_loader import load_application
from mdb_agent_builder.utils.logging_config import get_logger

# Initialize logger
logger = get_logger(__name__)

class AgentApp:
    """
    Flask application for serving agents loaded from YAML configurations.
    """
    
    def __init__(self, config_path: str, session_ttl: int = 3600):
        """
        Initialize the agent application with the specified YAML configuration.
        
        Args:
            config_path: Path to the YAML configuration file
            session_ttl: Time-to-live for session data in seconds (default: 1 hour)
        """
        self.app = Flask(__name__)
        self.app.secret_key = os.environ.get("FLASK_SECRET_KEY", str(uuid.uuid4()))
        self.app.config["PERMANENT_SESSION_LIFETIME"] = session_ttl
        self.config_path = config_path
        self.components = None
        self.agent = None
        
        # Register routes
        self.register_routes()
        
        # Load agent components
        self.load_components()
    
    def load_components(self):
        """Load agent and related components from the YAML configuration."""
        try:
            logger.info(f"Loading application components from {self.config_path}")
            self.components = load_application(self.config_path)
            
            if "agent" not in self.components:
                logger.error("No agent configured in the YAML file")
                raise ValueError("No agent configured in the YAML file")
            
            self.agent = self.components["agent"]
            logger.info(f"Agent successfully loaded from {self.config_path}")
        except Exception as e:
            logger.error(f"Failed to load application components: {str(e)}")
            raise
    
    def register_routes(self):
        """Register API routes for the Flask application."""
        @self.app.route("/health", methods=["GET"])
        def health():
            """Health check endpoint."""
            if self.agent:
                return jsonify({"status": "healthy", "agent_loaded": True})
            return jsonify({"status": "unhealthy", "agent_loaded": False}), 503
        
        @self.app.route("/chat", methods=["POST"])
        def chat():
            """Chat endpoint to interact with the agent."""
            if not self.agent:
                return jsonify({"error": "Agent not loaded"}), 503
            
            try:
                data = request.json
                if not data or "message" not in data:
                    return jsonify({"error": "Missing required field: message"}), 400
                
                user_message = data["message"]
                logger.info(f"Received chat request with message: {user_message[:50]}...")
                
                # Get or initialize chat history
                chat_history = session.get("chat_history", [])
                
                # Prepare input for the agent
                if hasattr(self.agent, "invoke"):
                    # For LangGraph agents
                    input_data = {
                        "messages": chat_history + [("user", user_message)]
                    }
                    
                    # Include any additional parameters from the request
                    for key, value in data.items():
                        if key != "message" and key != "history":
                            input_data[key] = value
                    
                    # Invoke the agent
                    response = self.agent.invoke(input_data)
                    
                    # Process agent response
                    if isinstance(response, dict) and "messages" in response:
                        # LangGraph agent response
                        agent_messages = response["messages"]
                        if agent_messages:
                            last_message = agent_messages[-1]
                            if hasattr(last_message, "content"):
                                agent_response = last_message.content
                            else:
                                agent_response = str(last_message)
                        else:
                            agent_response = "No response from agent"
                    else:
                        agent_response = str(response)
                    
                    # Update chat history
                    chat_history.append(("user", user_message))
                    chat_history.append(("assistant", agent_response))
                    session["chat_history"] = chat_history
                    
                    return jsonify({
                        "response": agent_response,
                        "history": chat_history
                    })
                else:
                    # Legacy agent format fallback
                    logger.warning("Using legacy agent format")
                    agent_response = str(self.agent(user_message))
                    
                    # Update chat history
                    chat_history.append(("user", user_message))
                    chat_history.append(("assistant", agent_response))
                    session["chat_history"] = chat_history
                    
                    return jsonify({
                        "response": agent_response,
                        "history": chat_history
                    })
            
            except Exception as e:
                logger.exception(f"Error processing chat request: {str(e)}")
                return jsonify({"error": f"Failed to process request: {str(e)}"}), 500
        
        @self.app.route("/reset", methods=["POST"])
        def reset():
            """Reset the chat history."""
            session["chat_history"] = []
            return jsonify({"status": "success", "message": "Chat history reset"})
    
    def run(self, host: str = "0.0.0.0", port: int = 5000, debug: bool = False):
        """Run the Flask application."""
        logger.info(f"Starting agent server on {host}:{port}")
        self.app.run(host=host, port=port, debug=debug)


def create_app(config_path: str) -> Flask:
    """
    Factory function to create and configure a Flask application.
    
    Args:
        config_path: Path to the YAML configuration file
        
    Returns:
        Configured Flask application
    """
    agent_app = AgentApp(config_path)
    return agent_app.app


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run the MAAP Agent Builder Flask application")
    parser.add_argument("--config", "-c", required=True, help="Path to the YAML configuration file")
    parser.add_argument("--host", default="0.0.0.0", help="Host to run the server on (default: 0.0.0.0)")
    parser.add_argument("--port", "-p", type=int, default=5000, help="Port to run the server on (default: 5000)")
    parser.add_argument("--debug", "-d", action="store_true", help="Run in debug mode")
    
    args = parser.parse_args()
    
    agent_app = AgentApp(args.config)
    agent_app.run(host=args.host, port=args.port, debug=args.debug)
