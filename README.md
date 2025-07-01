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

## Project Architecture

The agent's architecture is designed to be modular and extensible. Here's a breakdown of the key components:

- **`main.py`:** This is the heart of the application, containing the main chat loop, agent initialization, and tool configuration.
- **`gui.py`:** This file provides a user-friendly graphical interface using Streamlit, making it easy to interact with the agent in a more visual way.
- **Tool Modules (`*_tools.py`):** Each module defines a specific set of tools that the agent can use. This modular approach makes it easy to add new capabilities to the agent.
- **`get_google_service.py`:** This module handles the authentication and authorization for all Google Workspace services.
- **Pydantic Models:** The tools use Pydantic models to define their input schemas, which ensures that the LLM provides the correct arguments and reduces errors.

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
   - Run the `get_google_service.py` script to authorize the application. This will open a browser window for you to log in and grant permission. Upon successful authorization, a `token.json` file will be created to store your access tokens.
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

## Tool-Specific Examples

Here are some examples of how you can use the agent's tools:

- **Create a presentation:**
  `"Create a 5-slide presentation on the history of space exploration, with images."`
- **Create a Word document:**
  `"Create a Word document summarizing the key points of the latest AI trends, and include images."`
- **Send an email with an attachment:**
  `"Send an email to my manager with the presentation I just created."`
- **Schedule a meeting with a Google Meet link:**
  `"Schedule a meeting with the team for tomorrow at 10 AM to review the presentation. Include a Google Meet link."`
- **Search the web and save the results to a file:**
  `"What are the latest trends in artificial intelligence? Save the results to a file called 'ai_trends.txt'."`

## How to Contribute

We welcome contributions from the community! If you'd like to contribute to the project, please follow these steps:

1. **Fork the repository.**
2. **Create a new branch for your feature or bug fix.**
3. **Make your changes and commit them with clear, descriptive messages.**
4. **Push your changes to your fork.**
5. **Create a pull request to the main repository.**

We look forward to seeing your contributions!
