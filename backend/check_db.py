import chromadb

client = chromadb.PersistentClient(path='chroma_db')
collections = client.list_collections()
print('Collections:', [c.name for c in client.list_collections()])

for c in client.list_collections():
    coll = client.get_collection(c.name)
    count = coll.count()
    print(f'Collection: {c.name}, Count: {count}')
    if count > 0:
        sample = coll.get(include=['metadatas', 'documents'], limit=3)
        docs = sample.get('documents', [])
        metas = sample.get('metadatas', [])
        for i, (doc, meta) in enumerate(zip(docs, metas)):
            print(f'  Doc {i}: source_id={meta.get("source_id")}, owner={meta.get("owner_user_id")}, type={meta.get("source_type")}')
            print(f'  Text preview: {doc[:100] if doc else "EMPTY"}')
            print()