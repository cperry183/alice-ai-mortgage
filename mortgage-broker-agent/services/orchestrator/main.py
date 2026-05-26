from fastapi import Depends, FastAPI, HTTPException
import requests
import time
from requests import RequestException
from rbac import agent_auth_headers, require_agent_role

app = FastAPI()

LEAD_URL = "http://lead-agent/process"
LOAN_URL = "http://loan-agent/evaluate"
DOC_URL = "http://doc-agent/submit"
DOC_RESULT_URL = "http://doc-agent/result"
UNDERWRITE_URL = "http://underwriting-agent/underwrite"
REQUEST_TIMEOUT_SECONDS = 10


def post_agent(url: str, payload: dict, headers: dict[str, str]) -> dict:
    response = requests.post(
        url,
        json=payload,
        headers=headers,
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return response.json()


def get_agent(url: str, headers: dict[str, str]) -> dict:
    response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT_SECONDS)
    response.raise_for_status()
    return response.json()


@app.post("/pipeline")
def pipeline(data: dict, role: str = Depends(require_agent_role("broker", "admin"))):
    headers = agent_auth_headers()
    if not headers:
        raise HTTPException(status_code=503, detail="Agent RBAC is not configured")

    try:
        # Step 1: Lead
        lead = post_agent(LEAD_URL, data, headers)

        # Step 2: Loan Qualification
        loan = post_agent(LOAN_URL, lead, headers)

        # Step 3: Document Processing (async)
        doc_job = post_agent(DOC_URL, loan, headers)
        job_id = doc_job["job_id"]

        # Poll for result (simple version)
        for _ in range(10):
            result = get_agent(f"{DOC_RESULT_URL}/{job_id}", headers)
            if "documents_verified" in result:
                loan = result
                break
            time.sleep(1)

        # Step 4: Underwriting
        decision = post_agent(UNDERWRITE_URL, loan, headers)
    except RequestException as exc:
        raise HTTPException(status_code=502, detail=f"Agent call failed: {exc}") from exc

    return decision
