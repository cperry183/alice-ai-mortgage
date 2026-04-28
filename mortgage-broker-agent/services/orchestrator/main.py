from fastapi import FastAPI
import requests
import time

app = FastAPI()

LEAD_URL = "http://lead-agent/process"
LOAN_URL = "http://loan-agent/evaluate"
DOC_URL = "http://doc-agent/submit"
DOC_RESULT_URL = "http://doc-agent/result"
UNDERWRITE_URL = "http://underwriting-agent/underwrite"


@app.post("/pipeline")
def pipeline(data: dict):
    # Step 1: Lead
    lead = requests.post(LEAD_URL, json=data).json()

    # Step 2: Loan Qualification
    loan = requests.post(LOAN_URL, json=lead).json()

    # Step 3: Document Processing (async)
    doc_job = requests.post(DOC_URL, json=loan).json()
    job_id = doc_job["job_id"]

    # Poll for result (simple version)
    for _ in range(10):
        result = requests.get(f"{DOC_RESULT_URL}/{job_id}").json()
        if "documents_verified" in result:
            loan = result
            break
        time.sleep(1)

    # Step 4: Underwriting
    decision = requests.post(UNDERWRITE_URL, json=loan).json()

    return decision
