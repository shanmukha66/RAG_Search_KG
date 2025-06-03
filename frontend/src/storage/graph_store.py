from typing import Dict, Any, List, Optional
from neo4j import AsyncGraphDatabase
from neo4j.exceptions import ServiceUnavailable

class GraphStore:
    def __init__(
        self,
        uri: str = "bolt://localhost:7687",
        user: str = "neo4j",
        password: str = "password"
    ):
        self.driver = AsyncGraphDatabase.driver(uri, auth=(user, password))
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
    
    async def close(self):
        await self.driver.close()
    
    async def store_entity(
        self,
        entity: Dict[str, Any],
        relationships: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """
        Store an entity and its relationships in the graph
        """
        async with self.driver.session() as session:
            # Create entity node
            result = await session.run(
                """
                CREATE (e:Entity)
                SET e = $properties
                RETURN e.id as id
                """,
                properties=entity
            )
            entity_id = await result.single()["id"]
            
            # Create relationships if provided
            if relationships:
                for rel in relationships:
                    await session.run(
                        """
                        MATCH (e1:Entity {id: $from_id})
                        MATCH (e2:Entity {id: $to_id})
                        CREATE (e1)-[r:RELATES {type: $type}]->(e2)
                        SET r = $properties
                        """,
                        from_id=entity_id,
                        to_id=rel["to_id"],
                        type=rel["type"],
                        properties=rel.get("properties", {})
                    )
            
            return entity_id
    
    async def search(
        self,
        entities: List[Dict[str, Any]],
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search for entities and their relationships
        """
        async with self.driver.session() as session:
            # Build match conditions for each entity
            match_conditions = []
            where_conditions = []
            for i, entity in enumerate(entities):
                match_conditions.append(f"(e{i}:Entity)")
                for key, value in entity.items():
                    where_conditions.append(f"e{i}.{key} = ${key}_{i}")
            
            # Construct Cypher query
            query = f"""
            MATCH {', '.join(match_conditions)}
            WHERE {' AND '.join(where_conditions)}
            WITH e0
            MATCH (e0)-[r]-(related)
            RETURN e0 as entity,
                   collect({{
                       relationship: type(r),
                       properties: r,
                       entity: related
                   }}) as connections
            LIMIT $limit
            """
            
            # Prepare parameters
            params = {"limit": limit}
            for i, entity in enumerate(entities):
                for key, value in entity.items():
                    params[f"{key}_{i}"] = value
            
            # Execute query
            results = []
            records = await session.run(query, params)
            async for record in records:
                entity = dict(record["entity"])
                connections = [
                    {
                        "type": conn["relationship"],
                        "properties": dict(conn["properties"]),
                        "entity": dict(conn["entity"])
                    }
                    for conn in record["connections"]
                ]
                results.append({
                    "entity": entity,
                    "connections": connections
                })
            
            return results
    
    async def update_entity(
        self,
        entity_id: str,
        properties: Dict[str, Any]
    ) -> bool:
        """
        Update entity properties
        """
        async with self.driver.session() as session:
            result = await session.run(
                """
                MATCH (e:Entity {id: $id})
                SET e += $properties
                RETURN e
                """,
                id=entity_id,
                properties=properties
            )
            return await result.single() is not None
    
    async def delete_entity(self, entity_id: str) -> bool:
        """
        Delete an entity and its relationships
        """
        async with self.driver.session() as session:
            result = await session.run(
                """
                MATCH (e:Entity {id: $id})
                DETACH DELETE e
                """,
                id=entity_id
            )
            return result.consume().counters.nodes_deleted > 0
    
    async def get_entity(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """
        Get entity by ID
        """
        async with self.driver.session() as session:
            result = await session.run(
                """
                MATCH (e:Entity {id: $id})
                RETURN e
                """,
                id=entity_id
            )
            record = await result.single()
            return dict(record["e"]) if record else None 