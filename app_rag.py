from langchain import LLMChain, PromptTemplate
from langchain.agents import Tool, initialize_agent, AgentType
from langchain.chat_models import ChatOpenAI
from langchain.vectorstores import Qdrant
from neo4j import GraphDatabase
import os
from dotenv import load_dotenv
load_dotenv()
from langchain.chains import LLMChain
from langchain_core.prompts import PromptTemplate
from langchain.chat_models import ChatOpenAI

# 1. LLM
llm = ChatOpenAI(
  model="gpt-4o", 
  temperature=0,
  openai_api_key=os.environ["OPENAI_API_KEY"]
)


# 2. Qdrant retriever
qdrant = Qdrant(
    url=os.environ["QDRANT_URL"],
    prefer_grpc=True,
    collection_name="spdocvqa_chunks"
)
vector_retriever = qdrant.as_retriever(search_kwargs={"k": 3})

# 3. Neo4j function
driver = GraphDatabase.driver(
  os.environ["NEO4J_URI"],
  auth=(os.environ["NEO4J_USER"], os.environ["NEO4J_PASSWORD"])
)
def graph_query(question: str) -> str:
    with driver.session() as session:
        result = session.run(
            "MATCH (d:Document)-[r:HAS_ANSWER {question:$q}]->(a) RETURN a.value AS answer",
            q=question
        )
        rec = result.single()
        return rec["answer"] if rec else "No graph answer found."

# 4. Wrap tools
tools = [
    Tool(
        name="SemanticSearch",
        func=vector_retriever.get_relevant_documents,
        description="Useful to find relevant text snippets"
    ),
    Tool(
        name="GraphLookup",
        func=graph_query,
        description="Useful to get exact answer from the QA graph"
    ),
]

# 5. Initialize agent
agent = initialize_agent(
    tools, llm, agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION, verbose=True
)

# 6. Run a query
user_question = "What is the ‘actual’ value per 1000, during the year 1975?"
response = agent.run(user_question)
print("🔍 RAG Response:\n", response)
