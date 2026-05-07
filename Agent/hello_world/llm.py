"""
LLM client shared by all agents in this package.

Reads credentials from environment variables (loaded from .env by main.py).
Uses AzureAIChatCompletionsModel from langchain-azure-ai to connect to a model
deployed inside an Azure AI Foundry project.

Authentication strategy:
  - Production / AKS: DefaultAzureCredential resolves to the pod's Managed Identity.
  - Local dev with `az login`: DefaultAzureCredential uses the CLI token automatically.
  - Local dev without `az login`: set AZURE_AI_API_KEY in .env as a fallback.
"""
import os

from azure.identity import DefaultAzureCredential
from langchain_azure_ai.chat_models import AzureAIChatCompletionsModel


def get_llm() -> AzureAIChatCompletionsModel:
    """Return a configured AzureAIChatCompletionsModel instance."""
    endpoint = os.environ["AZURE_AI_PROJECT_ENDPOINT"]
    model_name = os.environ["MODEL_DEPLOYMENT_NAME"]
    api_key = os.environ.get("AZURE_AI_API_KEY")

    if api_key:
        # Explicit API key — useful for local dev without az login
        return AzureAIChatCompletionsModel(
            model_name=model_name,
            endpoint=endpoint,
            api_key=api_key,
            temperature=0.2,
        )

    # DefaultAzureCredential — works for az login (local) and Managed Identity (AKS)
    return AzureAIChatCompletionsModel(
        model_name=model_name,
        endpoint=endpoint,
        credential=DefaultAzureCredential(),
        temperature=0.2,
    )
