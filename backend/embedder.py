from sentence_transformers import SentenceTransformer

model = SentenceTransformer(
    "BAAI/bge-m3"
)

def create_embeddings(chunks):
    embeddings = model.encode(chunks, normalize_embeddings=True)
    return embeddings