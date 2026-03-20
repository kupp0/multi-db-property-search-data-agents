## 2024-05-22 - SSRF in Image Proxy

**Vulnerability:** The `/api/image` endpoint blindly proxied requests to any Google Cloud Storage bucket specified in the `gcs_uri` parameter. This allowed attackers to read arbitrary files from any bucket accessible to the service account.

**Learning:** When building proxy endpoints, implicit trust in service account permissions is dangerous. A service account often has broader access than intended for a specific public endpoint. Additionally, testing redirects with `TestClient` can mask 403 Forbidden responses if they redirect to an external URL (causing a 404 Not Found from the test client), leading to false negatives in security tests.

**Prevention:** Implement strict whitelisting for resource identifiers (e.g., bucket names). Do not rely on "security by obscurity" or the hope that the service account has minimal permissions. Fail secure if the whitelist is not configured.
