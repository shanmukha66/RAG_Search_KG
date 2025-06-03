from typing import Any, Dict, List, Optional, Set, Tuple
from datetime import datetime
import neo4j
from neo4j import GraphDatabase

class KnowledgeGraph:
    """Neo4j-based knowledge graph storage."""
    
    def __init__(self, uri: str, username: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(username, password))
    
    def close(self):
        """Close the database connection."""
        self.driver.close()
    
    async def add_content_node(
        self,
        content_id: str,
        content_type: str,
        metadata: Dict[str, Any]
    ) -> str:
        """Add a content node to the graph."""
        query = """
        MERGE (c:Content {id: $content_id})
        SET c.type = $content_type,
            c.metadata = $metadata,
            c.created_at = $created_at,
            c.updated_at = $updated_at
        RETURN c.id
        """
        
        with self.driver.session() as session:
            result = session.run(
                query,
                content_id=content_id,
                content_type=content_type,
                metadata=metadata,
                created_at=datetime.utcnow().isoformat(),
                updated_at=datetime.utcnow().isoformat()
            )
            return result.single()[0]
    
    async def add_entity(
        self,
        entity_type: str,
        name: str,
        properties: Dict[str, Any]
    ) -> str:
        """Add an entity node to the graph."""
        query = """
        MERGE (e:Entity {type: $entity_type, name: $name})
        SET e += $properties,
            e.updated_at = $updated_at
        RETURN e.name
        """
        
        with self.driver.session() as session:
            result = session.run(
                query,
                entity_type=entity_type,
                name=name,
                properties=properties,
                updated_at=datetime.utcnow().isoformat()
            )
            return result.single()[0]
    
    async def add_relationship(
        self,
        from_id: str,
        to_id: str,
        relationship_type: str,
        properties: Optional[Dict[str, Any]] = None
    ) -> None:
        """Add a relationship between nodes."""
        properties = properties or {}
        query = """
        MATCH (from {id: $from_id})
        MATCH (to {id: $to_id})
        MERGE (from)-[r:$relationship_type]->(to)
        SET r += $properties,
            r.created_at = $created_at
        """
        
        with self.driver.session() as session:
            session.run(
                query,
                from_id=from_id,
                to_id=to_id,
                relationship_type=relationship_type,
                properties=properties,
                created_at=datetime.utcnow().isoformat()
            )
    
    async def search_content(
        self,
        content_type: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search for content nodes based on criteria."""
        conditions = []
        params = {}
        
        if content_type:
            conditions.append("c.type = $content_type")
            params["content_type"] = content_type
        
        if properties:
            for key, value in properties.items():
                conditions.append(f"c.metadata.{key} = ${key}")
                params[key] = value
        
        where_clause = " AND ".join(conditions) if conditions else "TRUE"
        
        query = f"""
        MATCH (c:Content)
        WHERE {where_clause}
        RETURN c
        LIMIT $limit
        """
        params["limit"] = limit
        
        with self.driver.session() as session:
            result = session.run(query, params)
            return [dict(record["c"]) for record in result]
    
    async def get_related_entities(
        self,
        content_id: str,
        relationship_type: Optional[str] = None,
        entity_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get entities related to a content node."""
        conditions = []
        params = {"content_id": content_id}
        
        if relationship_type:
            conditions.append("type(r) = $rel_type")
            params["rel_type"] = relationship_type
        
        if entity_type:
            conditions.append("e.type = $entity_type")
            params["entity_type"] = entity_type
        
        where_clause = " AND ".join(conditions) if conditions else "TRUE"
        
        query = f"""
        MATCH (c:Content {{id: $content_id}})-[r]->(e:Entity)
        WHERE {where_clause}
        RETURN e, type(r) as relationship_type, r.properties as relationship_props
        """
        
        with self.driver.session() as session:
            result = session.run(query, params)
            return [{
                "entity": dict(record["e"]),
                "relationship": {
                    "type": record["relationship_type"],
                    "properties": record["relationship_props"]
                }
            } for record in result]
    
    async def find_paths(
        self,
        start_id: str,
        end_id: str,
        max_depth: int = 3
    ) -> List[List[Dict[str, Any]]]:
        """Find paths between two nodes."""
        query = """
        MATCH path = shortestPath((start {id: $start_id})-[*..%d]->(end {id: $end_id}))
        RETURN path
        """ % max_depth
        
        with self.driver.session() as session:
            result = session.run(query, start_id=start_id, end_id=end_id)
            paths = []
            
            for record in result:
                path = record["path"]
                path_nodes = []
                
                for i, node in enumerate(path.nodes):
                    node_dict = dict(node)
                    if i < len(path.relationships):
                        rel = path.relationships[i]
                        node_dict["next_relationship"] = {
                            "type": type(rel).__name__,
                            "properties": dict(rel)
                        }
                    path_nodes.append(node_dict)
                
                paths.append(path_nodes)
            
            return paths 