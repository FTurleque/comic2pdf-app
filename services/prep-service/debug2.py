import os, tempfile, sys
print('ENV DATA_DIR before:', os.environ.get('DATA_DIR'))
os.environ['DATA_DIR']=os.path.join(tempfile.gettempdir(),'pp_debug2')
print('ENV DATA_DIR set to', os.environ['DATA_DIR'])
from app import main
print('QUEUE_DIR repr:', repr(main.QUEUE_DIR))
print('QUEUE_DIR fspath:', os.fspath(main.QUEUE_DIR))
print('QUEUE_DIR str:', str(main.QUEUE_DIR))
print('DISABLE_WORKERS:', os.environ.get('DISABLE_WORKERS'))
from fastapi.testclient import TestClient
from app.main import app
with TestClient(app) as client:
    resp = client.post('/jobs/prep', json={'jobId':'d2','inputPath':'/no','workDir':os.path.join(os.environ['DATA_DIR'],'work')})
    print('post status', resp.status_code)
import json
q = os.path.join(os.fspath(main.QUEUE_DIR),'d2.json')
print('queue path', q)
if os.path.exists(q):
    print('queue content:', open(q).read())
else:
    print('queue missing')

