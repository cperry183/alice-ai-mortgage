from fastapi import FastAPI
import redis
import uuid
import json

app = FastAPI()
r = redis.Redis(host="redis", port=6379, decode_responses=True)

@app.post("/submit")
def submit(data: dict):
    job_id = str(uuid.uuid4())
    data["job_id"] = job_id

    r.rpush("doc_queue", json.dumps(data))

    return {"job_id": job_id}

@app.get("/result/{job_id}")
def result(job_id: str):
    res = r.get(job_id)
    return json.loads(res) if res else {"status": "processing"}
