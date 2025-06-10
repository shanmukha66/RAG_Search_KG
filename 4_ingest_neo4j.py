from neo4j import GraphDatabase
import json
import os

# 1. Load QA data
with open("qa_data.json") as f:
    qa_data = json.load(f)

total = len(qa_data)
print(f"🚀 Starting ingestion of {total} QA triples into Neo4j…")

# 2. Connect to Neo4j
uri = "bolt://localhost:7687"
driver = GraphDatabase.driver(uri, auth=("neo4j", "password"))

def ingest_transaction(tx, doc_id, question, answer):
    tx.run(
        """
        MERGE (d:Document {id: $doc_id})
        MERGE (a:Answer {value: $answer})
        MERGE (d)-[r:HAS_ANSWER {question: $question}]->(a)
        """,
        doc_id=doc_id, question=question, answer=answer
    )

with driver.session() as session:
    for idx, entry in enumerate(qa_data, start=1):
        # Normalize docId to match image_name
        image_name = os.path.splitext(os.path.basename(entry["image"]))[0]
        question   = entry["question"]
        answer     = entry.get("answers", [""])[0]

        session.write_transaction(
            ingest_transaction,
            image_name,
            question,
            answer
        )

        # Log progress every 1000 records
        if idx % 1000 == 0 or idx == total:
            print(f"  • Ingested {idx}/{total} triples")

driver.close()
print("✅ Finished ingestion into Neo4j.")
