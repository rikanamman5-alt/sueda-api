from pymongo import MongoClient
import json

client = MongoClient("mongodb://localhost:27017")
db = client["sueda_db"]

cols = db.list_collection_names()
print(f"\n=== SUEDA DB - {len(cols)} collections ===\n")

for col_name in sorted(cols):
    col = db[col_name]
    count = col.count_documents({})
    print(f"[{col_name}] ({count} documents)")

    if count > 0:
        docs = col.find().limit(5)
        for doc in docs:
            doc["_id"] = str(doc["_id"])
            print(json.dumps(doc, indent=2, default=str))
            print("---")
    print()

client.close()
