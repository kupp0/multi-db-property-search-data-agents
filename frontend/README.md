# Unified Data Cloud Property Search Frontend

This is the React frontend for the Unified Data Cloud Property Search Demo. It provides a modern, responsive UI for users to interact with the Gemini Data Agent across three different database backends: AlloyDB, Cloud Spanner, and Cloud SQL for PostgreSQL.

## Features

*   **3-Way Database Toggle**: Seamlessly switch between the active database backend to compare performance and SQL dialects.
*   **Natural Language Search**: A search bar for entering natural language queries.
*   **System Output View**: Displays the generated SQL, natural language answer, intent explanation, and a preview of the raw query results.
*   **Property Listings Grid**: Displays the property results with images served securely from Google Cloud Storage.
*   **ADK Chat Interface**: A floating chat window to interact with the dynamic ADK Chat Agent for follow-up questions.
*   **User History Widget**: A slide-out panel to view past prompts and the templates used.
*   **Architecture Modal**: Visual diagrams explaining the system architecture and data agent context.
*   **Dark Mode**: Built-in support for dark and light themes.

## Development

The frontend is built with React, Vite, and Tailwind CSS.

To run locally (usually handled by `scripts/debug_local.sh` from the project root):

```bash
npm install
npm run dev
```
