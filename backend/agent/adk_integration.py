from typing import Dict, Any

# In a real ADK setup, you would import the ADK Agent and Tool classes here.
# For this demonstration, we are mocking the ADK Agent structure to show the 
# "Dynamic Single Agent" architecture pattern.

class MockADKTool:
    def __init__(self, name: str, description: str, func: callable):
        self.name = name
        self.description = description
        self.func = func

class MockADKAgent:
    def __init__(self, name: str, instructions: str, tools: list):
        self.name = name
        self.instructions = instructions
        self.tools = tools
        
    def invoke(self, user_message: str) -> str:
        # Mocking the LLM deciding to use the tool
        print(f"[Agent {self.name}] Received message: {user_message}")
        if self.tools:
            tool = self.tools[0]
            print(f"[Agent {self.name}] Using tool: {tool.name}")
            # In reality, the LLM extracts arguments. Here we just pass the message.
            result = tool.func(user_message)
            return f"Agent processed result from {tool.name}: {result.get('naturalLanguageAnswer', 'No answer')}"
        return "I don't have any tools to help with that."

def get_dynamic_adk_agent(selected_backend: str) -> MockADKAgent:
    """
    Instantiates an ADK Chat Agent on the fly, injecting ONLY the MCP tool 
    corresponding to the selected database backend.
    
    This is the "Dynamic Single Agent" approach:
    - Pros: No prompt bloat, zero chance of the LLM selecting the wrong database tool.
    - Cons: Agent must be instantiated per request (usually very fast).
    """
    
    # 1. Define the tool function that wraps the GDA call for the specific backend
    def query_active_database(prompt: str) -> Dict[str, Any]:
        """
        Tool implementation that calls the GDA API.
        In a real implementation, this would import and call `query_gda(prompt, selected_backend)`
        from main.py.
        """
        print("--- Executing Tool: query_active_database ---")
        print(f"--- Routing to Backend: {selected_backend.upper()} ---")
        
        # Mocking the GDA response for demonstration
        return {
            "naturalLanguageAnswer": f"Here are the results from {selected_backend.upper()}.",
            "queryResult": {"rows": [], "columns": []}
        }

    # 2. Create the single MCP tool
    db_tool = MockADKTool(
        name="query_property_database",
        description=f"Queries the active property database ({selected_backend}) to find real estate listings based on user criteria.",
        func=query_active_database
    )
    
    # 3. Instantiate and return the Agent
    agent = MockADKAgent(
        name="PropertySearchAssistant",
        instructions="""
        You are a helpful real estate assistant in Switzerland. 
        You have access to a tool that queries the property database.
        Always use the tool to answer questions about available properties.
        """,
        tools=[db_tool]
    )
    
    return agent

# --- Example Usage ---
if __name__ == "__main__":
    print("=== Testing Dynamic Single Agent Architecture ===")
    
    # Scenario 1: User is on the AlloyDB tab
    print("\n[Scenario 1: Frontend sends selectedBackend='alloydb']")
    agent_alloydb = get_dynamic_adk_agent("alloydb")
    response1 = agent_alloydb.invoke("Find me a 2 bedroom in Zurich")
    print(f"Final Response: {response1}")
    
    # Scenario 2: User switches to the Spanner tab
    print("\n[Scenario 2: Frontend sends selectedBackend='spanner']")
    agent_spanner = get_dynamic_adk_agent("spanner")
    response2 = agent_spanner.invoke("Find me a 2 bedroom in Zurich")
    print(f"Final Response: {response2}")
