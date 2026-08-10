from rag_pipeline import answer_question

question = input("Ask a question: ")

answer = answer_question(question)

print("\n")
print("=" * 50)
print("ANSWER")
print("=" * 50)
print(answer)