import chromadb
client = chromadb.Client()
col = client.create_collection("test2")

try:
    col.add(documents=["hello"], ids=["1"])
    print("Normal works.")
except Exception as e:
    print(f"Normal failed: {e}")

try:
    col.add(documents=[None], ids=["2"])
    print("None works.")
except Exception as e:
    print(f"None failed: {e}")
    
try:
    col.add(documents=[b"bytes"], ids=["3"])
    print("Bytes works.")
except Exception as e:
    print(f"Bytes failed: {e}")

try:
    col.add(documents=[""], ids=["4"])
    print("Empty works.")
except Exception as e:
    print(f"Empty failed: {e}")

try:
    col.add(documents=["hello", 123], ids=["5", "6"])
    print("Int works.")
except Exception as e:
    print(f"Int failed: {e}")
