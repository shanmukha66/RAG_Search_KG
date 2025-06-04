"""Loader module for storing processed data in Neo4j and embeddings."""
from typing import Dict, List, Optional
import os
from neo4j import GraphDatabase
from sentence_transformers import SentenceTransformer
import weaviate

class DataLoader:
    def __init__(self):
        """Initialize connections to Neo4j and embedding storage."""
        # Neo4j connection
        self.neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.neo4j_user = os.getenv("NEO4J_USER", "neo4j")
        self.neo4j_password = os.getenv("NEO4J_PASSWORD")
        self.neo4j_driver = GraphDatabase.driver(
            self.neo4j_uri,
            auth=(self.neo4j_user, self.neo4j_password)
        )
        
        # Embedding model
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Weaviate client
        self.weaviate_client = weaviate.Client(
            url=os.getenv("WEAVIATE_URL", "http://localhost:8080")
        )
        
        # Ensure schema exists
        self._setup_weaviate_schema()
    
    def _setup_weaviate_schema(self):
        """Set up the Weaviate schema if it doesn't exist."""
        class_obj = {
            "class": "TextChunk",
            "vectorizer": "none",  # we'll provide our own vectors
            "properties": [
                {
                    "name": "content",
                    "dataType": ["text"],
                },
                {
                    "name": "source",
                    "dataType": ["string"],
                },
                {
                    "name": "metadata",
                    "dataType": ["text"],
                }
            ]
        }
        
        try:
            self.weaviate_client.schema.create_class(class_obj)
        except weaviate.exceptions.UnexpectedStatusCodeException:
            # Schema might already exist
            pass
    
    def store_chunk(self, content: str, metadata: Dict, source: str):
        """Store a chunk of text with its embedding."""
        # Generate embedding
        embedding = self.embedding_model.encode(content)
        
        # Store in Weaviate
        self.weaviate_client.data_object.create(
            "TextChunk",
            {
                "content": content,
                "source": source,
                "metadata": str(metadata)
            },
            vector=embedding.tolist()
        )
    
    def store_entity(self, entity: Dict):
        """Store an entity in Neo4j."""
        with self.neo4j_driver.session() as session:
            session.execute_write(self._create_entity_tx, entity)
    
    def store_relation(self, entity1: Dict, entity2: Dict, relation_type: str):
        """Store a relation between entities in Neo4j."""
        with self.neo4j_driver.session() as session:
            session.execute_write(
                self._create_relation_tx,
                entity1,
                entity2,
                relation_type
            )
    
    @staticmethod
    def _create_entity_tx(tx, entity):
        query = (
            "MERGE (e:Entity {name: $name, type: $type}) "
            "SET e.start = $start, e.end = $end"
        )
        tx.run(
            query,
            name=entity['word'],
            type=entity['entity'],
            start=entity['start'],
            end=entity['end']
        )
    
    @staticmethod
    def _create_relation_tx(tx, entity1, entity2, relation_type):
        query = (
            "MATCH (e1:Entity {name: $name1, type: $type1}) "
            "MATCH (e2:Entity {name: $name2, type: $type2}) "
            "MERGE (e1)-[r:" + relation_type + "]->(e2)"
        )
        tx.run(
            query,
            name1=entity1['word'],
            type1=entity1['entity'],
            name2=entity2['word'],
            type2=entity2['entity']
        )
    
    def close(self):
        """Close connections."""
        self.neo4j_driver.close() 