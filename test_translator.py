#!/usr/bin/env python3
"""Manual integration test: requires internet, GROQ_API_KEY and CST availability."""
from backend.translator import translate

for question in ["Hello", "What is a book?", "What is machine learning?"]:
    print("\nQuestion:", question)
    try:
        answer = translate(question)
        for key in ("dzongkha", "roman", "gloss"):
            print(f"{key}: {answer.get(key, '')}")
    except Exception as exc:
        print("Error:", exc)