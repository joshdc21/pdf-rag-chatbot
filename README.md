# PDF Q&A Chatbot (Conversational RAG)

A command-line conversational RAG (Retrieval-Augmented Generation) agent that answers questions about any PDF document using semantic search (ChromaDB) and Google's Gemini API. Unlike a plain single-turn Q&A script, this agent rewrites follow-up questions using conversation history *before* retrieval, so it correctly understands references like "what about the risks?" that depend on earlier turns.

## How it works

1. **Load & chunk** — The PDF is parsed page-by-page with `pypdf`, then split into ~500-character overlapping chunks using LangChain's `RecursiveCharacterTextSplitter`.
2. **Index** — Chunks are embedded (via ChromaDB's default embedding function) and stored in an in-memory ChromaDB collection.
3. **Query rewriting** — Before each search, the user's question and the conversation history are sent to Gemini, which rewrites the question into a standalone query if it depends on prior context (e.g. resolves "it", "that", "what about...").
4. **Retrieve** — The standalone query is used to fetch the top 3 most relevant chunks from ChromaDB.
5. **Generate** — Gemini answers the current question, grounded strictly in the retrieved PDF chunks (with conversation history included only to preserve conversational tone/context, not as a source of facts).
6. **Repeat** — The exchange is appended to `conversation_history` and the loop continues until the user types `exit`.

## Requirements

- Python 3.9+
- A Gemini API key

### Dependencies

```bash
pip install python-dotenv google-genai chromadb pypdf langchain-text-splitters
```

## Setup

1. Clone or copy this project into a directory containing your target PDF.
2. Create a `.env` file in the project root:

   ```
   GEMINI_API_KEY=your_api_key_here
   ```

3. Place the PDF you want to query in the project root. The filename is set in `pdf_reader.py`:

   ```python
   reader = PdfReader("AI_Healthcare_Sector_Market_Report.pdf")
   ```

## Usage

Run the script:

```bash
python pdf_reader.py
```

You'll see:

```
--- Ask anything about your pdf (type 'exit' to quit) ---
```

Ask questions naturally, including follow-ups:

```
> What is the AI healthcare market size?
Assistant: The global AI in healthcare market size was evaluated at $15.4 billion in 2024.

> What about in 2030?
What is the projected AI healthcare market size in 2030?
Assistant: The AI in healthcare market size is projected to reach $187.9 billion by 2030.
```

Type `exit` at any point to quit.

## Notes & Limitations

- **In-memory vector store** — `chromadb.Client()` is ephemeral. The PDF is re-chunked and re-indexed every time you run the script.
- **Grounding** — The assistant is instructed to answer only from retrieved PDF context and to say *"I don't know based on the provided document"* when the answer isn't found.
- **Cost/latency** — Each turn makes two Gemini calls (one to rewrite the query, one to generate the answer).

