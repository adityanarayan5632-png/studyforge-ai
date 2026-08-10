from sentence_transformers import SentenceTransformer

model = SentenceTransformer(
    "BAAI/bge-small-en-v1.5"
)

def create_embeddings(chunks):
    embeddings = model.encode(chunks)
    return embeddings