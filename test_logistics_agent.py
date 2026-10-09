import copy,json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from logistics_tools import LogisticsTools
from logistics_agent import ask
state=json.loads((Path(__file__).parent/'logistics_data/operations.json').read_text())
for role in ['manager','customer_service']:
 def generate(**kwargs):
  functions=kwargs['config'].tools
  # SDK preserves Python callables in the config supplied to the client.
  names=[fn.__name__ for fn in functions]
  assert 'commit_assignment' not in names and len(names)==6
  data=functions[0]();assert data['overdue']==8
  return SimpleNamespace(text='Eight overdue shipments require case review.')
 fake=SimpleNamespace(models=SimpleNamespace(generate_content=generate))
 with patch('google.genai.Client',return_value=fake):
  r=ask(LogisticsTools(copy.deepcopy(state),role),'What needs attention?','test-only-key',True)
  assert r['mode']=='live-ai' and r['trace'][0]['result']['overdue']==8
print('PASS: SDK tool registration, no AI commit tool and retained evidence trace')
