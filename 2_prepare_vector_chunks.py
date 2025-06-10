import json
import os
import textwrap

# Load OCR data
with open("ocr_data.json", "r") as f:
    ocr_data = json.load(f)

# Load QA data (already a list of QA objects)
with open("qa_data.json", "r") as f:
    qa_data = json.load(f)  # This is a list, no "data" key

# Debug: Check the first QA object
print("✅ First QA entry:", qa_data[0])

# Store vector-ready samples
vector_samples = []

for entry in qa_data:
    # Ensure we skip any malformed entries (like string keys)
    if not isinstance(entry, dict):
        continue
    if "image" not in entry or "question" not in entry:
        continue

    # Normalize image name (e.g., documents/abc_123.png → abc_123)
    image_path = entry["image"]
    image_name = os.path.splitext(os.path.basename(image_path))[0]

    # Match to OCR
    if image_name not in ocr_data:
        continue

    full_text = ocr_data[image_name]

    # Chunk the OCR text into 300-char chunks
    chunks = textwrap.wrap(full_text, width=300)

    # Add each chunk as a separate record
    for idx, chunk in enumerate(chunks):
        vector_samples.append({
            "id": f"{image_name}_chunk_{idx}",
            "doc_id": image_name,
            "text": chunk,
            "question": entry["question"],
            "answer": entry.get("answer", [""])[0],  # safe fallback
            "source": "spdocvqa"
        })

# Save to JSON for embedding in Chroma
with open("vector_chunks.json", "w") as f:
    json.dump(vector_samples, f, indent=2)

print("✅ Created", len(vector_samples), "chunks.")
