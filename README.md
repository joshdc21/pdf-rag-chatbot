<<<<<<< HEAD
# pdf-rag-chatbot
A conversational RAG chatbot for querying any PDF — built with ChromaDB and the Gemini API. Rewrites follow-up questions using conversation history before retrieval, so multi-turn context (e.g. 'what about the risks?') actually resolves correctly
=======


Readme · MD
# PDF Q&A Chatbot (Conversational RAG)
 
A command-line conversational RAG (Retrieval-Augmented Generation) agent that answers
questions about any PDF document using semantic search (ChromaDB) and Google's Gemini
API. Unlike a plain single-turn Q&A script, this agent rewrites follow-up questions
using conversation history *before* retrieval, so it correctly understands references
like "what about the risks?" that depend on earlier turns.
 
## How it works
 
1. **Load & chunk** — The PDF is parsed page-by-page with `pypdf`, then split into
   ~500-character overlapping chunks using LangChain's `RecursiveCharacterTextSplitter`.
2. **Index** — Chunks are embedded (via ChromaDB's default embedding function) and
   stored in an in-memory ChromaDB collection.
3. **Query rewriting** — Before each search, the user's question and the conversation
   history are sent to Gemini, which rewrites the question into a standalone query if
   it depends on prior context (e.g. resolves "it", "that", "what about...").
4. **Retrieve** — The standalone query is used to fetch the top 3 most relevant chunks
   from ChromaDB.
5. **Generate** — Gemini answers the current question, grounded strictly in the
   retrieved PDF chunks (with conversation history included only to preserve
   conversational tone/context, not as a source of facts).
6. **Repeat** — The exchange is appended to `conversation_history` and the loop
   continues until the user types `exit`.
 
## Requirements
 
- Python 3.9+
- A Gemini API key
 
### Dependencies
 
```
python-dotenv
google-genai
chromadb
pypdf
langchain-text-splitters
```
 
Install with:
 
```bash
pip install python-dotenv google-genai chromadb pypdf langchain-text-splitters
```
 
(Consider freezing these into a `requirements.txt` once your environment is stable.)
 
## Setup
 
1. Clone or copy this project into a directory containing your target PDF.
2. Create a `.env` file in the project root:
 
```
   GEMINI_API_KEY=your_api_key_here
```
 
3. Place the PDF you want to query in the project root. The filename is currently
   hardcoded near the top of the script:
 
```python
   reader = PdfReader("your_file_name.pdf")
```
 
   To use a different PDF, just change the filename inside the quotes to match your
   file.
 
## Usage
 
Run the script:
 
```bash
python main.py
```
 
You'll see:
 
```
--- Ask anything about your pdf(type 'exit' to quit) ---
```
 
Ask questions naturally, including follow-ups:
 
```
> What are the main findings in section 2?
Assistant: ...
 
> What about the risks mentioned there?
[standalone query printed here if rewritten]
Assistant: ...
 
> exit
```
 
Type `exit` at any point to quit.
 
## Notes & limitations
 
- **In-memory vector store** — `chromadb.Client()` is ephemeral. The PDF is
  re-chunked and re-indexed every time you run the script. For persistence across
  runs, switch to `chromadb.PersistentClient(path="...")`.
- **Default embeddings** — Retrieval currently uses ChromaDB's built-in embedding
  function rather than Gemini's embedding model (`gemini-embedding-001`). Gemini
  embeddings were tried but kept hitting API rate limits, so the switch to
  ChromaDB's default was a practical workaround rather than a permanent design
  choice. It's simpler and avoids rate-limit issues, but is generally less accurate
  for domain-specific text (technical terminology, numbers, etc.) than Gemini's
  embeddings would be.
- **Grounding** — The assistant is instructed to answer only from retrieved PDF
  context and to say "I don't know based on the provided document" when the answer
  isn't found, to reduce hallucination.
- **Cost/latency** — Each turn makes two Gemini calls (one to rewrite the query, one
  to generate the answer), so responses are slightly slower and use more tokens than
  a single-turn setup.
 
## Possible next steps
 
- Swap in `PersistentClient` so the index doesn't need to be rebuilt every run.
- Use Gemini embeddings for retrieval instead of ChromaDB defaults.
- Support multiple PDFs / a folder of documents.
- Add source citations (chunk/page numbers) to answers.
- Wrap in a simple web UI (e.g. Streamlit) instead of a CLI loop.
>>>>>>> af3c1fd (Initial commit: PDF Q&A assistant with Gemini and ChromaDB)
