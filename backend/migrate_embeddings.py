"""Migration script to re-index all documents with multilingual embedding model."""

import chromadb
from pathlib import Path
from sentence_transformers import SentenceTransformer
from collections import defaultdict


OLD_COLLECTION_NAME = "studyforge"
NEW_COLLECTION_NAME = "studyforge_m3"
MODEL_NAME = "BAAI/bge-m3"


def migrate():
    print(f"Loading model: {MODEL_NAME}")
    model = SentenceTransformer(MODEL_NAME)
    print(f"Model loaded. Embedding dimension: {model.get_embedding_dimension()}")

    CHROMA_PATH = Path(__file__).parent / "chroma_db"
    client = chromadb.PersistentClient(path=str(CHROMA_PATH))

    # Get old collection
    print(f"Reading from old collection: {OLD_COLLECTION_NAME}")
    old_collection = client.get_collection(OLD_COLLECTION_NAME)

    # Create new collection
    print(f"Creating new collection: {NEW_COLLECTION_NAME}")
    new_collection = client.get_or_create_collection(
        name=NEW_COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"}
    )

    # Get all data from old collection
    data = old_collection.get(include=["metadatas", "documents"])
    docs = data["documents"]
    metas = data["metadatas"]
    ids = data["ids"]

    print(f"Total chunks to migrate: {len(docs)}")

    # Group by source_id to process in batches
    source_chunks = defaultdict(list)
    for doc, meta, id_ in zip(docs, metas, ids):
        source_chunks[meta["source_id"]].append((doc, meta, id_))

    print(f"Unique sources: {len(source_chunks)}")

    # Process each source
    total_migrated = 0
    for source_id, chunks in source_chunks.items():
        chunk_texts = [c[0] for c in chunks]
        chunk_metas = [c[1] for c in chunks]
        chunk_ids = [c[2] for c in chunks]

        print(f"  Migrating {source_id}: {len(chunks)} chunks...")

        # Generate new embeddings
        embeddings = model.encode(chunk_texts, normalize_embeddings=True)

        # Add to new collection
        new_collection.add(
            ids=chunk_ids,
            documents=chunk_texts,
            embeddings=embeddings.tolist(),
            metadatas=chunk_metas,
        )
        total_migrated += len(chunks)

    print(f"Migration complete. Total chunks migrated: {total_migrated}")

    # Verify new collection
    new_count = new_collection.count()
    print(f"New collection count: {new_count}")

    # Test a few queries
    print("\nTesting retrieval...")
    test_queries = [
        "Machine learning is a branch of artificial intelligence.",
        "मशीन लर्निंग आर्टिफिशियल इंटेलिजेंस की एक शाखा है।",
        "Quantum computing uses quantum bits called qubits.",
    ]
    for query in test_queries:
        q_emb = model.encode(query)
        results = new_collection.query(
            query_embeddings=[q_emb.tolist()],
            n_results=3,
        )
        print(f"Query: {query[:50]}...")
        print(f"  Results: {len(results['documents'][0])} docs")
        for i, (doc, meta, dist) in enumerate(zip(
            results["documents"][0][:2],
            results["metadatas"][0][:2],
            results["distances"][0][:2],
        )):
            print(f"    [{i}] dist={dist:.4f} source={meta.get('source_id')} owner={meta.get('owner_user_id')}: {doc[:60]}...")

    print("\nMigration successful!")


if __name__ == "__main__":
    migrate()