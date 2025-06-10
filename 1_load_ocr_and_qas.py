import json
import os

# Set your paths
ocr_path = "/Volumes/workspace/Aparavi/RAG_Search_KG/spdocvqa_ocr"
qa_path  = "/Volumes/workspace/Aparavi/RAG_Search_KG/spdocvqa_qas"

# Load QA entries
qa_data = []
for fname in os.listdir(qa_path):
    if not fname.endswith(".json"):
        continue
    with open(os.path.join(qa_path, fname)) as f:
        obj = json.load(f)
        # If it's a dict with "data", extend with that list
        if isinstance(obj, dict) and "data" in obj:
            qa_data.extend(obj["data"])
        # If it's already a list, extend directly
        elif isinstance(obj, list):
            qa_data.extend(obj)

# Load OCR data
ocr_data = {}
for fname in os.listdir(ocr_path):
    if not fname.endswith(".json"):
        continue
    with open(os.path.join(ocr_path, fname)) as f:
        doc_ocr = json.load(f)
        doc_id = os.path.splitext(fname)[0]
        lines = doc_ocr["recognitionResults"][0]["lines"]
        full_text = "\n".join(line["text"] for line in lines)
        ocr_data[doc_id] = full_text

# Store QA data
with open("qa_data.json", "w") as f:
    json.dump(qa_data, f, indent=4)

# Store OCR data
with open("ocr_data.json", "w") as f:
    json.dump(ocr_data, f, indent=4)

# Quick sanity check
print("OCR loaded:", list(ocr_data.keys())[:3])
print("Sample OCR:", ocr_data[list(ocr_data.keys())[0]][:200])
print("First QA entry:", qa_data[0])
print("Total QA entries:", len(qa_data))
