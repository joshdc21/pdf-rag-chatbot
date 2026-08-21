from dotenv import load_dotenv 
import os 
import glob
from google import genai 
# pyrefly: ignore [missing-import]
import chromadb
# pyrefly: ignore [missing-import]
from pypdf import PdfReader
# pyrefly: ignore [missing-import]
from langchain_text_splitters import RecursiveCharacterTextSplitter

load_dotenv()

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

# Create a local Vector Database using ChromaDB
chroma_client = chromadb.PersistentClient(path='./chroma_db')

# Collection is where you store related document(like a table in a database)
collection = chroma_client.get_or_create_collection(name="my_knowledge_base")

# Split the text into chunks
splitter = RecursiveCharacterTextSplitter( 
    chunk_size=500, chunk_overlap=50 
) 

pdf_files = glob.glob("documents/*.pdf")

for pdf_file in pdf_files:
    print(pdf_file)
    filename = os.path.basename(pdf_file)
    # Check whether this PDF has already been ingested
    existing = collection.get(
        where={"source": filename}
    )

    if existing["ids"]:
        print(f"Skipping {filename} - already ingested")
        continue

    print(f"Processing {filename}")
    # Load the pdf
    reader = PdfReader(pdf_file)

    # extract text from pdf
    text = "" 
    for page in reader.pages: 
        page_text = page.extract_text() 
        if page_text: 
            text += page_text + "\n"

    # Split the text into chunks
    chunks = splitter.split_text(text) 

    print(f"Number of chunks: {len(chunks)}")

    collection.add(
        documents = chunks,
        ids = [
            f"{filename}-chunk-{i}" for i in range(len(chunks))
        ],
        metadatas = [
            {'source': filename}
            for _ in range(len(chunks))
        ]
    )
    print(f"Added {filename} to ChromaDB")

conversation_history = []

def rewrite_query_with_history(user_query, conversation_history):
    """
    Rewrites a follow-up question into a standalone, search-friendly query
    using the conversation history.
    """
    # if it isn't in the history, don't rewrite it
    if not conversation_history:
        return user_query

    #converts history into text so that gemini understand the context of the conversation
    history_text = "\n".join(
        f"{message['role']}: {message['content']}"
        for message in conversation_history
    )

    #look at the the previous conversation, and then figure out what the user wants
    prompt = f"""Given the following conversation history and a follow-up question, 
    rephrase the follow-up question to be a standalone search query that can be understood on its 
    own without needing the conversation history.

Do NOT answer the question. Only return the rephrased standalone query. If the follow-up question is already standalone, return it as is.

Conversation History:
{history_text}

Follow-up Question: {user_query}

Standalone Query:"""

    #rewrite the prompt, and then send it back
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt
    )
    return response.text.strip()

if __name__ == "__main__":
    print("\n--- Ask anything about your pdf(type 'exit' to quit) ---\n")
    while True: 
        user_query = input("Ask anything: ")
        if user_query.lower() == "exit":
            break

        standalone_query = rewrite_query_with_history(user_query, conversation_history)
        
        if standalone_query != user_query:
            print(f"{standalone_query}")

        results = collection.query(
            query_texts=[standalone_query],
            n_results=3
        )
        retrieved_context = ""

        for document, metadata in zip(
            results["documents"][0],
            results["metadatas"][0]
        ):
            retrieved_context += (
                f"Source: {metadata['source']}\n"
                f"Content: {document}\n\n"
            )

        history_text = "\n".join(
            f"{message['role']}: {message['content']}"
            for message in conversation_history
        )

        prompt = f"""You are a helpful assistant. Answer the user's current question using ONLY the 
        provided PDF context.
        For every factual claim in your answer, cite the PDF filename that supports it using this format:
        [Source: filename.pdf]
        Previous conversation history:
        {history_text if history_text else "None"}

        Relevant PDF context:
        {retrieved_context}

Current question:
{user_query}

If the answer cannot be found in the PDF context, say:
"I don't know based on the provided document." Do not invent facts outside the PDF context.
"""

        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )

        print(f"Assistant: {response.text}\n")
        
        conversation_history.append({
            "role": "user",
            "content": user_query
        })
        
        conversation_history.append({
            "role": "assistant",
            "content": response.text
        })