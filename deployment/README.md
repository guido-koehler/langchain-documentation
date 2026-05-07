# Deployment — Azure AI Foundry (Terraform)

This folder provisions the Azure AI Foundry infrastructure needed to run the
tj-sales agentic development setup.

## What gets deployed

| Resource | Name | Purpose |
|---|---|---|
| Resource Group | `rg-agentic-development` | Container for all resources |
| Storage Account | `stagenticdevelopmentserv` | Required by Foundry Hub |
| Key Vault | `kv-agentic-development` | Required by Foundry Hub; also stores agent secrets |
| Log Analytics Workspace | `law-agentic-development-service` | Backing store for Application Insights |
| Application Insights | `appi-agentic-development-service` | OpenTelemetry traces from LangGraph agents |
| **Foundry Hub** | `agentic-development-service` | Top-level Foundry resource; owns storage/KV/APPI |
| **Foundry Project** | `agentic-development-project` | Project scope — deploy models here, connect from agents |

## Prerequisites

- [Terraform](https://developer.hashicorp.com/terraform/install) ≥ 1.9  
  Install on Windows: `winget install Hashicorp.Terraform`
- Azure CLI logged in to the target subscription:  
  ```bash
  az login
  az account set --subscription 9e713dec-c712-47bf-b240-84d71a958e83
  ```

## Deploy

```bash
# From the deployment/ directory

# 1. Initialise providers
terraform init

# 2. Validate configuration
terraform validate

# 3. Preview changes
terraform plan

# 4. Apply
terraform apply -auto-approve
```

After a successful apply, Terraform prints the outputs. Copy the values into
`Agent/.env`:

```
AZURE_AI_PROJECT_ENDPOINT=<foundry_project_endpoint output>
APPLICATION_INSIGHTS_CONNECTION_STRING=<run: terraform output -raw application_insights_connection_string>
```

## Deploy models

After the infrastructure is created, open the Foundry portal and deploy your
models into the project:

1. Go to the [Azure Portal link](https://portal.azure.com) printed in the outputs.
2. Navigate to the Foundry Hub → **Launch in AI Foundry portal**.
3. Open the `agentic-development-project` project.
4. Go to **Models + endpoints** → **Deploy model** → choose `gpt-5.4` (primary)
   and `gpt-5.4-mini` (mini).
5. Set `MODEL_DEPLOYMENT_NAME=gpt-5.4` in `Agent/.env`.

## Tear down

```bash
terraform destroy -auto-approve
```

## File structure

```
deployment/
├── providers.tf      ← azurerm (≥4.2) + azapi (≥2.0) provider config
├── variables.tf      ← all input variables with defaults
├── main.tf           ← all resources (RG, Storage, KV, APPI, Hub, Project)
├── outputs.tf        ← endpoint URL, App Insights connection string, KV URI
├── terraform.tfvars  ← concrete values for this environment
├── .gitignore        ← excludes terraform state and plan files
└── README.md         ← this file
```
