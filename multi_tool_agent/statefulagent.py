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
import requests

load_dotenv()
WEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
agent_model = "gemini-2.0-flash-exp"
APP_NAME = "weather_tutorial_agent_team"

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

    
    preferred_unit = tool_context.state.get("user_preference_temperature_unit", "Celsius") 
    print(f"--- Tool: Reading state 'user_preference_temperature_unit': {preferred_unit} ---")

    city_normalized = city.lower().replace(" ", "")

    #--------------------------------------------------------
    lat = 0
    lon = 0
    url = "http://api.openweathermap.org/geo/1.0/direct"
    params = {
        "q": city,
        "limit": 2,
        "appid": WEATHER_API_KEY
    }

    response = requests.get(url, params=params)

    if response.status_code == 200:
        data = response.json()
        if data:
            lat = data[0]['lat']
            lon = data[0]['lon']
    else:
        error_msg = f"Sorry, I don't have weather information for '{city}'."
        print(f"--- Tool: City '{city}' not found. ---")
        return {"status": "error", "error_message": error_msg}
    



    weather_url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "lat": lat,
        "lon": lon,
        "appid": WEATHER_API_KEY,
        "units": "metric" 

    }

    response = requests.get(weather_url, params=params)
    if response.status_code == 200:
        data = response.json()
        weather = data['weather'][0]['description']
        temp = data['main']['temp']
    else:
        error_msg = f"Sorry, I don't have weather information for '{city}'."
        print(f"--- Tool: City '{city}' not found. ---")
        return {"status": "error", "error_message": error_msg}

    #--------------------------------------------------------
    

    
    

    if temp:
        temp_c = temp
        condition = weather

        
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

#creating stateful session and memory
session_service_stateful = InMemorySessionService()
print("✅ New InMemorySessionService created for state demonstration.")

SESSION_ID_STATEFUL = "session_state_demo_001"
USER_ID_STATEFUL = "user_state_demo"

initial_state = {
    "user_preference_temperature_unit": "Celsius"
}
session_stateful = session_service_stateful.create_session(
    app_name=APP_NAME, 
    user_id=USER_ID_STATEFUL,
    session_id=SESSION_ID_STATEFUL,
    state=initial_state 
)

print(f"✅ Session '{SESSION_ID_STATEFUL}' created for user '{USER_ID_STATEFUL}'.")

retrieved_session = session_service_stateful.get_session(app_name=APP_NAME,
                                                         user_id=USER_ID_STATEFUL,
                                                         session_id = SESSION_ID_STATEFUL)
print("\n--- Initial Session State ---")
if retrieved_session:
    print(retrieved_session.state)
else:
    print("Error: Could not retrieve session.")


#defining agents
greeting_agent = None
try:
    greeting_agent = Agent(
        model=agent_model,
        name="greeting_agent",
        instruction="You are the Greeting Agent. Your ONLY task is to provide a friendly greeting using the 'say_hello' tool. Do nothing else.",
        description="Handles simple greetings and hellos using the 'say_hello' tool.",
        tools=[say_hello],
    )
    print(f"✅ Agent '{greeting_agent.name}' redefined.")
except Exception as e:
    print(f"❌ Could not redefine Greeting agent. Error: {e}")


farewell_agent = None
try:
    farewell_agent = Agent(
        model=agent_model,
        name="farewell_agent",
        instruction="You are the Farewell Agent. Your ONLY task is to provide a polite goodbye message using the 'say_goodbye' tool. Do not perform any other actions.",
        description="Handles simple farewells and goodbyes using the 'say_goodbye' tool.",
        tools=[say_goodbye],
    )
    print(f"✅ Agent '{farewell_agent.name}' redefined.")
except Exception as e:
    print(f"❌ Could not redefine Farewell agent. Error: {e}")


root_agent_stateful = None
runner_root_stateful = None 


