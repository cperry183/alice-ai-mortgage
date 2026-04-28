import time
import redis
import json

r = redis.Redis(host="redis", port=6379, decode_responses=True)

def process_document(task):
    # Simulate parsing
    time.sleep(2)

    return {
        **task,
        "documents_verified": True
    }

while True:
    _, task_json = r.blpop("doc_queue")
    task = json.loads(task_json)

    result = process_document(task)
    r.set(task["job_id"], json.dumps(result))
