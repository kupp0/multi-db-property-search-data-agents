## 2024-05-24 - Hardcoded database password
**Vulnerability:** A hardcoded database password ("Welcome01") was present in the application code as a fallback default when the environment variable was not set (`DB_PASSWORD = os.environ.get("DB_PASSWORD", "Welcome01")`).
**Learning:** Default fallback values for sensitive secrets like passwords can result in hardcoded secrets in the codebase, leading to security vulnerabilities. Even as fallbacks, sensitive information should not be committed.
**Prevention:** Only use environment variables for sensitive configuration settings, without providing hardcoded default values in the code.
