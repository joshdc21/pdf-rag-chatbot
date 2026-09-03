from dotenv import load_dotenv 
import os 
import glob
import re
from google import genai 
# pyrefly: ignore [missing-import]
import chromadb
# pyrefly: ignore [missing-import]
from pypdf import PdfReader
# pyrefly: ignore [missing-import]
from langchain_text_splitters import RecursiveCharacterTextSplitter
import hashlib
from supabase_client import supabase
from embedding import embed_text

load_dotenv()

def hash_content(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def retrieve_documents(query, n_results=5, user_id=None):
    where_clause = {"user_id": user_id} if user_id else None
    return collection.query(
        query_texts=[query],
        n_results=n_results,
        where=where_clause
    )

def delete_document(user_id, filename):
    try:        
        # Delete from documents
        supabase.table("documents")\
            .delete()\
            .eq("user_id", user_id)\
            .eq("source", filename)\
            .execute()
        # Delete from storage
        supabase.storage \
            .from_("pdfs") \
            .remove([f"{user_id}/{filename}"])
            
        return True, f"Deleted '{filename}' successfully."
    except Exception as e:
        return False, f"Error deleting document: {str(e)}"

def rename_document(user_id, old_name, new_name):
    try:
        new_name = new_name.strip()

        if not new_name:
            return False, "Filename can not be empty"
        
        if new_name == old_name:
            return False, "New filename is the same as the current filename"

        existing = (
            supabase
            .storage
            .from_("pdfs")
            .list(user_id)
        )

        existing_names = {
            file_obj.get("name")
            for file_obj in existing
            if file_obj.get("name")
        }

        if new_name in existing_names:
            return False, f"File name already exist"

        # Rename from storage
        supabase.storage \
            .from_("pdfs") \
            .move(
                f"{user_id}/{old_name}",
                f"{user_id}/{new_name}"
            )
        # Rename from documents
        supabase.table("documents")\
            .update({"source": new_name})\
            .eq("user_id", user_id)\
            .eq("source", old_name)\
            .execute()
        return True, f"Renamed '{old_name}' to '{new_name}'."

    except Exception as e:
        return False, f"Error renaming document: {str(e)}"

#retrieve document from supabase
def retrieve_documents_supabase(query, n_results=5):
    embedding = embed_text(query)

    response = supabase.rpc(
        "match_documents",
        {
            "query_embedding": embedding,
            "match_count": n_results
        }
    ).execute()

    return response.data

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

# Create a local Vector Database using ChromaDB
chroma_client = chromadb.PersistentClient(path='./chroma_db')

# Collection is where you store related document(like a table in a database)
collection = chroma_client.get_or_create_collection(name="my_knowledge_base")

# Split the text into chunks
splitter = RecursiveCharacterTextSplitter( 
    chunk_size=500, chunk_overlap=50 
) 

def extract_pdf_pages_and_hash(file_source):
    """
    Extracts text page-by-page from a PDF and returns page list and SHA256 content hash.
    """
    reader = PdfReader(file_source)
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
    return pages, content_hash

def insert_chunk_to_supabase(file_source, filename, user_id=None, status_cb=None):
    def log(msg):
        if status_cb:
            status_cb(msg)

    log(f"Processing {filename}...")
    pages, content_hash = extract_pdf_pages_and_hash(file_source)

    # Check whether this PDF has already been processed
    existing = (
        supabase
        .table("documents")
        .select("id, content_hash")
        .eq("user_id", user_id)
        .eq("source", filename)
        .execute()
    )
    
    if existing.data:
        existing_hash = existing.data[0]["content_hash"]

        if existing_hash == content_hash:
            log(f"Skipping {filename} - already processed")
            return

        log(f"{filename} has changed - re-processing")
        supabase.table("documents").delete().eq("user_id", user_id).eq("source", filename).execute()

    rows = []

    for page in pages:
        page_chunks = splitter.split_text(page["text"])
        for chunk in page_chunks:
            embedding = embed_text(chunk)
            row = {
                "user_id": user_id,
                "content": chunk,
                "embedding": embedding,
                "source": filename,
                "page": page["page"],
                "content_hash": content_hash
            }
            rows.append(row)

    if rows:
        try:
            supabase.table("documents").insert(rows).execute()
            log(f"Added {filename} to Supabase")
        except Exception as e:
            log(f"Failed to insert rows: {e}")

    log(f"Number of chunks: {len(rows)}")


def ingest_single_pdf(file_source, filename, user_id=None, status_cb=None):
    """
    Ingests a single PDF file (either file path or file-like object) into ChromaDB.
    """
    def log(msg):
        if status_cb:
            status_cb(msg)

    log(f"Processing {filename}...")
    pages, content_hash = extract_pdf_pages_and_hash(file_source)

    # Check whether this PDF has already been processed
    where_cond = {"$and": [{"source": filename}, {"user_id": user_id}]} if user_id else {"source": filename}
    existing = collection.get(where=where_cond)

    if existing and existing.get("ids"):
        existing_hash = existing["metadatas"][0].get("content_hash")
        if existing_hash == content_hash:
            log(f"Skipping {filename} - already processed")
            return
        log(f"{filename} has changed - re-processing")
        collection.delete(where=where_cond)

    # Split the text into chunks
    chunks = []
    metadatas = []

    for page in pages:
        page_chunks = splitter.split_text(page["text"])
        for chunk in page_chunks:
            chunks.append(chunk)
            meta = {
                "source": filename,
                "page": page["page"],
                "content_hash": content_hash
            }
            if user_id:
                meta["user_id"] = user_id
            metadatas.append(meta)

    log(f"Number of chunks: {len(chunks)}")

    if chunks:
        collection.add(
            documents=chunks,
            ids=[f"{user_id}-{filename}-chunk-{i}" for i in range(len(chunks))],
            metadatas=metadatas
        )
        log(f"Added {filename} to ChromaDB")

def ingest_documents():
    pdf_files = glob.glob("documents/*.pdf")

    for pdf_file in pdf_files:
        filename = os.path.basename(pdf_file)
        ingest_single_pdf(pdf_file, filename, status_cb=print)

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
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        return response.text.strip()
    except Exception as e:
        print(f"Query rewrite failed: {e}")
        return user_query

def add_clickable_citations(response_text, user_id=None):
    pattern = r'\[(?:Source:\s*)?([^,\]]+\.pdf)(?:,\s*|\s*-\s*)Page:?\s*(\d+)\]'
    url_cache = {}

    def replace_citation(match):
        filename = match.group(1).strip()
        page_num = match.group(2).strip()
        cache_key = (filename, page_num)

        if cache_key not in url_cache:
            file_path = f"{user_id}/{filename}" if user_id else filename
            try:
                res = supabase.storage.from_("pdfs").create_signed_url(file_path, 3600)
                if isinstance(res, dict):
                    url = res.get("signedUrl") or res.get("signedURL") or str(res)
                else:
                    url = getattr(res, "signed_url", str(res))
            except Exception:
                url = supabase.storage.from_("pdfs").get_public_url(file_path)
            
            url_cache[cache_key] = f"{url}#page={page_num}"

        return f"[{filename} - Page {page_num}]({url_cache[cache_key]})"

    return re.sub(pattern, replace_citation, response_text)

def generate_rag_response(user_query, conversation_history, user_id=None):
    standalone_query = rewrite_query_with_history(user_query, conversation_history)
    results = retrieve_documents_supabase(standalone_query, n_results=5)

    retrieved_context = ""
    if results:
        for result in results:
            retrieved_context += (
                f"Source: {result['source']}\n"
                f"Page: {result['page']}\n"
                f"Content: {result['content']}\n\n"
            )

    history_text = "\n".join(
        f"{message['role']}: {message['content']}"
        for message in conversation_history
    )

    prompt = f"""You are a helpful assistant answering questions about the provided PDF documents.

Answer the user's current question using ONLY the provided PDF context.

Cite the relevant source and page number using the format [filename.pdf - Page: X] naturally at the end of key statements or paragraphs. Avoid repeating the same citation after every single sentence when consecutive sentences come from the same source.

Only cite sources and page numbers that appear in the provided PDF context.
Do not invent or guess page numbers.

Previous conversation history:
{history_text if history_text else "None"}

Relevant PDF context:
{retrieved_context}

Current question:
{user_query}

If the answer cannot be found in the provided PDF context, say:
"I don't know based on the provided document."

Do not use outside knowledge or invent information.
"""
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        return add_clickable_citations(response.text, user_id=user_id)
    except Exception as e:
        if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
            return "Rate limit reached for Gemini API. Please try again in a bit."
        raise e

if __name__ == "__main__":
    ingest_documents()
    print("\n--- Ask anything about your pdf(type 'exit' to quit) ---\n")
    while True: 
        user_query = input("Ask anything: ")
        if user_query.lower() == "exit":
            break

        try:
            answer = generate_rag_response(user_query, conversation_history)
            print(f"Assistant: {answer}\n")
            conversation_history.append({"role": "user", "content": user_query})
            conversation_history.append({"role": "assistant", "content": answer})
        except Exception as e:
            print(f"Error generating response: {e}")
            continue