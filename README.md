# Urumi MCP Platform

A Kubernetes-native, multi-user MCP (Model Context Protocol) gateway featuring a self-written WooCommerce MCP server, a React admin dashboard, and an AI chat agent powered by Sarvam AI. 

This platform allows AI agents and external MCP clients to securely interact with a WooCommerce store, manage upstream MCP servers, and maintain a strict audit trail of all tool executions.

---

## 🏗️ Architecture Overview

The system is composed of four main components running inside a Kubernetes cluster:

1. **The Store**: WordPress + WooCommerce + MariaDB (deployed via Bitnami Helm chart).
2. **Woo-MCP Server**: A self-written Python FastMCP server that translates MCP tool calls into WooCommerce REST API requests using OAuth 1.0a.
3. **Gateway Backend**: The core switchboard. It runs two services in one pod:
   - **MCP Endpoint (:8001)**: Aggregates tools from all registered upstream servers.
   - **REST API (:8000)**: Manages users, servers, and audit logs for the dashboard.
   - *Shared Storage*: A SQLite database on a Persistent Volume Claim (PVC).
4. **Frontend Dashboard**: A React SPA served by Nginx, providing a UI for admin control and the AI chat agent.

Traffic enters the cluster via an Nginx Ingress Controller, routing to stable URLs (`dashboard.*`, `api.*`, `mcp.*`, `store.*`).

---

## 🚀 Local Setup (Kind)

### Prerequisites
- Docker Desktop
- `kind`, `kubectl`, `helm` installed and configured.

### 1. Create the Local Cluster
```bash
kind create cluster --name urumi-local --config kind-config.yaml
```

### 2. Install Ingress Controller
```bash
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml
kubectl wait --namespace ingress-nginx \
  --for=condition=ready pod \
  --selector=app.kubernetes.io/component=controller \
  --timeout=90s
```

### 3. Deploy the WooCommerce Store
```bash
kubectl create namespace store
helm upgrade --install urumi-store helm/store -n store -f helm/store/values-local.yaml
```
*(Wait for WordPress and MariaDB pods to be `1/1 Running`)*.

### 4. Build and Load Docker Images
```bash
docker build -t woo-mcp-server:latest src/woo-mcp-server/
docker build -t gateway-backend:latest src/gateway-backend/
docker build -t frontend:latest frontend/

kind load docker-image woo-mcp-server:latest --name urumi-local
kind load docker-image gateway-backend:latest --name urumi-local
kind load docker-image frontend:latest --name urumi-local
```

### 5. Deploy Application Components
```bash
helm upgrade --install woo-mcp-server helm/woo-mcp-server -n store -f helm/woo-mcp-server/values-local.yaml
helm upgrade --install gateway helm/gateway -n store -f helm/gateway/values-local.yaml
helm upgrade --install frontend helm/frontend -n store -f helm/frontend/values-local.yaml
```

### 6. Retrieve API Keys
The gateway seeds an `admin` and a `member` user on first boot.
```bash
kubectl logs -n store -l app=gateway -c seed-db | grep "API KEY"
```
*Save both keys. The Admin key is for the dashboard/chat. The Member key is for external MCP clients (User B).*

---

## 🌍 Production Setup (k3s / VPS)

The same Helm charts are used for production. Create a `values-prod.yaml` that overrides `values-local.yaml`:

1. **Domains**: Replace `127.0.0.1.nip.io` with your actual domains.
2. **TLS**: Install `cert-manager` and add TLS blocks to the Ingress resources.
3. **Storage**: Change the StorageClass from `standard` to a cloud provider class (e.g., `gp2`, `rook-ceph`).
4. **Database**: For production, migrate the gateway's SQLite to PostgreSQL (requires updating `database.py` and `requirements.txt`).
5. **Secrets**: Move API keys to an External Secrets Operator or HashiCorp Vault.

```bash
helm upgrade --install gateway helm/gateway -n store -f helm/gateway/values-prod.yaml
```

---

## 🎬 End-to-End Demo Guide

This guide satisfies the project's Definition of Done.

### 1. Storefront Checkout
- Open `http://store.127.0.0.1.nip.io`.
- Add a product to the cart and checkout (Cash on Delivery is enabled).
- Log into WordPress Admin (`http://store.127.0.0.1.nip.io/wp-admin`) and verify the order exists.

### 2. Chat Agent (User A - Admin)
- Open `http://dashboard.127.0.0.1.nip.io` and log in with the **Admin API Key**.
- Navigate to the **Chat Agent**.
- Prompt: *"Create a new product called Urumi Mug for 499"*.
- Verify the product appears on the storefront.
- Place a manual order for it on the storefront.
- Prompt the agent: *"What orders came in today?"*. The agent will query the store and summarize the new order.

