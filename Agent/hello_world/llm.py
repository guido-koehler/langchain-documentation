"""
LLM client shared by all agents in this package.

Reads credentials from environment variables (loaded from .env by main.py).
Uses AzureChatOpenAI from langchain_openai to connect to a model deployed
in Azure OpenAI (*.openai.azure.com).

Authentication strategy:
  - Production / AKS: DefaultAzureCredential resolves to the pod's Managed Identity.
  - Local dev with `az login`: DefaultAzureCredential uses the CLI token automatically.
  - Local dev without `az login`: set AZURE_OPENAI_API_KEY in .env as a fallback.
"""
import os

from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from langchain_openai import AzureChatOpenAI


def get_llm() -> AzureChatOpenAI:
    """Return a configured AzureChatOpenAI instance."""
    endpoint = os.environ["AZURE_OPENAI_ENDPOINT"]
    model_name = os.environ["MODEL_DEPLOYMENT_NAME"]
    api_version = os.environ.get("AZURE_OPENAI_API_VERSION", "2024-10-21")
    api_key = os.environ.get("AZURE_OPENAI_API_KEY")

    if api_key:
        # Explicit API key — useful for local dev without az login
        return AzureChatOpenAI(
            azure_endpoint=endpoint,
            azure_deployment=model_name,
            api_version=api_version,
            api_key=api_key,
            temperature=0.2,
        )

    # DefaultAzureCredential — works for az login (local) and Managed Identity (AKS)
    token_provider = get_bearer_token_provider(
        DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default"
    )
    return AzureChatOpenAI(
        azure_endpoint=endpoint,
        azure_deployment=model_name,
        api_version=api_version,
        azure_ad_token_provider=token_provider,
        temperature=0.2,
    )
