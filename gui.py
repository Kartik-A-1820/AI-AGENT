from concurrent.futures import ThreadPoolExecutor
import time

import streamlit as st
from main import get_agent_response, HumanMessage, AIMessage
import re
import os
from assistant_state import ASSISTANT_HOME, get_profile, load_tasks

st.set_page_config(page_title="PC Assistant", page_icon="AI", layout="wide")


@st.cache_resource
def get_executor() -> ThreadPoolExecutor:
    return ThreadPoolExecutor(max_workers=4)


def build_chat_history(messages):
    chat_history = []
    for msg in messages:
        if msg["role"] == "user":
            chat_history.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            chat_history.append(AIMessage(content=msg["content"]))
    return chat_history


def extract_artifact_paths(response: str) -> list[str]:
    paths = re.findall(r"(?:Saved (?:image|video) to|Research brief saved to)\s+([^\n]+)", response)
    paths.extend(re.findall(r"(D:\\[^\n]+?\.(?:png|jpg|jpeg|webp|mp4|webm|mov|md|docx|pptx))", response))
    return list(dict.fromkeys(path.strip() for path in paths if os.path.exists(path.strip())))


st.title("PC Assistant")
st.caption("Powered by your local OmniRoute endpoint")

# Initialize chat history and total cost
if "messages" not in st.session_state:
    st.session_state.messages = []
if "total_cost" not in st.session_state:
    st.session_state.total_cost = 0.0
if "pending_job" not in st.session_state:
    st.session_state.pending_job = None
if "pending_prompt" not in st.session_state:
    st.session_state.pending_prompt = None

profile = get_profile()
open_tasks = [task for task in load_tasks() if task.get("status") != "done"]
with st.sidebar:
    st.subheader("Assistant")
    st.write(f"Home: `{ASSISTANT_HOME}`")
    if profile.get("name"):
        st.write(f"User: {profile['name']}")
    st.metric("Open tasks", len(open_tasks))
    st.divider()
    quick_prompt = None
    if st.button("Daily brief", use_container_width=True):
        quick_prompt = "Give me my daily brief. Include local tasks, calendar events, and recent important email."
    if st.button("Open tasks", use_container_width=True):
        quick_prompt = "List my open local tasks and suggest what I should do next."
    if st.button("Recent context", use_container_width=True):
        quick_prompt = "Recall my saved profile and recent durable memories."
    if st.button("Topic research", use_container_width=True):
        quick_prompt = "Research a practical topic I should learn this week and save a cited research brief."
    if st.button("Media models", use_container_width=True):
        quick_prompt = "List available Omniroute image and video generation models."
    st.divider()
    st.markdown(f"### Total Conversation Cost: ${st.session_state.total_cost:.6f}")

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if "cost_info" in message:
            st.caption(message["cost_info"])
        if "image_path" in message:
            st.image(message["image_path"])
        for artifact in message.get("artifacts", []):
            suffix = artifact.lower()
            if suffix.endswith((".png", ".jpg", ".jpeg", ".webp")):
                st.image(artifact)
            elif suffix.endswith((".mp4", ".webm", ".mov")):
                st.video(artifact)
            else:
                st.caption(f"Artifact: {artifact}")

typed_prompt = st.chat_input("What can I help you with?")
prompt = quick_prompt or typed_prompt

pending = st.session_state.pending_job
if pending is not None:
    with st.status(f"Working on: {st.session_state.pending_prompt}", expanded=False):
        st.write("Running in the background with async tools and retries.")
    if pending.done():
        try:
            response, prompt_tokens, completion_tokens, cost = pending.result()
        except Exception as exc:
            response, prompt_tokens, completion_tokens, cost = f"Request failed: {exc}", 0, 0, 0.0
        st.session_state.total_cost += cost
        cost_info = f"Prompt Tokens: {prompt_tokens}, Completion Tokens: {completion_tokens}, Cost: ${cost:.6f}"
        st.session_state.messages.append({"role": "assistant", "content": response, "cost_info": cost_info, "artifacts": extract_artifact_paths(response)})
        st.session_state.pending_job = None
        st.session_state.pending_prompt = None
        st.rerun()
    else:
        time.sleep(0.5)
        st.rerun()

# React to user input
if prompt and st.session_state.pending_job is None:
    # Display user message in chat message container
    st.chat_message("user").markdown(prompt)
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})

    chat_history = build_chat_history(st.session_state.messages)
    st.session_state.pending_job = get_executor().submit(get_agent_response, prompt, chat_history)
    st.session_state.pending_prompt = prompt
    st.rerun()

elif prompt:
    st.warning("A request is already running. Please wait for it to finish.")
