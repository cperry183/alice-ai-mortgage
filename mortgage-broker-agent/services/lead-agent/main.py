from fastapi import FastAPI
from agent import LeadAgent

app = FastAPI()
agent = LeadAgent()

@app.post("/process")
def process(data: dict):
    return agent.run(data)
