import streamlit as st
from main import get_agent_response, HumanMessage, AIMessage
import re
import os

st.title("Gemini Powered AI Agent")

# Initialize chat history and total cost
if "messages" not in st.session_state:
    st.session_state.messages = []
if "total_cost" not in st.session_state:
    st.session_state.total_cost = 0.0

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if "cost_info" in message:
            st.caption(message["cost_info"])
        if "image_path" in message:
            st.image(message["image_path"])

# React to user input
if prompt := st.chat_input("What can I help you with?"):
    # Display user message in chat message container
    st.chat_message("user").markdown(prompt)
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Check if the prompt is for image generation
    is_image_prompt = "generate an image" in prompt.lower() or "create an image" in prompt.lower()

    # Get agent response
    spinner_message = "Generating image..." if is_image_prompt else "Agent is thinking..."
    with st.spinner(spinner_message):
        chat_history = []
        for msg in st.session_state.messages:
            if msg["role"] == "user":
                chat_history.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                chat_history.append(AIMessage(content=msg["content"]))

        response, prompt_tokens, completion_tokens, cost = get_agent_response(prompt, chat_history)
    
    # Update total cost
    st.session_state.total_cost += cost

    # Display assistant response in chat message container
    with st.chat_message("assistant"):
        st.markdown(response)
        cost_info = f"Prompt Tokens: {prompt_tokens}, Completion Tokens: {completion_tokens}, Cost: ${cost:.6f}"
        st.caption(cost_info)

        # Check if an image was generated and display it
        image_path_match = re.search(r"✅ Saved image → (agent_working/images/.*?\.(?:png|jpg|jpeg))", response)
        if image_path_match:
            image_path = image_path_match.group(1)
            if os.path.exists(image_path):
                st.image(image_path)
                st.session_state.messages.append({"role": "assistant", "content": response, "cost_info": cost_info, "image_path": image_path})
            else:
                st.error("Image file not found at the specified path.")
                st.session_state.messages.append({"role": "assistant", "content": response, "cost_info": cost_info})
        else:
            st.session_state.messages.append({"role": "assistant", "content": response, "cost_info": cost_info})


# Display total cost at the bottom
st.sidebar.markdown(f"### Total Conversation Cost: ${st.session_state.total_cost:.6f}")