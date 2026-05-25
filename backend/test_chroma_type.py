import chromadb
client = chromadb.Client()
col = client.create_collection("test")

try:
    col.add(documents=["hello", ""], ids=["1", "2"])
    print("Empty string works.")
except Exception as e:
    print(f"Empty string failed: {e}")

try:
    col.add(documents=["hello", None], ids=["3", "4"])
    print("None works.")
except Exception as e:
    print(f"None failed: {e}")

try:
    col.add(documents=[["hello"]], ids=["5"])
    print("Nested list works.")
except Exception as e:
    print(f"Nested list failed: {e}")
