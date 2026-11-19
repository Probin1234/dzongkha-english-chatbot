
import os
from groq import Groq

api_key = os.getenv("GROQ_API_KEY")

if not api_key:
    raise RuntimeError("GROQ_API_KEY is missing")

client = Groq(api_key=api_key)

try:
    response = client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=[
            {
                "role": "user",
                "content": "Say hello in English."
            }
        ],
        max_tokens=50
    )

    print("SUCCESS!")
    print(response.choices[0].message.content)

except Exception as error:
    print("Groq connection failed:")
    print(type(error).__name__)
    print(str(error)[:600])
