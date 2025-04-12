import datetime
import asyncio
import os
from dotenv import load_dotenv
from zoneinfo import ZoneInfo
from google.adk.agents import Agent
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from google.genai import types
from google.adk.tools.tool_context import ToolContext

load_dotenv()
agent_model = "gemini-2.0-flash-exp"

#defining the tools:
def say_hello(name:str="there") -> str:
    """Provides a simple greeting,optionally addressing the user by name.
    Args:
        name (str,optional): The name of the person to greet. Defaults to "there".
    Returns:
    str: A friendly greeting message.
    """
    print(f"--- Tool: say_hello called with name: {name} ---")
    return f"Hello, {name}!"

def say_goodbye() -> str:
    """Provides a simple farewell message to conclude the conversation."""
    print(f"--- Tool: say_goodbye called ---")
    return "Goodbye!Have a great day."

def get_weather_stateful(city: str, tool_context: ToolContext) -> dict:
    """Retrieves weather, converts temp unit based on session state."""
    print(f"--- Tool: get_weather_stateful called for {city} ---")

    # --- Read preference from state ---
    preferred_unit = tool_context.state.get("user_preference_temperature_unit", "Celsius") 
    print(f"--- Tool: Reading state 'user_preference_temperature_unit': {preferred_unit} ---")

    city_normalized = city.lower().replace(" ", "")

    
    mock_weather_db = {
        "newyork": {"temp_c": 25, "condition": "sunny"},
        "london": {"temp_c": 15, "condition": "cloudy"},
        "tokyo": {"temp_c": 18, "condition": "light rain"},
    }

    if city_normalized in mock_weather_db:
        data = mock_weather_db[city_normalized]
        temp_c = data["temp_c"]
        condition = data["condition"]

        
        if preferred_unit == "Fahrenheit":
            temp_value = (temp_c * 9/5) + 32 
            temp_unit = "°F"
        else: 
            temp_value = temp_c
            temp_unit = "°C"

        report = f"The weather in {city.capitalize()} is {condition} with a temperature of {temp_value:.0f}{temp_unit}."
        result = {"status": "success", "report": report}
        print(f"--- Tool: Generated report in {preferred_unit}. Result: {result} ---")

        
        tool_context.state["last_city_checked_stateful"] = city
        print(f"--- Tool: Updated state 'last_city_checked_stateful': {city} ---")

        return result
    else:
        error_msg = f"Sorry, I don't have weather information for '{city}'."
        print(f"--- Tool: City '{city}' not found. ---")
        return {"status": "error", "error_message": error_msg}

print("✅ State-aware 'get_weather_stateful' tool defined.")
def get_weather(city: str) -> dict:
    """Retrieves the current weather report for a particular city.

    Args:
        city (str) : The name of the city (e.g., "New York","London","Tokyo").
    
    Returns:
        dict: A dictionary containing the weather information.
                Includes a 'status' key ('success' or 'error').
                If 'success', includes a 'report' key with eather details.
                if 'error', includes an 'error_message' key.
    """
    print(f"--- Tool: get_weather called for city: {city} ---")
    city_normalized = city.lower().replace(" ","")

    mock_weather_db = {
        "newyork": {"status": "success", "report": "The weather in New York is sunny with a temperature of 25°C."},
        "london": {"status": "success", "report": "It's cloudy in London with a temperature of 15°C."},
        "tokyo": {"status": "success", "report": "Tokyo is experiencing light rain and a temperature of 18°C."},
    }

    if city_normalized in mock_weather_db:
        return mock_weather_db[city_normalized]
    else:
        return {"status":"error","error_message":f"Sorry, i don't have the weather data for '{city}'"}
    
#defining the agent:

greeting_agent = Agent(
        model=agent_model,
        name="greeting_agent",
        instruction="You are the Greeting Agent. Your ONLY task is to provide a friendly greeting to the user. "
                    "Use the 'say_hello' tool to generate the greeting. "
                    "If the user provides their name, make sure to pass it to the tool. "
                    "Do not engage in any other conversation or tasks.",
        description="Handles simple greetings and hellos using the 'say_hello' tool.", 
        tools=[say_hello],
    )
print(f"✅ Agent '{greeting_agent.name}' created using model '{agent_model}'.")

