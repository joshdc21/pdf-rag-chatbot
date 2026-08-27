import os
import streamlit as st
from login import login
from supabase_client import supabase

if "user" not in st.session_state:
    login()
    st.stop()

if "session" in st.session_state and st.session_state["session"]:
    try:
        supabase.auth.set_session(
            st.session_state["session"].access_token,
            st.session_state["session"].refresh_token
        )
    except Exception:
        pass

from pdf_reader import generate_rag_response, insert_chunk_to_supabase

st.set_page_config(page_title="PDF Chatbot Assistant", layout="wide")

# Initialize session state for message display and conversation history
if "messages" not in st.session_state:
    st.session_state.messages = []

if "conversation_history" not in st.session_state:
    st.session_state.conversation_history = []

user = st.session_state["user"]
display_name = user.user_metadata.get(
    "display_name",
    user.email
)

st.sidebar.write(f"Hello **{display_name}**")
if st.sidebar.button("Log Out"):
    supabase.auth.sign_out()
    del st.session_state["user"]
    if "session" in st.session_state:
        del st.session_state["session"]
    st.rerun()
st.sidebar.divider()

# Sidebar
st.sidebar.header("Documents")

if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = 0

uploaded_files = st.sidebar.file_uploader(
    "Upload PDF Documents",
    type=["pdf"],
    accept_multiple_files=True,
    key=f"pdf_uploader_{st.session_state.uploader_key}"
)

process_button = st.sidebar.button("Process PDF")

if process_button:
    if not uploaded_files:
        st.sidebar.warning("Please select at least one PDF file before processing.")
    else:
        with st.sidebar.spinner("Processing & indexing PDFs..."):
            status_container = st.sidebar.container()
            for uploaded_file in uploaded_files:
                filename = uploaded_file.name

                user = st.session_state["user"]
                user_id = user.id

                file_bytes = uploaded_file.getvalue()
                file_path = f"{user_id}/{filename}"

                try:
                    supabase.storage \
                        .from_("pdfs") \
                        .upload(
                            file_path,
                            file_bytes,
                            {
                                "content-type": "application/pdf"
                            }
                        )

                    status_container.text(
                        f"{filename} uploaded successfully"
                    )

                except Exception as e:
                    status_container.error(
                        f"Failed to upload {filename}: {e}"
                    )
                    continue

                insert_chunk_to_supabase(
                    file_source=uploaded_file,
                    filename=filename,
                    user_id=user_id,
                    status_cb=status_container.text
                )

            st.session_state.uploader_key += 1
            st.rerun()

# Display list of uploaded/indexed PDFs for the current user
user_docs = set()
try:
    files = supabase.storage.from_("pdfs").list(user.id)
    if files:
        for file_obj in files:
            name = file_obj.get("name")
            if name and not name.startswith("."):
                user_docs.add(name)
except Exception:
    pass

st.sidebar.divider()
st.sidebar.subheader("Uploaded Documents")
if user_docs:
    for doc_name in sorted(user_docs):
        st.sidebar.markdown(f"📄 `{doc_name}`")
else:
    st.sidebar.caption("No documents uploaded yet.")

# Main Application Window: Chat Interface
st.title("PDF Chatbot Assistant")

# Check for Missing API Key
api_key = os.environ.get("GEMINI_API_KEY")
api_key_missing = not api_key

if api_key_missing:
    st.warning("`GEMINI_API_KEY` environment variable is missing. AI chat is disabled. Please set GEMINI_API_KEY in your environment or `.env` file.")

if not user_docs:
    st.info("No documents indexed yet. Upload PDF files in the sidebar and click **Process & Index PDFs** to begin.")

# Render Chat Message Feed
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Sticky Chat Input Box
user_input = st.chat_input(
    "Ask anything about your documents...",
    disabled=api_key_missing
)

if user_input:
    # 1. Render user message & append to session messages
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # 2. Generate RAG response via shared engine
    with st.chat_message("assistant"):
        try:
            response_text = generate_rag_response(
                user_query=user_input,
                conversation_history=st.session_state.conversation_history,
                user_id=user.id
            )
            st.markdown(response_text)
        except Exception as e:
            response_text = f"Error generating response: {e}"
            st.error(response_text)

    # 3. Append prompt and response to conversation history and messages
    st.session_state.conversation_history.append({
        "role": "user",
        "content": user_input
    })
    st.session_state.conversation_history.append({
        "role": "assistant",
        "content": response_text
    })
    st.session_state.messages.append({
        "role": "assistant",
        "content": response_text
    })
