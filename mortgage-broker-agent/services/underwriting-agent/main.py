from fastapi import Depends, FastAPI
from agent import UnderwritingAgent
from rbac import require_agent_role

app = FastAPI()
agent = UnderwritingAgent()

@app.post("/underwrite")
def underwrite(data: dict, role: str = Depends(require_agent_role("orchestrator"))):
    return agent.run(data)
