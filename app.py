# 1) ── Imports
import os
import dotenv
from langchain_openai import ChatOpenAI
from langchain_tavily import TavilySearch
from langchain.agents import AgentExecutor
from langchain.agents import create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain_experimental.tools.python.tool import PythonREPLTool
from langchain.tools import tool
from gmail_tools import send_gmail, read_gmail
from calender_tools import create_calendar_event, list_calendar_events, delete_calendar_event, update_calendar_event, schedule_google_meet_event
from gdrive_tools import upload_drive_file, download_drive_file, list_drive_files
from image_generation_tools import generate_image_from_prompt




dotenv.load_dotenv()                       # expects .env in the current directory

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
TAVILY_API_KEY    = os.getenv("TAVILY_API_KEY")

if not OPENROUTER_API_KEY:
    raise RuntimeError("OPENROUTER_API_KEY not set in .env")
if not TAVILY_API_KEY:
    raise RuntimeError("TAVILY_API_KEY not set in .env")

AGENT_DIR = "agent_working"
os.makedirs(AGENT_DIR, exist_ok=True)

# The model on OpenRouter is accessed exactly like an OpenAI model, just with a custom base_url.
llm = ChatOpenAI(
    model_name="deepseek/deepseek-chat-v3-0324:free",
    base_url="https://openrouter.ai/api/v1",
    openai_api_key=OPENROUTER_API_KEY,
    temperature=0.2,                         # ↳ lower temperature = more deterministic
    timeout=60,
)

@tool
def write_to_file(filename: str, content: str) -> str:
    """
    Writes text content to a file within the 'agent_working' directory.
    """
    filepath = os.path.abspath(os.path.join(AGENT_DIR, filename))
    working_dir = os.path.abspath(AGENT_DIR)

    if not filepath.startswith(working_dir):
        return "Error: Attempt to write outside agent_working is not allowed."

    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Successfully wrote to {filename}."
    except Exception as e:
        return f"Write failed: {str(e)}"
    
@tool
def read_from_file(filename: str) -> str:
    """
    Reads the contents of a file from 'agent_working'.
    """
    filepath = os.path.abspath(os.path.join(AGENT_DIR, filename))
    working_dir = os.path.abspath(AGENT_DIR)

    if not filepath.startswith(working_dir):
        return "Error: Attempt to read outside agent_working is not allowed."

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Read failed: {str(e)}"
    


# `TavilySearchResults` returns the *content* (snippets) of the results.  
# If you prefer only URLs, use `TavilySearchResultsJson`.
search_tool = TavilySearch(
    tavily_api_key=TAVILY_API_KEY,
    max_results=5,                # tweak as you like
)

python_tool = PythonREPLTool()
tools = [
    search_tool,
    python_tool,
    write_to_file,
    read_from_file,
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
]

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
"""),
    ("user", "{input}"),
    ("ai", "{agent_scratchpad}"),
])

agent = create_tool_calling_agent(
    llm=llm,
    tools=tools,
    prompt=prompt,
)

agent_executor = AgentExecutor(agent=agent, tools=tools)

# 6) ── Test it -------------------------------------------------------------------
if __name__ == "__main__":
    question = "Implement logistic regression with numpy and save that to file as `logistic_regression.py`. "
    result   = agent_executor.invoke({"input": question})
    print("\nAnswer:\n", result["output"])
