from neo4j import GraphDatabase
import json
import os
from typing import List, Dict
from tqdm import tqdm
import multiprocessing
from concurrent.futures import ThreadPoolExecutor
import time
import random
from neo4j.exceptions import TransientError

def init_neo4j():
    """Initialize Neo4j database with constraints and indexes"""
    uri = "bolt://localhost:7687"
    driver = GraphDatabase.driver(uri, auth=("neo4j", "password"))
    
    def clean_database(tx):
        # Remove all nodes and relationships
        tx.run("MATCH (n) DETACH DELETE n")
    
    def drop_constraints(tx):
        # Drop existing constraints
        tx.run("DROP CONSTRAINT document_id IF EXISTS")
        tx.run("DROP CONSTRAINT question_id IF EXISTS")
    
    def create_constraints(tx):
        # Create constraints for unique IDs
        tx.run("CREATE CONSTRAINT document_id IF NOT EXISTS FOR (d:Document) REQUIRE d.id IS UNIQUE")
        tx.run("CREATE CONSTRAINT question_id IF NOT EXISTS FOR (q:Question) REQUIRE q.id IS UNIQUE")
    
    def create_indexes(tx):
        # Create indexes for better search performance
        tx.run("CREATE INDEX document_text IF NOT EXISTS FOR (d:Document) ON (d.text)")
        tx.run("CREATE INDEX question_text IF NOT EXISTS FOR (q:Question) ON (q.text)")
        tx.run("CREATE INDEX document_image IF NOT EXISTS FOR (d:Document) ON (d.image_path)")
    
    with driver.session() as session:
        print("Cleaning database...")
        session.execute_write(clean_database)
        
        print("Dropping existing constraints...")
        session.execute_write(drop_constraints)
        
        print("Creating new constraints...")
        session.execute_write(create_constraints)
        
        print("Creating indexes...")
        session.execute_write(create_indexes)
        
        print("✅ Database initialized successfully")
    
    return driver

def process_entry_with_retry(driver, entry, ocr_data, max_retries=5):
    retry_count = 0
    while retry_count < max_retries:
        try:
            with driver.session() as session:
                # Extract image name from the path
                image_name = entry.get('image', '').split('/')[-1] if entry.get('image') else ''
                doc_id = image_name.split('.')[0] if image_name else ''
                
                # Skip if no valid document ID
                if not doc_id:
                    return False
                
                # Get OCR text
                doc_text = ocr_data.get(doc_id, {}).get('text', '') if isinstance(ocr_data.get(doc_id), dict) else ''
                
                # Construct full image path
                image_path = os.path.join('spdocvqa_images', image_name) if image_name else ''
                
                # Create Document node with image_path
                cypher_query = """
                MERGE (d:Document {id: $doc_id})
                ON CREATE SET 
                    d.text = $doc_text,
                    d.image_path = $image_path
                ON MATCH SET 
                    d.text = $doc_text,
                    d.image_path = $image_path
                WITH d
                MERGE (q:Question {id: $qa_id})
                ON CREATE SET 
                    q.text = $question,
                    q.answer = $answer
                ON MATCH SET 
                    q.text = $question,
                    q.answer = $answer
                MERGE (d)-[r:HAS_QUESTION]->(q)
                """
                
                # Generate a unique ID for the QA pair
                qa_id = f"{doc_id}_qa_{abs(hash(entry.get('question', '')))}"
                
                session.run(
                    cypher_query,
                    doc_id=doc_id,
                    doc_text=doc_text,
                    qa_id=qa_id,
                    question=str(entry.get('question', '')),
                    answer=str(entry.get('answer', '')),
                    image_path=image_path
                )
                return True
        except Exception as e:
            print(f"Error processing entry (attempt {retry_count + 1}): {str(e)}")
            retry_count += 1
            time.sleep(0.1 * (2 ** retry_count))  # Exponential backoff
    return False

def process_batch(args):
    """Process a batch of entries"""
    batch, ocr_data, driver = args
    results = []
    for entry in batch:
        success = process_entry_with_retry(driver, entry, ocr_data)
        results.append(success)
    return sum(results)

def main():
    """Main function to initialize Neo4j and process data"""
    try:
        # Initialize Neo4j
        driver = init_neo4j()
        print("✅ Neo4j initialized successfully")
        
        # Load QA data
        print("Loading QA data...")
        with open("qa_data.json", "r") as f:
            qa_data = json.load(f)
        
        # Load OCR data
        print("Loading OCR data...")
        with open("ocr_data.json", "r") as f:
            ocr_data = json.load(f)
        
        # Process in batches with parallel processing
        batch_size = 50
        num_workers = min(4, multiprocessing.cpu_count())
        
        # Prepare batches
        batches = []
        for i in range(0, len(qa_data), batch_size):
            batch = qa_data[i:i + batch_size]
            batches.append((batch, ocr_data, driver))
        
        print(f"Processing {len(qa_data)} entries with {num_workers} workers...")
        total_processed = 0
        
        # Process batches with progress bar
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            with tqdm(total=len(qa_data), desc="Ingesting data") as pbar:
                for processed in executor.map(process_batch, batches):
                    total_processed += processed
                    pbar.update(batch_size)
                    time.sleep(0.1)  # Small delay between batches
        
        print(f"✅ Data ingestion completed. Successfully processed {total_processed} entries")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
    finally:
        if 'driver' in locals():
            driver.close()

if __name__ == "__main__":
    main() 