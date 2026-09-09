import asyncio
import os
import tiktoken
from langchain_tavily import TavilySearch
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain.tools import tool
from gmail_tools import send_gmail, read_gmail
from calender_tools import create_calendar_event, list_calendar_events, delete_calendar_event, update_calendar_event, schedule_google_meet_event
from gdrive_tools import upload_drive_file, download_drive_file, list_drive_files
from image_generation_tools import generate_image_from_prompt
from document_tools import create_pptx_presentation, create_docx_document
from pydantic import BaseModel, Field
from file_tools import AGENT_DIR, write_to_file, read_from_file
from llm_config import create_llm, estimate_llm_cost
from code_tools import install_python_package, run_python_code
from personal_tools import (
    add_personal_task,
    complete_personal_task,
    daily_brief,
    get_pc_status,
    list_personal_tasks,
    recall_context,
    remember,
    update_user_profile,
)
from media_tools import (
    generate_omniroute_image,
    generate_omniroute_video,
    list_omniroute_media_models,
)
from research_tools import research_topic

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.prompts import MessagesPlaceholder

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

os.makedirs(AGENT_DIR, exist_ok=True)

llm = create_llm()

# --- Token and cost tracking ---
def count_tokens(text: str) -> int:
    """Counts the number of tokens in a string."""
    encoding = tiktoken.get_encoding("cl100k_base")
    return len(encoding.encode(text))

def get_cost(prompt_tokens: int, completion_tokens: int) -> float:
    """Estimates cost when OmniRoute pricing env vars are provided."""
    return estimate_llm_cost(prompt_tokens, completion_tokens)

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
search_tool = TavilySearch(tavily_api_key=TAVILY_API_KEY, max_results=5) if TAVILY_API_KEY else None

# --- All Tools ---
tools = [
    get_current_date_time,
    run_python_code,
    install_python_package,
    write_to_file,
    read_from_file,
    remember,
    recall_context,
    update_user_profile,
    add_personal_task,
    list_personal_tasks,
    complete_personal_task,
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
    create_pptx_presentation,
    create_docx_document,
]
if search_tool:
    tools.append(search_tool)

# Prompt
prompt = ChatPromptTemplate.from_messages([
    ("system", f"""You are a full-time personal PC assistant powered by OmniRoute with tools for Google Workspace, local task memory, safe file creation, web search when configured, and sandboxed Python coding tools.
Your primary directive is to complete user requests fully and efficiently.
- You have access to Google services. Use them when appropriate.
- You have durable local memory tools. Save stable preferences, recurring facts, project context, and tasks when the user asks you to remember or track something.
- For everyday planning requests, combine local tasks, calendar, Gmail, Drive, web search, topic research, media tools, and PC status when useful.
- Before sending emails, creating/updating/deleting calendar events, uploading Drive files, or downloading Drive files, ask for confirmation unless the user gave a clear, specific instruction for that exact action in the current message.
- Only read/write files inside the `agent_working` sandbox directory. The absolute path to this directory is: {os.path.abspath(AGENT_DIR)}
- Always use current date/time tool for timestamps
- Never access or modify anything outside that folder
- Do NOT delete files, even inside the sandbox, unless the user explicitly asks for that exact sandbox file deletion.
- Use `run_python_code` for coding tasks instead of an unrestricted REPL. Scripts run from the sandbox directory.
- Use `install_python_package` when a task needs a pip package. It installs only into the assistant's dedicated virtual environment.
- Use required tools for tasks intelligently.
- You can perform many tasks using Python in the sandbox. If a specific tool is not available, write and execute Python code with `run_python_code` while keeping all files inside the sandbox.
- When creating a presentation, generate detailed and informative content for each slide. Go beyond simple bullet points; provide descriptive and well-structured text.
- For topic research, use `research_topic` to create a cited brief and save sources before drafting documents, recommendations, or content plans.
- Prefer Omniroute media generation tools for images and videos. Use `list_omniroute_media_models` when the user asks what is available.
- To create a `.pptx` file, first generate the text content for each slide. If images are required, use the `generate_omniroute_image` tool to create them and collect the file paths. Finally, use the `create_pptx_presentation` tool with the text content and the image file paths.
- To create a `.docx` file, use the `create_docx_document` tool. You can provide an optional `image_prompt` for each paragraph to automatically generate and insert images.
- To create a `.csv` file, you can import the `csv` library and use its functions.
- To create a `.pdf` file, you can import the `fpdf` library and use its functions.
- To generate an image, use `generate_omniroute_image` first. Use `generate_image_from_prompt` only when the Gemini API key is configured and Omniroute media generation is unavailable.
- Long operations are asynchronous and may take time; give progress-oriented answers and report retry exhaustion clearly.
"""),
    MessagesPlaceholder(variable_name="chat_history"),
    ("user", "{input}"),
    ("ai", "{agent_scratchpad}"),
])

# --- Memory management via summarization ---
conversation_history = []  # stores recent turns
summary = ""        # cumulative summary

async def summarize_history_async():
    global summary, conversation_history
    # Combine previous summary with recent turns
    content = f"Previous summary:\n{summary}\n\nRecent conversation:\n"
    for turn in conversation_history:
        content += f"User: {turn['user']}\nAssistant: {turn['assistant']}\n"

    result = await llm.ainvoke([
        SystemMessage(content="Please provide a concise summary of the following conversation without loosing knowledge."),
        HumanMessage(content=content)
    ])
    summary = result.content
    try:
        with open(os.path.join(AGENT_DIR, "summary.txt"), "w", encoding="utf-8") as f:
            f.write(summary)
    except Exception as e:
        print(f"[Memory Save Error] Could not write summary: {e}")
    # Clear the recent history buffer
    conversation_history = []

def summarize_history():
    asyncio.run(summarize_history_async())


async def get_agent_response_async(user_input, chat_history):
    agent = create_tool_calling_agent(
        llm=llm,
        tools=tools,
        prompt=prompt,
    )
    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=os.getenv("AI_AGENT_VERBOSE", "false").lower() == "true",
        handle_parsing_errors=True,
        max_iterations=12,
    )
    result = await agent_executor.ainvoke({"input": user_input, "chat_history": chat_history})
    response = result["output"]
    
    prompt_tokens = count_tokens(user_input)
    completion_tokens = count_tokens(response)
    cost = get_cost(prompt_tokens, completion_tokens)

    return response, prompt_tokens, completion_tokens, cost


def get_agent_response(user_input, chat_history):
    return asyncio.run(get_agent_response_async(user_input, chat_history))

# --- Reactive chat loop ---
async def main_async():
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

        response, prompt_tokens, completion_tokens, cost = await get_agent_response_async(full_input, chat_history)
        total_cost += cost
        print(f"Assistant: {response}")
        print(f"(Prompt Tokens: {prompt_tokens}, Completion Tokens: {completion_tokens}, Cost: ${cost:.6f}, Total Cost: ${total_cost:.6f})")

        # Update memory buffer
        chat_history.extend([HumanMessage(content=user_input), AIMessage(content=response)])
        conversation_history.append({"user": user_input, "assistant": response})
        # Summarize every 6 turns to keep context manageable
        if len(conversation_history) >= 5:
            await summarize_history_async()


def main():
    asyncio.run(main_async())

if __name__ == "__main__":
    main()