farewell_agent = Agent(
        model=agent_model,
        name="farewell_agent",
        instruction="You are the Farewell Agent. Your ONLY task is to provide a polite goodbye message. "
                    "Use the 'say_goodbye' tool when the user indicates they are leaving or ending the conversation "
                    "(e.g., using words like 'bye', 'goodbye', 'thanks bye', 'see you'). "
                    "Do not perform any other actions.",
        description="Handles simple farewells and goodbyes using the 'say_goodbye' tool.", 
        tools=[say_goodbye],
    )
print(f"✅ Agent '{farewell_agent.name}' created using model '{agent_model}'.")

if greeting_agent and farewell_agent and 'get_weather' in globals():
    weather_agent_team = Agent(
    name="weather_agent_v2",
    model = agent_model,
    description="The ain coordinator. Handles weather requests and delegates greetings/farewells to specialists",
    instruction="You are the main Weather Agent coordinating a team. Your primary responsibility is to provide weather information. "
                    "Use the 'get_weather' tool ONLY for specific weather requests (e.g., 'weather in London'). "
                    "You have specialized sub-agents: "
                    "1. 'greeting_agent': Handles simple greetings like 'Hi', 'Hello'. Delegate to it for these. "
                    "2. 'farewell_agent': Handles simple farewells like 'Bye', 'See you'. Delegate to it for these. "
                    "Analyze the user's query. If it's a greeting, delegate to 'greeting_agent'. If it's a farewell, delegate to 'farewell_agent'. "
                    "If it's a weather request, handle it yourself using 'get_weather'. "
                    "For anything else, respond appropriately or state you cannot handle it.",
        tools=[get_weather], 
        sub_agents=[greeting_agent, farewell_agent]
)
    print(f"✅ Root Agent '{weather_agent_team.name}' created using model '{agent_model}' with sub-agents: {[sa.name for sa in weather_agent_team.sub_agents]}")

else:
    print("❌ Cannot create root agent because one or more sub-agents failed to initialize or 'get_weather' tool is missing.")
    if not greeting_agent: print(" - Greeting Agent is missing.")
    if not farewell_agent: print(" - Farewell Agent is missing.")
    if 'get_weather' not in globals(): print(" - get_weather function is missing.")







#creating session service and runner


root_agent_var_name = 'weather_agent_team'
if root_agent_var_name in globals() and globals()[root_agent_var_name]:
        session_service = InMemorySessionService()
        APP_NAME = "weather_tutorial_agent_team"
        USER_ID = "user_1_agent_team"
        SESSION_ID = "session_001_agent_team"

        session = session_service.create_session(
            app_name=APP_NAME,
            user_id=USER_ID,
            session_id=SESSION_ID
        )
        print(f"Session created: App='{APP_NAME}', User='{USER_ID}', Session='{SESSION_ID}'")
        actual_root_agent = globals()[root_agent_var_name]

        runner_agent_team = Runner(
            agent=actual_root_agent, 
            app_name=APP_NAME,       
            session_service=session_service 
            )
        print(f"Runner created for agent '{actual_root_agent.name}'.")
else:
    print("\n⚠️ Skipping agent team conversation as the root agent was not successfully defined in the previous step.")

#interacting with agent:
async def call_agent_async(query:str):
    """Sends a query to the agent and prints the final response."""
    print(f"\n>>>User Query: {query}")

    content = types.Content(role='user',parts=[types.Part(text=query)])

    final_response_text = "Agent did not produce a final response."

    async for event in runner_agent_team.run_async(user_id=USER_ID,session_id=SESSION_ID,new_message=content):
        # print(f"  [Event] Author: {event.author}, Type: {type(event).__name__}, Final: {event.is_final_response()}, Content: {event.content}")
        if event.is_final_response():
            if event.content and event.content.parts:
                final_response_text = event.content.parts[0].text
            elif event.actions and event.actions.escalate:
                final_response_text = f"Agent escalated: {event.error_message or 'No specific message.'}"
            break
    print(f"<<< Agent Response: {final_response_text}")       







async def run_conversation():
    await call_agent_async("Hello there!")
    await call_agent_async("What is the weather like in London?")
    await call_agent_async("Thanks, bye!")

asyncio.run(run_conversation())