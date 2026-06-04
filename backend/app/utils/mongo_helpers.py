from bson import ObjectId


def fix_mongo(doc):
    if isinstance(doc, list):
        return [fix_mongo(i) for i in doc]
    if isinstance(doc, dict):
        return {k: fix_mongo(v) for k, v in doc.items()}
    if isinstance(doc, ObjectId):
        return str(doc)
    return doc
