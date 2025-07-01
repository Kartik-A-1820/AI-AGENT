# Gemini Powered AI Agent

This project is a powerful, interactive AI agent that leverages the capabilities of Google's Gemini models to perform a wide range of tasks. It's designed to be a versatile assistant that can be controlled through a command-line interface (CLI) or a Streamlit-based graphical user interface (GUI).

## Key Features

- **Multi-Modal LLM:** Powered by the `gemini-1.5-pro-latest` model, the agent can understand and process both text and images.
- **Extensive Toolset:** The agent is equipped with a rich set of tools, enabling it to interact with various services and perform complex actions:
    - **Google Workspace:** Seamlessly integrates with Gmail, Google Calendar, and Google Drive to manage your digital life.
    - **Web Search:** Utilizes Tavily to find up-to-date information on the web.
    - **Image Generation:** Creates images from text prompts using the latest Gemini image generation models.
    - **Document Creation:** Can create professional-looking PowerPoint presentations and Word documents with both text and images.
    - **Code Execution:** A built-in Python REPL allows the agent to write and execute code to solve problems.
    - **File Management:** Can read and write files within a sandboxed `agent_working` directory.
- **Conversational Memory:** Maintains a summary of the conversation, allowing it to retain context over longer interactions.
- **Cost Tracking:** Monitors token usage and provides a cost breakdown for each interaction.
- **Secure and Sandboxed:** All file operations are restricted to the `agent_working` directory to ensure the safety of your local files.

## Project Structure

The project is organized into several key files:

- **`main.py`:** The main entry point for the command-line interface (CLI).
- **`gui.py`:** A Streamlit-based graphical user interface (GUI) for a more visual experience.
- **`*_tools.py`:** Modules that define the agent's capabilities (e.g., `gmail_tools.py`, `gdrive_tools.py`, `image_generation_tools.py`, `document_tools.py`).
- **`requirements.txt`:** A list of all the Python packages required for the project.
- **`.env`:** A configuration file for storing your API keys.
- **`agent_working/`:** A dedicated directory where the agent can create, modify, and store files.

## Getting Started

### Prerequisites

- Python 3.8 or higher
- An active Google Cloud project with the following APIs enabled:
    - Gmail API
    - Google Calendar API
    - Google Drive API
- A `credentials.json` file from your Google Cloud project.

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-username/ai-agent.git
   cd ai-agent
   ```

2. **Install the required packages:**
   This project uses `uv` for fast and efficient package management.
   ```bash
   pip install uv
   uv pip install -r requirements.txt
   ```
   Alternatively, you can use `pip`:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up your API keys:**
   Create a `.env` file in the root of the project and add your API keys:
   ```
   GEMINI_API_KEY="your-gemini-api-key"
   TAVILY_API_KEY="your-tavily-api-key"
   ```

4. **Authorize Google Workspace access:**
   - Place your `credentials.json` file in the root of the project.
   - Run the `get_google_service.py` script to authorize the application. This will create a `token.json` file that stores your access tokens.
   ```bash
   python get_google_service.py
   ```

### Usage

You can interact with the agent through the command line or a graphical user interface.

**Command-Line Interface (CLI):**
```bash
python main.py
```

**Graphical User Interface (GUI):**
```bash
streamlit run gui.py
```

## Example Use Cases

- **"Send an email to my team about the project update."**
- **"Schedule a meeting with John for tomorrow at 2 PM to discuss the new design."**
- **"What are the top headlines from today?"**
- **"Create a PowerPoint presentation about the future of AI, with images."**
- **"Create a Word document summarizing the latest developments in space exploration, with images."**
- **"Generate an image of a futuristic cityscape."**
- **"Write a Python script to sort a list of numbers."**

This agent is a powerful tool for automating tasks, accessing information, and exploring the creative possibilities of AI. Enjoy!
