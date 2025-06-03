from neo4j import GraphDatabase
from config import config

def test_connection():
    try:
        # Create a driver instance
        driver = GraphDatabase.driver(
            config["neo4j"]["uri"],
            auth=(config["neo4j"]["user"], config["neo4j"]["password"])
        )
        
        # Verify connectivity
        driver.verify_connectivity()
        print("Successfully connected to Neo4j!")
        
        # Create a test node
        with driver.session() as session:
            result = session.run("CREATE (n:Test {name: 'test'}) RETURN n")
            print("Successfully created test node!")
        
        driver.close()
        return True
    except Exception as e:
        print(f"Error connecting to Neo4j: {str(e)}")
        return False

if __name__ == "__main__":
    test_connection() 