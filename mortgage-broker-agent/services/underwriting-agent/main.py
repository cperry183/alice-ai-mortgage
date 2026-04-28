from fastapi import FastAPI
from agent import UnderwritingAgent

app = FastAPI()
agent = UnderwritingAgent()

@app.post("/underwrite")
def underwrite(data: dict):
    return agent.run(data)
