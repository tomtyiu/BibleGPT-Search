from openai import OpenAI
import streamlit as st
import json
import tempfile
import subprocess
import sys
import os
import http.client

# --- Custom CSS for a white background and light gray borders ---
st.markdown("""
<style>
body {
    font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
    line-height: 1.6;
    background-color: #ffffff;
}
.user-message {
    background-color: #ffffff;
    padding: 12px;
    border: 1px solid #ccc;
    border-radius: 8px;
    margin-bottom: 10px;
    font-size: 16px;
}
.bot-message {
    background-color: #ffffff;
    padding: 12px;
    border: 1px solid #ccc;
    border-radius: 8px;
    margin-bottom: 10px;
    font-size: 16px;
}
.search-result {
    background-color: #ffffff;
    padding: 10px;
    border: 1px solid #ccc;
    border-radius: 8px;
    margin-bottom: 10px;
    font-size: 14px;
}
</style>
""", unsafe_allow_html=True)

st.title("TheosGPT: Christian Search AI")

# Create two columns: left for chat, right for Google search results.
left_col, right_col = st.columns([2, 1])

# Prompt user for OpenAI API Key in the left column.
with left_col:
    openai_key = st.text_input("Enter your OpenAI API Key:", type="password")
    if openai_key:
        client = OpenAI(api_key=openai_key)

# Initialize conversation history if not already present.
if "messages" not in st.session_state:
    st.session_state["messages"] = []

# Placeholders for conversation and search results.
with left_col:
    conversation_placeholder = st.container()
with right_col:
    search_placeholder = st.container()

def save_and_run_code(code):
    """
    Saves the provided code into a temporary .py file and executes it.
    Returns the stdout if successful, or the stderr if there's an error.
    """
    try:
        code = code.strip()
        if code.startswith("```python"):
            code = code[len("```python"):].strip()
        if code.endswith("```"):
            code = code[:-len("```")].strip()
        with tempfile.NamedTemporaryFile('w', suffix='.py', delete=False) as tmp_file:
            temp_path = tmp_file.name
            tmp_file.write(code)
        result = subprocess.run(
            [sys.executable, temp_path],
            text=True,
            capture_output=True
        )
        try:
            os.remove(temp_path)
        except Exception:
            pass
        if result.returncode == 0:
            return result.stdout
        else:
            return f"Error:\n{result.stderr}"
    except Exception as e:
        return f"An exception occurred: {e}"

def fetch_google_search_results(search_query):
    """
    Calls the Google search API via serper.dev and returns the JSON response.
    """
    conn = http.client.HTTPSConnection("google.serper.dev")
    payload = json.dumps({"q": search_query})
    headers = {
        'X-API-KEY': '1e6a24e58cd92c8ecb92c77fbb799d026c5aa0e0',
        'Content-Type': 'application/json'
    }
    conn.request("POST", "/search", payload, headers)
    res = conn.getresponse()
    data = res.read()
    return json.loads(data.decode("utf-8"))

def display_messages():
    """Render the conversation history in the left column container."""
    with conversation_placeholder:
        st.markdown("### Conversation")
        for message in st.session_state["messages"]:
            if message["role"] == "user":
                st.markdown(
                    f"<div class='user-message'><b>You:</b> {message['content']}</div>",
                    unsafe_allow_html=True,
                )
            elif message["role"] == "assistant":
                if isinstance(message["content"], list):
                    combined_text = ""
                    for part in message["content"]:
                        combined_text += part.get("text", "")
                    output = f"<div class='bot-message'><b>Bot:</b> {combined_text}</div>"
                    st.markdown(output, unsafe_allow_html=True)
                else:
                    st.markdown(
                        f"<div class='bot-message'><b>Bot:</b> {message['content']}</div>",
                        unsafe_allow_html=True,
                    )

def display_search_results(results):
    """Render Google search results (organic results) in the right column container."""
    with search_placeholder:
        st.markdown("### Google Search Results")
        if results:
            for result in results:
                title = result.get("title", "No Title")
                link = result.get("link", "#")
                snippet = result.get("snippet", "")
                st.markdown(
                    f"<div class='search-result'><a href='{link}' target='_blank'><b>{title}</b></a><br>{snippet}</div>",
                    unsafe_allow_html=True,
                )
        else:
            st.markdown("<div class='search-result'>No search results available.</div>", unsafe_allow_html=True)

# Display the initial conversation and (empty) search results.
display_messages()
display_search_results([])

# Chat input area placed in the left column.
with left_col:
    col_input, col_submit = st.columns([9, 1])
    with col_input:
        query = st.text_input("Enter your question:", key="query_input")
    with col_submit:
        submit = st.button("→")

if submit:
    if not openai_key:
        with left_col:
            st.error("Please enter your OpenAI API Key above.")
    elif not query:
        with left_col:
            st.warning("Please enter a question or code.")
    else:
        google_results = []
        # Check if the input starts with "Code:" and handle code execution.
        if query.strip().startswith("Code:"):
            code_to_execute = query.strip()[len("Code:"):].strip()
            completion = client.chat.completions.create(
                model="o3-mini",
                messages=[
                    {"role": "developer", "content": (
                        "You are a super-intelligent advanced Python code assistant. "
                        "Generate the highest quality, improved code. Output raw code only."
                    )},
                    {"role": "user", "content": code_to_execute}
                ],
            )
            code_response = completion.choices[0].message.content
            execution_result = save_and_run_code(code_response)
            st.session_state["messages"].append({"role": "assistant", "content": execution_result})
        else:
            # Append the user's query to the conversation history.
            st.session_state["messages"].append({"role": "user", "content": query})
            with st.spinner("Fetching response..."):
                try:
                    response = client.responses.create(
                        model="gpt-4o",
                        instructions="You are a Christian search agent. Provide a detailed answer with citations at end of the response.",
                        tools=[{"type": "web_search_preview", "search_context_size": "medium"}],
                        input=query
                    )
                    answer = response.output_text
                except Exception as e:
                    answer = f"Error: {e}"
            if answer.strip().startswith("```python"):
                execution_result = save_and_run_code(answer)
                st.session_state["messages"].append({"role": "assistant", "content": execution_result})
            else:
                st.session_state["messages"].append({"role": "assistant", "content": answer.strip()})
        
        # Fetch Google search results.
        try:
            google_data = fetch_google_search_results(query)
            google_results = google_data.get("organic", [])
        except Exception as e:
            google_results = []
            st.error(f"Google Search API error: {e}")
        
        # Update the conversation and search results displays.
        display_messages()
        display_search_results(google_results)
    
    # Clear the text input field by resetting its session state.
    st.session_state["query_input"] = ""
