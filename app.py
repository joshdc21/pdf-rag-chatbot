import os
import streamlit as st
# pyrefly: ignore [missing-import]
from pypdf import PdfReader

from pdf_reader import (
    client, collection, splitter, hash_content,
    retrieve_documents, rewrite_query_with_history
)

st.set_page_config(page_title="PDF Chatbot Assistant", layout="wide")

# Initialize session state for message display and conversation history
if "messages" not in st.session_state:
    st.session_state.messages = []

if "conversation_history" not in st.session_state:
    st.session_state.conversation_history = []

# Sidebar: Document Management & Configuration
st.sidebar.header("Documents")

uploaded_files = st.sidebar.file_uploader(
    "Upload PDF Documents",
    type=["pdf"],
    accept_multiple_files=True
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
                status_container.text(f"Processing {filename}...")

                # Read PDF pages in memory
                reader = PdfReader(uploaded_file)
                pages = []
                for page_number, page in enumerate(reader.pages, start=1):
                    page_text = page.extract_text()
                    if page_text:
                        pages.append({
                            "page": page_number,
                            "text": page_text
                        })

                full_text = "\n".join(page["text"] for page in pages)
                content_hash = hash_content(full_text)

                # Deduplication logic
                existing = collection.get(where={"source": filename})
                if existing and existing.get("ids"):
                    existing_hash = existing["metadatas"][0].get("content_hash")
                    if existing_hash == content_hash:
                        status_container.text(f"Skipping {filename} - already processed")
                        continue
                    status_container.text(f"{filename} has changed - re-processing")
                    collection.delete(where={"source": filename})

                # Split text into chunks
                chunks = []
                metadatas = []
                for page in pages:
                    page_chunks = splitter.split_text(page["text"])
                    for chunk in page_chunks:
                        chunks.append(chunk)
                        metadatas.append({
                            "source": filename,
                            "page": page["page"],
                            "content_hash": content_hash
                        })

                if chunks:
                    collection.add(
                        documents=chunks,
                        ids=[f"{filename}-chunk-{i}" for i in range(len(chunks))],
                        metadatas=metadatas
                    )
                    status_container.text(f"Added {filename} to ChromaDB")

# Main Application Window: Chat Interface
st.title("PDF Chatbot Assistant")

# Check for Missing API Key
api_key = os.environ.get("GEMINI_API_KEY")
api_key_missing = not api_key

if api_key_missing:
    st.warning("⚠️ `GEMINI_API_KEY` environment variable is missing. AI chat is disabled. Please set GEMINI_API_KEY in your environment or `.env` file.")

# Check for Empty Collection Safeguard
try:
    doc_count = collection.count()
except Exception:
    doc_count = 0

if doc_count == 0:
    st.info("📄 No documents indexed yet. Upload PDF files in the sidebar and click **Process & Index PDFs** to begin.")

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

    # 2. Rewrite query with history
    standalone_query = rewrite_query_with_history(
        user_input,
        st.session_state.conversation_history
    )

    # 3. Retrieve documents
    results = retrieve_documents(standalone_query, n_results=5)

    # 4. Format retrieved context
    retrieved_context = ""
    if results and results.get("documents") and len(results["documents"]) > 0:
        for document, metadata in zip(results["documents"][0], results["metadatas"][0]):
            retrieved_context += (
                f"Source: {metadata['source']}\n"
                f"Page: {metadata['page']}\n"
                f"Content: {document}\n\n"
            )

    # 5. Inject context into system prompt template
    history_text = "\n".join(
        f"{message['role']}: {message['content']}"
        for message in st.session_state.conversation_history
    )

    prompt = f"""You are a helpful assistant answering questions about the provided PDF documents.

Answer the user's current question using ONLY the provided PDF context.

For every factual claim, cite the specific source and page that supports it using this format:
[Source: filename.pdf, Page: X]

Only cite sources and page numbers that appear in the provided PDF context.
Do not invent or guess page numbers.

If multiple sources or pages support a claim, you may cite multiple sources.

Previous conversation history:
{history_text if history_text else "None"}

Relevant PDF context:
{retrieved_context}

Current question:
{user_input}

If the answer cannot be found in the provided PDF context, say:
"I don't know based on the provided document."

Do not use outside knowledge or invent information.
"""

    # 6 & 7. Send prompt payload to model and render response
    with st.chat_message("assistant"):
        try:
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt
            )
            response_text = response.text
            st.markdown(response_text)
        except Exception as e:
            response_text = f"Error generating response: {e}"
            st.error(response_text)

    # 8. Append prompt and response to conversation history and messages
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
