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

from pdf_reader import generate_rag_response, insert_chunk_to_supabase, delete_document, rename_document

def load_css(file_path):
    with open(file_path) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

st.set_page_config(page_title="PDF Chatbot Assistant", layout="wide", initial_sidebar_state="expanded")
load_css("style.css")

# Initialize session state for message display, history, and doc status
if "messages" not in st.session_state:
    st.session_state.messages = []

if "conversation_history" not in st.session_state:
    st.session_state.conversation_history = []

if "doc_status" not in st.session_state:
    st.session_state.doc_status = {}

user = st.session_state["user"]
user_email = user.email

# 2. Account section: "Signed in as", plain text email, "Log out" link
with st.sidebar:
    st.markdown(f"""
        <div class="sidebar-account">
            <div class="account-label">Signed in as</div>
            <div class="account-email">{user_email}</div>
        </div>
    """, unsafe_allow_html=True)
    
    if st.button("Log out", type="tertiary", key="btn_logout"):
        supabase.auth.sign_out()
        del st.session_state["user"]
        if "session" in st.session_state:
            del st.session_state["session"]
        st.rerun()
    st.divider()

# Sidebar: Document Upload & Processing Section
st.sidebar.header("Documents")

if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = 0

uploaded_files = st.sidebar.file_uploader(
    "Upload PDF Documents",
    type=["pdf"],
    accept_multiple_files=True,
    key=f"pdf_uploader_{st.session_state.uploader_key}"
)

# Process PDF as Primary Button
process_button = st.sidebar.button("Process PDF", type="primary", use_container_width=True)

if process_button:
    if not uploaded_files:
        st.sidebar.warning("Please select at least one PDF file before processing.")
    else:
        with st.sidebar.spinner("Processing & indexing PDFs..."):
            status_container = st.sidebar.container()
            for uploaded_file in uploaded_files:
                filename = uploaded_file.name
                user_id = user.id

                # Per-document status: Set Amber (Processing) while active
                st.session_state.doc_status[filename] = "Processing"

                file_bytes = uploaded_file.getvalue()
                file_path = f"{user_id}/{filename}"

                try:
                    supabase.storage.from_("pdfs").upload(
                        file_path,
                        file_bytes,
                        {"content-type": "application/pdf"}
                    )
                    status_container.text(f"{filename} uploaded successfully")
                except Exception:
                    pass

                def make_status_cb(file_name):
                    def cb(msg):
                        status_container.text(msg)
                        if "Failed" in msg or "Error" in msg or "failed" in msg:
                            st.session_state.doc_status[file_name] = "Failed"
                        elif "Added" in msg or "Skipping" in msg or "already processed" in msg:
                            st.session_state.doc_status[file_name] = "Ready"
                    return cb

                try:
                    insert_chunk_to_supabase(
                        file_source=uploaded_file,
                        filename=filename,
                        user_id=user_id,
                        status_cb=make_status_cb(filename)
                    )
                    # If no failure was recorded during insertion, mark Ready (Green)
                    if st.session_state.doc_status.get(filename) != "Failed":
                        st.session_state.doc_status[filename] = "Ready"
                except Exception as e:
                    # Per-document status: Set Red (Failed) if exception occurs
                    st.session_state.doc_status[filename] = "Failed"
                    status_container.error(f"Failed to process {filename}: {e}")

            st.session_state.uploader_key += 1
            st.rerun()

# Fetch list of uploaded PDFs from Supabase storage
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

