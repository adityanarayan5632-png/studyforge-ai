import uuid

import chromadb

client = chromadb.PersistentClient(path="./chroma_db")
collection = client.get_or_create_collection(name="studyforge")


def store_chunks(chunks, embeddings, source_id: str | None = None) -> str:
    """
    Stores chunks under IDs namespaced by source_id, so uploading a second
    (or third, fourth...) source never collides with a previous one.

    Previously every upload wrote IDs "chunk_0", "chunk_1", ... — the second
    upload's IDs collided with the first's, chromadb raised on the
    duplicate-ID add, and the exception was silently swallowed. In practice
    that meant only the very first upload in the collection's lifetime was
    ever actually stored. Namespacing by source_id fixes that.
    """
    source_id = source_id or uuid.uuid4().hex
    ids = [f"{source_id}_chunk_{i}" for i in range(len(chunks))]
    metadatas = [{"source_id": source_id} for _ in chunks]
    collection.add(
        ids=ids,
        documents=chunks,
        embeddings=embeddings.tolist(),
        metadatas=metadatas,
    )
    return source_id


def get_collection_count():
    return collection.count()


def search(query_embedding, n_results=3):
    results = collection.query(
        query_embeddings=[query_embedding.tolist()],
        n_results=n_results,
    )
    return results
