import json
import os
import tempfile

# 自测使用独立临时数据库，绝不触碰真实 data/app.db
os.environ["APP_DB_PATH"] = os.path.join(tempfile.gettempdir(), "code_paas_smoke_test.db")
if os.path.exists(os.environ["APP_DB_PATH"]):
    os.remove(os.environ["APP_DB_PATH"])

from app import app

c = app.test_client()

def login(u, p):
    return c.post('/api/auth/login', json={'username': u, 'password': p}).get_json()['data']['token']

h = {'Authorization': 'Bearer ' + login('admin', 'admin123')}

r = c.post('/api/customer/draft', json={'customer_name': '测试客户D', 'customer_type': 'PERSONAL', 'customer_level': 'NORMAL'}, headers=h)
cid = r.get_json()['data']['id']
c.post(f'/api/customer/{cid}/submit', headers=h)

mh = {'Authorization': 'Bearer ' + login('cmanager', '123456')}
r = c.get('/api/workbench/todo', headers=mh)
t = r.get_json()['data']['list'][0]
r = c.post(f"/api/workbench/todo/{t['id']}/reject", json={'comment': '资料不全'}, headers=mh)
print('reject:', r.get_json()['message'])

r = c.get(f'/api/customer/{cid}', headers=h)
print('rejected status:', r.get_json()['data']['status'])

# withdraw path
r = c.post('/api/customer/draft', json={'customer_name': '测试客户E', 'customer_type': 'PERSONAL', 'customer_level': 'NORMAL'}, headers=h)
cid2 = r.get_json()['data']['id']
c.post(f'/api/customer/{cid2}/submit', headers=h)
r = c.post(f'/api/customer/{cid2}/withdraw', headers=h)
print('withdraw:', r.get_json()['message'], r.get_json()['data']['status'])

# system management smoke
r = c.get('/api/users', headers=h)
print('users total:', r.get_json()['data']['total'])
r = c.get('/api/roles', headers=h)
print('roles total:', r.get_json()['data']['total'])
r = c.get('/api/permissions', headers=h)
print('perms total:', r.get_json()['data']['total'])
r = c.get('/api/resources/tree', headers=h)
print('resource roots:', [x['name'] for x in r.get_json()['data']])
r = c.get('/api/flow/definitions', headers=h)
print('flow defs:', [(x['code'], x['status']) for x in r.get_json()['data']['list']])
r = c.get('/api/flow/instances', headers=h)
print('instances total:', r.get_json()['data']['total'])
