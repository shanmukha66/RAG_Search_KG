from typing import List, Dict, Any
from neo4j import GraphDatabase
from neo4j.exceptions import Neo4jError

class GraphStore:
    def __init__(self, uri: str = "bolt://localhost:7687", user: str = "neo4j", password: str = "password"):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
    
    def close(self):
        self.driver.close()
    
    async def create_entity(self, entity_type: str, properties: Dict[str, Any]) -> str:
        """
        Create a new entity node in the graph
        
        Args:
            entity_type: Type of entity (e.g., 'Person', 'Document', 'Image')
            properties: Entity properties
        
        Returns:
            ID of created entity
        """
        query = (
            f"CREATE (e:{entity_type} $properties) "
            "RETURN id(e) as entity_id"
        )
        
        with self.driver.session() as session:
            result = session.run(query, properties=properties)
            record = result.single()
            return str(record["entity_id"])
    
    async def create_relationship(
        self,
        from_id: str,
        to_id: str,
        relationship_type: str,
        properties: Dict[str, Any] = None
    ):
        """
        Create a relationship between two entities
        
        Args:
            from_id: Source entity ID
            to_id: Target entity ID
            relationship_type: Type of relationship
            properties: Optional relationship properties
        """
        query = (
            "MATCH (a), (b) "
            "WHERE id(a) = $from_id AND id(b) = $to_id "
            f"CREATE (a)-[r:{relationship_type} $properties]->(b) "
            "RETURN type(r)"
        )
        
        with self.driver.session() as session:
            session.run(
                query,
                from_id=int(from_id),
                to_id=int(to_id),
                properties=properties or {}
            )
    
    async def search_entities(
        self,
        entity_type: str = None,
        properties: Dict[str, Any] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search for entities with optional type and property filters
        """
        where_clauses = []
        params = {}
        
        if entity_type:
            where_clauses.append(f"e:{entity_type}")
        
        if properties:
            for key, value in properties.items():
                where_clauses.append(f"e.{key} = ${key}")
                params[key] = value
        
        where_statement = " AND ".join(where_clauses)
        query = (
            "MATCH (e) "
            f"WHERE {where_statement} " if where_statement else "MATCH (e) "
            "RETURN e "
            "LIMIT $limit"
        )
        
        params['limit'] = limit
        
        with self.driver.session() as session:
            result = session.run(query, params)
            return [dict(record["e"]) for record in result]
    
    async def traverse_graph(
        self,
        start_id: str,
        relationship_type: str = None,
        max_depth: int = 2
    ) -> List[Dict[str, Any]]:
        """
        Traverse the graph starting from an entity
        """
        rel_type = f":{relationship_type}" if relationship_type else ""
        query = (
            "MATCH path = (start)-[" + rel_type + "*1.." + str(max_depth) + "]->(related) "
            "WHERE id(start) = $start_id "
            "RETURN path"
        )
        
        with self.driver.session() as session:
            result = session.run(query, start_id=int(start_id))
            # Process and return path information
            paths = []
            for record in result:
                path = record["path"]
                path_info = {
                    "nodes": [dict(node) for node in path.nodes],
                    "relationships": [
                        {
                            "type": rel.type,
                            "properties": dict(rel)
                        } for rel in path.relationships
                    ]
                }
                paths.append(path_info)
            return paths 