from embedder import model
from vector_store import search

question = "What are the core capabilities of Faith AI GPT?"

query_embedding = model.encode(question)

results = search(query_embedding)

print("\n=== SEARCH RESULTS ===\n")

for doc in results["documents"][0]:
    print(doc[:800])
    print("\n" + "="*80 + "\n")