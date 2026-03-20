## 2024-05-22 - SSRF in Image Proxy

**Vulnerability:** The `/api/image` endpoint blindly proxied requests to any Google Cloud Storage bucket specified in the `gcs_uri` parameter. This allowed attackers to read arbitrary files from any bucket accessible to the service account.

**Learning:** When building proxy endpoints, implicit trust in service account permissions is dangerous. A service account often has broader access than intended for a specific public endpoint. Additionally, testing redirects with `TestClient` can mask 403 Forbidden responses if they redirect to an external URL (causing a 404 Not Found from the test client), leading to false negatives in security tests.

**Prevention:** Implement strict whitelisting for resource identifiers (e.g., bucket names). Do not rely on "security by obscurity" or the hope that the service account has minimal permissions. Fail secure if the whitelist is not configured.

## 2024-03-07 - Hardcoded DB Password and Overly Permissive CORS
**Vulnerability:** A fallback database password (`Welcome01`) was hardcoded into the source code of the agent service in `backend/agent/main.py`. Additionally, the agent service used `allow_origins=["*"]` which allows cross-origin requests from any site, exposing the API to potential CSRF-like attacks from unauthorized domains.
**Learning:** Development defaults often leak into production code when default values are hardcoded in `os.environ.get()` calls or when CORS configurations are left as wildcards. This is a common pattern when quickly bootstrapping services but represents a significant security risk if deployed. The main backend service correctly used environment variables for these settings, but the agent service did not, highlighting a lack of consistency.
**Prevention:** Avoid hardcoding fallback secrets in code; require secrets to be explicitly set via environment variables. If a secret is not present, the application should fail to start or raise an error, rather than silently falling back to a known weak secret. For CORS, use a configurable allowlist via environment variables (e.g., `ALLOWED_ORIGINS`) rather than wildcards, ensuring that production environments can restrict access to trusted domains. Ensure consistency in configuration handling across all microservices.
