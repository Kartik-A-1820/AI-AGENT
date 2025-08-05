import os
import re
import dotenv
import tiktoken
from langchain_openai import ChatOpenAI
from langchain_tavily import TavilySearch
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain_experimental.tools.python.tool import PythonREPLTool
from langchain.tools import tool
from gmail_tools import send_gmail, read_gmail
from calender_tools import create_calendar_event, list_calendar_events, delete_calendar_event, update_calendar_event, schedule_google_meet_event
from gdrive_tools import upload_drive_file, download_drive_file, list_drive_files
from image_generation_tools import generate_image_from_prompt
from document_tools import create_pptx_presentation, create_docx_document
from pydantic import BaseModel, Field

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.prompts import MessagesPlaceholder
from langchain_google_genai import ChatGoogleGenerativeAI
dotenv.load_dotenv()  # expects .env in the current directory

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

if not OPENROUTER_API_KEY:
    raise RuntimeError("OPENROUTER_API_KEY not set in .env")
if not TAVILY_API_KEY:
    raise RuntimeError("TAVILY_API_KEY not set in .env")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

AGENT_DIR = "agent_working"
os.makedirs(AGENT_DIR, exist_ok=True)

# Gemini LLM initialization
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-pro",
    google_api_key=GEMINI_API_KEY
)

# --- Token and cost tracking ---
def count_tokens(text: str) -> int:
    """Counts the number of tokens in a string."""
    encoding = tiktoken.get_encoding("cl100k_base")
    return len(encoding.encode(text))

def get_cost(prompt_tokens: int, completion_tokens: int) -> float:
    """Calculates the cost of a prompt and completion."""
    # Pricing for gemini-1.5-pro-latest (per 1 million tokens)
    input_cost = 1.25
    output_cost = 5.00

    prompt_cost = (prompt_tokens / 1_000_000) * input_cost
    completion_cost = (completion_tokens / 1_000_000) * output_cost

    return prompt_cost + completion_cost

from app import write_to_file, read_from_file

class GetCurrentDateTimeInput(BaseModel):
    pass

@tool
def get_current_date_time(input_data: GetCurrentDateTimeInput) -> str:
    """
    Get the current date and time in ISO format.
    """
    from datetime import datetime
    return datetime.now().isoformat()

# --- Other tools ---
search_tool = TavilySearch(
    tavily_api_key=TAVILY_API_KEY,
    max_results=5,
)
python_tool = PythonREPLTool()

# --- All Tools ---
tools = [
    get_current_date_time,
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
    create_pptx_presentation,
    create_docx_document,
]

# Prompt
prompt = ChatPromptTemplate.from_messages([
    ("system", f"""You are a powerful assistant with a wide range of tools, including Google Workspace, web search, and a Python REPL.
Your primary directive is to complete user requests fully and efficiently.
- You have access to Google services. Use them when appropriate.
- Only read/write files inside the `agent_working` directory. The absolute path to this directory is: {os.path.abspath(AGENT_DIR)}
- Always use current date/time tool for timestamps
- Never access or modify anything outside that folder
- Do NOT delete files
- Use required tools for tasks intelligently.
- You can perform any task using Python. If a specific tool is not available, write and execute Python code to accomplish the task. Never say you don't have access or can't do something; instead, provide the Python code to solve the problem.
- When creating a presentation, generate detailed and informative content for each slide. Go beyond simple bullet points; provide descriptive and well-structured text.
- To create a `.pptx` file, first generate the text content for each slide. If images are required, use the `generate_image_from_prompt` tool to create them and collect the file paths. Finally, use the `create_pptx_presentation` tool with the text content and the image file paths.
- To create a `.docx` file, use the `create_docx_document` tool. You can provide an optional `image_prompt` for each paragraph to automatically generate and insert images.
- To create a `.csv` file, you can import the `csv` library and use its functions.
- To create a `.pdf` file, you can import the `fpdf` library and use its functions.
- To generate an image, you MUST use the `generate_image_from_prompt` tool. This is the only way you can generate images. Do not claim you cannot generate images; use the tool.
"""),
    MessagesPlaceholder(variable_name="chat_history"),
    ("user", "{input}"),
    ("ai", "{agent_scratchpad}"),
])

# --- Memory management via summarization ---
conversation_history = []  # stores recent turns
summary = ""        # cumulative summary

def summarize_history():
    global summary, conversation_history
    # Combine previous summary with recent turns
    content = f"Previous summary:\n{summary}\n\nRecent conversation:\n"
    for turn in conversation_history:
        content += f"User: {turn['user']}\nAssistant: {turn['assistant']}\n"

    summary = llm.invoke([
        SystemMessage(content="Please provide a concise summary of the following conversation without loosing knowledge."),
        HumanMessage(content=content)
    ]).content
    try:
        with open(os.path.join(AGENT_DIR, "summary.txt"), "w", encoding="utf-8") as f:
            f.write(summary)
    except Exception as e:
        print(f"[Memory Save Error] Could not write summary: {e}")
    # Clear the recent history buffer
    conversation_history = []

def get_agent_response(user_input, chat_history):
    agent = create_tool_calling_agent(
        llm=llm,
        tools=tools,
        prompt=prompt,
    )
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True) # Add verbose=True for detailed logging
    result = agent_executor.invoke({"input": user_input, "chat_history": chat_history})
    response = result["output"]
    
    prompt_tokens = count_tokens(user_input)
    completion_tokens = count_tokens(response)
    cost = get_cost(prompt_tokens, completion_tokens)

    return response, prompt_tokens, completion_tokens, cost

# --- Reactive chat loop ---
def main():
    print("Agent is running. Type 'exit' or 'quit' to stop.")
    chat_history = []
    total_cost = 0
    while True:
        user_input = input("User: ").strip()
        if user_input.lower() in ("exit", "quit"):
            # Clear memory and exit
            conversation_history.clear()
            global summary
            summary = ""
            print("Memory cleared. Exiting agent.")
            break

        # Prepend summary if available
        if summary:
            full_input = f"Summary of previous conversation:\n{summary}\n\nRecent messages:\n"
            for turn in conversation_history[-2:]:
                full_input += f"User: {turn['user']}\nAssistant: {turn['assistant']}\n"
            full_input += f"\nUser: {user_input}"
        else:
            full_input = user_input

        response, prompt_tokens, completion_tokens, cost = get_agent_response(full_input, chat_history)
        total_cost += cost
        print(f"Assistant: {response}")
        print(f"(Prompt Tokens: {prompt_tokens}, Completion Tokens: {completion_tokens}, Cost: ${cost:.6f}, Total Cost: ${total_cost:.6f})")

        # Update memory buffer
        chat_history.extend([HumanMessage(content=user_input), AIMessage(content=response)])
        conversation_history.append({"user": user_input, "assistant": response})
        # Summarize every 6 turns to keep context manageable
        if len(conversation_history) >= 5:
            summarize_history()

if __name__ == "__main__":
    main()

