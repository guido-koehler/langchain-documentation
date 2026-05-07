"""
LLM client shared by all agents in this package.

Reads credentials from environment variables (loaded from .env by main.py).
Uses ChatAnthropic from langchain-anthropic to connect to Claude models
(claude-sonnet-4-6 / claude-haiku-4-5) deployed inside an Azure AI Foundry project.

Authentication:
  - AZURE_AI_API_KEY is the Azure-issued key for the Claude serverless deployment.
    In production (AKS) this key is injected from Azure Key Vault via the CSI driver;
    it is never stored in source code.
  - AZURE_AI_PROJECT_ENDPOINT is the Foundry project endpoint used as the base URL.

Model selection:
  - get_llm()           → claude-sonnet-4-6  (complex tasks: scaffolding, review, planning)
  - get_llm(mini=True)  → claude-haiku-4-5   (fast/cheap tasks: translation, summaries)
"""
import os

from langchain_anthropic import ChatAnthropic


def get_llm(mini: bool = False) -> ChatAnthropic:
    """Return a configured ChatAnthropic instance pointing to Azure AI Foundry."""
    model = (
        os.environ.get("MODEL_MINI_DEPLOYMENT_NAME", "claude-haiku-4-5") if mini
        else os.environ.get("MODEL_DEPLOYMENT_NAME", "claude-sonnet-4-6")
    )
    return ChatAnthropic(
        model=model,
        # Azure Foundry-issued API key for the Claude serverless deployment
        api_key=os.environ["AZURE_AI_API_KEY"],
        # Foundry project endpoint acts as the Anthropic-compatible base URL
        base_url=os.environ["AZURE_AI_PROJECT_ENDPOINT"],
        temperature=0,       # deterministic output for code generation
        max_retries=3,
    )
