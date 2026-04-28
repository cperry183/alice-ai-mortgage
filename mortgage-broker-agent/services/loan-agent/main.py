from fastapi import FastAPI
from agent import LoanAgent

app = FastAPI()
agent = LoanAgent()

@app.post("/evaluate")
def evaluate(data: dict):
    return agent.evaluate(data)