if greeting_agent and farewell_agent and 'get_weather_stateful' in globals():

    root_agent_model = agent_model

    root_agent_stateful = Agent(
        name="weather_agent_v4_stateful", 
        model=root_agent_model,
        description="Main agent: Provides weather (state-aware unit), delegates greetings/farewells, saves report to state.",
        instruction="You are the main Weather Agent. Your job is to provide weather using 'get_weather_stateful'. "
                    "The tool will format the temperature based on user preference stored in state. "
                    "Delegate simple greetings to 'greeting_agent' and farewells to 'farewell_agent'. "
                    "Handle only weather requests, greetings, and farewells.",
        tools=[get_weather_stateful], 
        sub_agents=[greeting_agent, farewell_agent], 
        output_key="last_weather_report" 
    )
    print(f"✅ Root Agent '{root_agent_stateful.name}' created using stateful tool and output_key.")

    runner_root_stateful = Runner(
        agent=root_agent_stateful,
        app_name=APP_NAME,
        session_service=session_service_stateful 
    )
    print(f"✅ Runner created for stateful root agent '{runner_root_stateful.agent.name}' using stateful session service.")

else:
    print("❌ Cannot create stateful root agent. Prerequisites missing.")
    if not greeting_agent: print(" - greeting_agent definition missing.")
    if not farewell_agent: print(" - farewell_agent definition missing.")
    if 'get_weather_stateful' not in globals(): print(" - get_weather_stateful tool missing.")


async def call_agent_async(query:str,runner,user_Id,session_Id):
    """Sends a query to the agent and prints the final response."""
    print(f"\n>>>User Query: {query}")

    content = types.Content(role='user',parts=[types.Part(text=query)])

    final_response_text = "Agent did not produce a final response."

    async for event in runner.run_async(user_id=user_Id,session_id=session_Id,new_message=content):
        # print(f"  [Event] Author: {event.author}, Type: {type(event).__name__}, Final: {event.is_final_response()}, Content: {event.content}")
        if event.is_final_response():
            if event.content and event.content.parts:
                final_response_text = event.content.parts[0].text
            elif event.actions and event.actions.escalate:
                final_response_text = f"Agent escalated: {event.error_message or 'No specific message.'}"
            break
    print(f"<<< Agent Response: {final_response_text}")  






if 'runner_root_stateful' in globals() and runner_root_stateful:
  async def run_stateful_conversation():
      print("\n--- Testing State: Temp Unit Conversion & output_key ---")


      print("--- Turn 1: Requesting weather in London (expect Celsius) ---")
      await call_agent_async(query= "What's the weather in London?",
                             runner=runner_root_stateful,
                             user_Id=USER_ID_STATEFUL,
                             session_Id=SESSION_ID_STATEFUL
                            )


      print("\n--- Manually Updating State: Setting unit to Fahrenheit ---")
      try:
          
          stored_session = session_service_stateful.sessions[APP_NAME][USER_ID_STATEFUL][SESSION_ID_STATEFUL]
          stored_session.state["user_preference_temperature_unit"] = "Fahrenheit"
          print(f"--- Stored session state updated. Current 'user_preference_temperature_unit': {stored_session.state['user_preference_temperature_unit']} ---")
      except KeyError:
          print(f"--- Error: Could not retrieve session '{SESSION_ID_STATEFUL}' from internal storage for user '{USER_ID_STATEFUL}' in app '{APP_NAME}' to update state. Check IDs and if session was created. ---")
      except Exception as e:
           print(f"--- Error updating internal session state: {e} ---")


      print("\n--- Turn 2: Requesting weather in New York (expect Fahrenheit) ---")
      await call_agent_async(query= "Tell me the weather in New York.",
                             runner=runner_root_stateful,
                             user_Id=USER_ID_STATEFUL,
                             session_Id=SESSION_ID_STATEFUL
                            )


      print("\n--- Turn 3: Sending a greeting ---")
      await call_agent_async(query= "Hi!",
                             runner=runner_root_stateful,
                             user_Id=USER_ID_STATEFUL,
                             session_Id=SESSION_ID_STATEFUL
                            )

 
  asyncio.run(run_stateful_conversation())
 

 
  print("\n--- Inspecting Final Session State ---")
  final_session = session_service_stateful.get_session(app_name=APP_NAME,
                                                       user_id= USER_ID_STATEFUL,
                                                       session_id=SESSION_ID_STATEFUL)
  if final_session:
      print(f"Final Preference: {final_session.state.get('user_preference_temperature_unit')}")
      print(f"Final Last Weather Report (from output_key): {final_session.state.get('last_weather_report')}")
      print(f"Final Last City Checked (by tool): {final_session.state.get('last_city_checked_stateful')}")

  else:
      print("\n❌ Error: Could not retrieve final session state.")

else:
  print("\n⚠️ Skipping state test conversation. Stateful root agent runner ('runner_root_stateful') is not available.")


