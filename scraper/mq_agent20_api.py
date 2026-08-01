"""mq-agent-20 section A: user-service + chat-service API scrape."""
import sys, time, json

sys.path.insert(0, 'scraper')
from mq_db import start_run, finish_run, save_response, save_endpoint
from mq_api import get, path_of

AGENT = 'mq-agent-20'
UNIT = 'user-chat-account'

run_id = start_run(AGENT, UNIT)
print('run_id =', run_id)

stats = {'calls': 0, 'ok': 0}
results = {}

def call(service, path, template, params=''):
    stats['calls'] += 1
    status, data = get(service, path)
    url = path_of(service, path)
    save_response(run_id, service, url, status, data)
    save_endpoint(service, template, example_url=url, params=params,
                  status=status, discovered_via='agent-scrape')
    if 200 <= status < 300:
        stats['ok'] += 1
    print(f'[{status}] {service}{path}  bytes={len(json.dumps(data, ensure_ascii=False))}')
    time.sleep(0.4)
    return status, data

# --- user-service ---
st, me = call('user-service', '/api/web/v1/users/me', '/api/web/v1/users/me')
results['users_me'] = (st, bool(me))
st, watchlists = call('user-service', '/api/web/v1/watchlists', '/api/web/v1/watchlists')
results['watchlists'] = (st, len(watchlists) if isinstance(watchlists, list) else None)
st, prefs = call('user-service', '/api/web/v1/user-preferences?type=tradingview',
                 '/api/web/v1/user-preferences', params='type=tradingview')
results['prefs'] = (st, bool(prefs))

# --- chat-service ---
st, ctx = call('chat-service', '/api/web/v1/chat-context', '/api/web/v1/chat-context')
results['chat_context'] = (st, bool(ctx))
st, chats = call('chat-service', '/api/web/v1/chats', '/api/web/v1/chats')
nchats = None
if isinstance(chats, list):
    nchats = len(chats)
elif isinstance(chats, dict):
    for k in ('chats', 'items', 'data', 'results'):
        if isinstance(chats.get(k), list):
            nchats = len(chats[k]); break
results['chats'] = (st, nchats)

st, stmps = call('chat-service', '/api/web/v1/screener-templates', '/api/web/v1/screener-templates')
results['screener_templates'] = (st, len(stmps) if isinstance(stmps, list) else None)

st, tmps = call('chat-service', '/api/web/v1/templates?type=suggested',
                '/api/web/v1/templates', params='type=suggested')
results['templates_suggested'] = (st, len(tmps) if isinstance(tmps, list) else None)

# --- screener-template details (max 6) ---
ids = []
items = stmps if isinstance(stmps, list) else []
if isinstance(stmps, dict):
    for k in ('templates', 'items', 'data', 'results'):
        if isinstance(stmps.get(k), list):
            items = stmps[k]; break
for it in items:
    if isinstance(it, dict):
        tid = it.get('id') or it.get('templateId') or it.get('uuid')
        if tid:
            ids.append(str(tid))
for tid in ids[:6]:
    call('chat-service', f'/api/web/v1/screener-templates/{tid}',
         '/api/web/v1/screener-templates/{id}')

print('RESULTS_META', json.dumps(results))
status = 'ok' if stats['ok'] == stats['calls'] else ('partial' if stats['ok'] else 'blocked')
finish_run(run_id, status, f"calls={stats['calls']} ok={stats['ok']}")
print('FINISHED', status, stats)
