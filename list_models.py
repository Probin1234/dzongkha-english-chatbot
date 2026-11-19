
from groq import Groq

client = Groq()

try:
    models = client.models.list()

    print("AVAILABLE MODELS:")
    for model in models.data:
        print(model.id)

except Exception as error:
    print("ERROR:", type(error).__name__)
    print(str(error))
