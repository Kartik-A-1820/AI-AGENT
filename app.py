# 1) ── Imports
import asyncio
import os
from langchain_tavily import TavilySearch
from langchain.agents import AgentExecutor
from langchain.agents import create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain_experimental.tools.python.tool import PythonREPLTool
from gmail_tools import send_gmail, read_gmail
from calender_tools import create_calendar_event, list_calendar_events, delete_calendar_event, update_calendar_event, schedule_google_meet_event
from gdrive_tools import upload_drive_file, download_drive_file, list_drive_files
from image_generation_tools import generate_image_from_prompt
from media_tools import generate_omniroute_image, generate_omniroute_video, list_omniroute_media_models
from research_tools import research_topic
from file_tools import AGENT_DIR, write_to_file, read_from_file
from llm_config import create_llm
from personal_tools import add_personal_task, daily_brief, get_pc_status, list_personal_tasks, recall_context, remember, update_user_profile


TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
os.makedirs(AGENT_DIR, exist_ok=True)

llm = create_llm()


# `TavilySearchResults` returns the *content* (snippets) of the results.  
# If you prefer only URLs, use `TavilySearchResultsJson`.
search_tool = TavilySearch(tavily_api_key=TAVILY_API_KEY, max_results=5) if TAVILY_API_KEY else None

python_tool = PythonREPLTool()
tools = [
    python_tool,
    write_to_file,
    read_from_file,
    remember,
    recall_context,
    update_user_profile,
    add_personal_task,
    list_personal_tasks,
    daily_brief,
    get_pc_status,
    send_gmail,
    read_gmail,
    create_calendar_event,
    list_calendar_events,
    delete_calendar_event,
    update_calendar_event,
    schedule_google_meet_event,
    upload_drive_file,
    download_drive_file,
    list_drive_files,
    generate_image_from_prompt,
    list_omniroute_media_models,
    generate_omniroute_image,
    generate_omniroute_video,
    research_topic,
]
if search_tool:
    tools.append(search_tool)

# 5) ── Build a function-calling agent --------------------------------------------
prompt = ChatPromptTemplate.from_messages([
    ("system",         """
You are a Python expert in a sandboxed environment.
- Only read/write files inside `agent_working/`
- Never access or modify anything outside that folder
- Do NOT delete files
- Use tools for all file operations
- To create a `.docx` file, you can import the `docx` library and use its functions.
- To create a `.pptx` file, you can import the `pptx` library and use its functions.
- To create a `.csv` file, you can import the `csv` library and use its functions.
- To create a `.pdf` file, you can import the `fpdf` library and use its functions.
- Use `research_topic` for cited topic research.
- Prefer Omniroute media tools for image and video generation.
"""),
    ("user", "{input}"),
    ("ai", "{agent_scratchpad}"),
])

agent = create_tool_calling_agent(
    llm=llm,
    tools=tools,
    prompt=prompt,
)

agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    handle_parsing_errors=True,
    max_iterations=12,
)

# 6) ── Test it -------------------------------------------------------------------
if __name__ == "__main__":
    question = "Implement logistic regression with numpy and save that to file as `logistic_regression.py`. "
    result   = asyncio.run(agent_executor.ainvoke({"input": question}))
    print("\nAnswer:\n", result["output"])
