import logging
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.callbacks import BaseCallbackHandler
from typing import List, Optional

from .config import get_config

logger = logging.getLogger(__name__)

def get_llm(callbacks: Optional[List[BaseCallbackHandler]] = None) -> ChatGoogleGenerativeAI:
    """
    Configures and returns an instance of the ChatGoogleGenerativeAI LLM.

    Reads configuration settings (API key, model name, temperature) 
    from the application's config. Includes basic retry logic.

    Args:
        callbacks: An optional list of LangChain callback handlers to attach.

    Returns:
        An instance of ChatGoogleGenerativeAI.
    """
    config = get_config()
    
    try:
        llm = ChatGoogleGenerativeAI(
            model=config.LLM_MODEL,
            google_api_key=config.GOOGLE_API_KEY,
            temperature=config.LLM_TEMPERATURE,
            convert_system_message_to_human=True, # Recommended for Gemini
            callbacks=callbacks or [],
            # Configure basic retries using LangChain's default mechanism (tenacity)
            max_retries=config.LLM_MAX_RETRIES, 
        )
        logger.info(f"Initialized ChatGoogleGenerativeAI LLM with model: {config.LLM_MODEL}")
        return llm
    except ValueError as ve:
        # Catch potential validation errors during Pydantic model creation inside get_llm/get_config
        logger.error(f"Configuration error: {ve}", exc_info=True)
        raise ValueError(f"Configuration error: {ve}")
    except Exception as e:
        logger.exception(f"Failed to initialize ChatGoogleGenerativeAI LLM: {e}")
        # Ensure the error message refers to the correct key
        raise ValueError(f"Failed to initialize LLM. Ensure GOOGLE_API_KEY is set correctly and valid. Error: {e}")

# Example Usage (Optional - for direct testing)
if __name__ == '__main__':
    # Logging setup needs to access config, which loads .env now
    from mdt_agent_system.app.core.logging.logger import setup_logging 
    from mdt_agent_system.app.core.callbacks import LoggingCallbackHandler
    # Removed dotenv and pathlib imports as .env is loaded by settings.py
    import os 

    # Removed explicit dotenv loading logic
    print("Setting up logging...")
    # Logging setup might fail if config (which loads .env) failed, 
    # but the error would have occurred earlier during import.
    setup_logging()
    
    # Check if API key is actually loaded in the environment now
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        # This check might be redundant if Settings() validation passed, but good for sanity check
        print("ERROR: GOOGLE_API_KEY not found in environment variables after settings load.")
        logger.error("GOOGLE_API_KEY not found in environment variables after settings load.")
        exit(1)
    
    try:
        print("Initializing LLM with logging callback...")
        logging_callback = LoggingCallbackHandler()
        test_llm = get_llm(callbacks=[logging_callback])
        print("LLM Initialized successfully.")
        
        print("\nInvoking LLM...")
        prompt = "Explain the concept of a Large Language Model in one sentence."
        print(f"Prompt: {prompt}")
        response = test_llm.invoke(prompt)
        print("\nLLM Response:")
        print(response.content)
        print("\nCheck logs for LLM Start/End events from LoggingCallbackHandler.")

    except ValueError as ve:
        print(f"\nERROR during LLM initialization: {ve}")
        logger.error(f"Error during LLM initialization: {ve}", exc_info=True)
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")
        logger.error(f"An unexpected error occurred: {e}", exc_info=True) 