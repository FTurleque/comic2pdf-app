import os, json, sys, tempfile
# Diagnostic script: simulate test POST to /jobs/prep with TestClient
os.environ['DATA_DIR'] = os.path.join(tempfile.gettempdir(), 'pp_debug_data')
os.environ['DISABLE_WORKERS'] = '1'
import shutil
shutil.rmtree(os.environ['DATA_DIR'], ignore_errors=True)
from fastapi.testclient import TestClient
from app.main import app, QUEUE_DIR, RUNNING_DIR
# ensure dirs
import os
os.makedirs(os.fspath(QUEUE_DIR), exist_ok=True)
# post
payload = { 'jobId': 'job-debug', 'inputPath': '/no', 'workDir': os.path.join(os.environ['DATA_DIR'],'work') }
with TestClient(app) as client:
    r = client.post('/jobs/prep', json=payload)
    print('status', r.status_code)
# inspect files
qpath = os.path.join(os.fspath(QUEUE_DIR),'job-debug.json')
rpath = os.path.join(os.fspath(RUNNING_DIR),'job-debug.json')
print('queue exists', os.path.exists(qpath), 'running exists', os.path.exists(rpath))
if os.path.exists(qpath):
    print('queue content:\n', open(qpath,'r',encoding='utf-8').read())
if os.path.exists(rpath):
    print('running content:\n', open(rpath,'r',encoding='utf-8').read())
print('DATA_DIR=', os.environ['DATA_DIR'])
print('QUEUE_DIR=', os.fspath(QUEUE_DIR))
print('RUNNING_DIR=', os.fspath(RUNNING_DIR))

