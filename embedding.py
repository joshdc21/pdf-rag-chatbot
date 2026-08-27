# pyrefly: ignore [missing-import]
from sentence_transformers import SentenceTransformer

model = SentenceTransformer('all-MiniLM-L6-v2')

def embed_text(text):
    return model.encode(text).tolist()


if __name__ == "__main__":
    vector = embed_text("What is Supabase?")
    print(len(vector))
    print(vector[:5])