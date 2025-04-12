# Weather Agent using Google ADK (Agent development Kit)

This is a multiagent Weather Retreival Bot.
It consists of a root agent, that handles the weather retrieval using OpenWeather API and two sub agents that are for greeting and farewell.

This is meant to be a fun experiment. :D

LLM used: Google's gemini-2.0-flash-exp
Weather API: OpenWeather API

check statefulagent.py

To run the bot: 
1. in .env file declare API keys: a. GOOGLE_API_KEY b. OPENWEATHER_API_KEY c. GOOGLE_GENAI_USE_VERTEXAI="False"
2. run script statefulagent.py 


reference: https://google.github.io/adk-docs/get-started/tutorial/