### 3. External MCP Client (User B - Member)
- Open **MCP Inspector** (or Cursor/Claude Code).
- Configure the connection to `http://mcp.127.0.0.1.nip.io/mcp` (Streamable HTTP).
- Add a custom header: `Authorization: Bearer <MEMBER_API_KEY>`.
- Connect and **List Tools**. You will see tools from all 3 registered upstream servers.
- Run `woo-mcp__list_orders`. 

### 4. Team and Control
- **Audit Log**: In the dashboard, view the Audit Log. You will see the Chat Agent's calls attributed to `admin` and the Inspector's calls attributed to `member`.
- **Revocation**: Use the API to revoke User B's key. Their next MCP call will instantly fail with `401 Unauthorized`.
- **Isolation**: Toggle the `woo-mcp` server to **DISABLED** in the dashboard. Its tools instantly vanish from both the Chat Agent and the Inspector.
- **Resilience**: Kill the upstream pod: `kubectl delete pod -l app=woo-mcp -n store`. The gateway remains healthy, other servers' tools still work, and failed calls are logged with a clear timeout/error message.

---

## 📐 System Design and Tradeoffs

### Architecture Choices
- **Streamable HTTP**: Chosen over SSE for the MCP transport as it is the modern, stateless standard for MCP, allowing easier load balancing and proxying through Nginx.
- **WooCommerce REST vs WP-CLI**: REST was chosen because it operates over standard HTTP with OAuth 1.0a signing, making it ideal for cross-pod communication. WP-CLI requires direct filesystem/DB access or `kubectl exec`, which is brittle for an MCP server.

### Tool Aggregation & Routing
- **Prefixing**: To prevent tool name collisions between different upstream servers, the gateway prefixes all tools with `<server_name>__<tool_name>` (e.g., `woo-mcp__list_products`). 
- **Routing**: At call time, the gateway splits the prefix, identifies the target upstream, and proxies the JSON-RPC request.

### Failure Handling
- **Timeouts**: Every upstream call is wrapped in a strict `asyncio.timeout(10)`. A dead or slow upstream cannot hang the gateway.
- **Graceful Degradation**: If an upstream fails during `list_tools`, the gateway catches the exception and returns the tools from the remaining healthy servers, ensuring the client always gets a partial response rather than a total failure.

---

## 🛡️ Threat Model

### Shared Upstream Credentials
- **Risk**: The WooCommerce Consumer Key/Secret is highly privileged.
- **Mitigation**: Credentials are stored in a Kubernetes Secret and mounted *only* into the `woo-mcp-server` pod. Members and external clients never see them. They can only execute the specific tools the gateway exposes.

### Client Token Isolation
- **Risk**: Passing client tokens directly to upstreams could leak identity or require complex OAuth proxying.
- **Mitigation**: The gateway acts as a credential vault. Clients authenticate to the gateway with their API key. The gateway then uses its own upstream credentials to make the call, attributing the action to the client in the audit log.

### Untrusted Upstreams
- **Risk**: A compromised upstream could return malicious tool descriptions to jailbreak the LLM.
- **Mitigation**: Upstreams are strictly registered by Admins only. The gateway treats tool descriptions as untrusted data, and the Agent's system prompt is hardened to prioritize user intent over tool instructions.

### Team Member Isolation
- **Risk**: A member attempting to access admin functions or other users' data.
- **Mitigation**: 
  - **RBAC**: REST endpoints enforce strict role checks (`admin` vs `member`).
  - **Cryptographic Security**: API keys are hashed using `bcrypt` before storage. Even if the database is compromised, raw keys cannot be recovered.
  - **Auditability**: Every action is immutably logged with a timestamp, user ID, and outcome.

---

## 📂 Project Structure

```text
urumi-mcp-platform/
── helm/                  # Helm charts for all components
│   ├── store/             # Bitnami WordPress/MariaDB
│   ├── woo-mcp-server/    # Custom WooCommerce MCP server
│   ├── gateway/           # Backend API + MCP Switchboard
│   └── frontend/          # React Dashboard + Chat UI
── src/
│   ├── woo-mcp-server/    # Python source for WooCommerce MCP
│   ── gateway-backend/   # Python source for Gateway, Auth, Agent
├── frontend/              # React/Vite source code
├── kind-config.yaml       # Kind cluster configuration
├── SYSTEM_DESIGN.md       # Detailed architecture notes
└── THREAT_MODEL.md        # Detailed security analysis
```