# Render uploaded documents with status dots and clean filename display
if user_docs:
    for idx, doc_name in enumerate(sorted(user_docs)):
        # Default status for existing storage documents is Ready unless in session state
        status = st.session_state.doc_status.get(doc_name, "Ready")
        status_dot = "🟢" if status == "Ready" else ("🟡" if status == "Processing" else "🔴")

        # Truncate long filenames with ellipsis and show tooltip on hover
        max_name_len = 22
        display_name_text = doc_name if len(doc_name) <= max_name_len else doc_name[:19] + "..."

        doc_col, menu_col = st.sidebar.columns([0.82, 0.18], vertical_alignment="center")
        with doc_col:
            st.markdown(
                f"<span title='{doc_name} • Status: {status}'>{status_dot} 📄 {display_name_text}</span>",
                unsafe_allow_html=True,
                help=f"{doc_name} • Status: {status}"
            )
        with menu_col:
            with st.popover("⋮", help=f"Options for {doc_name}"):
                new_name = st.text_input(
                    "New file name",
                    value=doc_name,
                    key=f"rename_input_{idx}"
                )
                if st.button("Rename", key=f"btn_rename_{idx}", use_container_width=True):
                    success, message = rename_document(
                        user_id=user.id,
                        old_name=doc_name,
                        new_name=new_name
                    )
                    if success:
                        if doc_name in st.session_state.doc_status:
                            st.session_state.doc_status[new_name] = st.session_state.doc_status.pop(doc_name)
                        st.toast(f"Successfully renamed '{doc_name}' to '{new_name}'")
                        st.rerun()
                    else:
                        st.toast(f"Error renaming '{doc_name}': {message}")
                
                st.divider()
                
                if st.button("Delete", key=f"btn_delete_{idx}", type="primary", use_container_width=True):
                    success, message = delete_document(
                        user_id=user.id,
                        filename=doc_name
                    )
                    if success:
                        st.session_state.doc_status.pop(doc_name, None)
                        st.toast(f"Successfully deleted '{doc_name}'")
                        st.rerun()
                    else:
                        st.toast(f"Error deleting '{doc_name}': {message}")
else:
    st.sidebar.caption("No documents uploaded yet.")

# Condense the Header into a slim top bar
st.markdown("""
    <div class="top-header">
        <div class="top-header-left">
            <span class="top-header-title">PDF Chatbot Assistant</span>
        </div>
        <span class="top-header-subtitle">AI Document Search</span>
    </div>
""", unsafe_allow_html=True)

# Check for Missing API Key
api_key = os.environ.get("GEMINI_API_KEY")
api_key_missing = not api_key

if api_key_missing:
    st.warning("`GEMINI_API_KEY` environment variable is missing. AI chat is disabled. Please set GEMINI_API_KEY in your environment or `.env` file.")

if not user_docs:
    st.info("No documents indexed yet. Upload PDF files in the sidebar and click **Process PDF** to begin.")

# Empty Chat State & Clickable Prompt Chips
prompt_from_chip = None

if not st.session_state.messages:
    st.markdown("""
        <div class="empty-chat-container">
            <div class="empty-chat-icon">💬</div>
            <h2 class="empty-chat-heading">Ask anything about your documents</h2>
            <p class="empty-chat-subtext">
                Upload your PDF files in the sidebar and ask questions, or select a suggested prompt below to get started.
            </p>
        </div>
    """, unsafe_allow_html=True)

    chip_col1, chip_col2, chip_col3 = st.columns([1, 1, 1], gap="small")
    with chip_col1:
        if st.button("📄 Summarize this document", use_container_width=True, key="chip_summarize"):
            prompt_from_chip = "Summarize the main points of the document."
    with chip_col2:
        if st.button("📊 Key statistics & findings", use_container_width=True, key="chip_stats"):
            prompt_from_chip = "What are the key statistics and findings in the document?"
    with chip_col3:
        if st.button("💡 Explain core concepts", use_container_width=True, key="chip_concepts"):
            prompt_from_chip = "Explain the core concepts covered in the uploaded documents."

# Render Chat Message Feed when messages exist
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Sticky Chat Input Box
user_input = st.chat_input(
    "Ask anything about your documents...",
    disabled=api_key_missing
)

active_query = user_input or prompt_from_chip

if active_query:
    # Render user message & append to session messages
    st.session_state.messages.append({"role": "user", "content": active_query})
    with st.chat_message("user"):
        st.markdown(active_query)

    # Generate RAG response via backend
    with st.chat_message("assistant"):
        try:
            response_text = generate_rag_response(
                user_query=active_query,
                conversation_history=st.session_state.conversation_history,
                user_id=user.id
            )
            st.markdown(response_text)
        except Exception as e:
            response_text = f"Error generating response: {e}"
            st.error(response_text)

    # Append prompt and response to conversation history and messages
    st.session_state.conversation_history.append({
        "role": "user",
        "content": active_query
    })
    st.session_state.conversation_history.append({
        "role": "assistant",
        "content": response_text
    })
    st.session_state.messages.append({
        "role": "assistant",
        "content": response_text
    })
    st.rerun()