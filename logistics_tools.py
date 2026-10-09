"""RelayPoint demo tools. All data and mutations stay in a fictional session."""
import copy,re
from datetime import datetime
ROLES={'manager','dispatch','customer_service'}
ACTIVE={'In transit','Awaiting dispatch','Assigned'}
class LogisticsTools:
 def __init__(self,state,role='manager'):
  if role not in ROLES:raise PermissionError('Unknown demo role')
  self.state=state;self.role=role;self.clock=datetime.fromisoformat(state['as_of'])
 def _dispatch(self):
  if self.role not in {'manager','dispatch'}:raise PermissionError('Dispatch tools require an operations manager or dispatch role')
 def _record(self,shipment_id):
  rows=[s for s in self.state['shipments'] if s['shipment_id']==shipment_id.upper()]
  if not rows:raise KeyError('Shipment not found')
  return rows[0]
 def _public(self,s):
  row=copy.deepcopy(s)
  if self.role!='manager':
   for key in ['declared_value_ngn','delivery_fee_ngn']:row.pop(key,None)
  return row
 def flags(self,s):
  out=[]
  if s['status'] in ACTIVE:
   promise=datetime.fromisoformat(s['promised_at'])
   if promise<self.clock:out.append('Overdue')
   elif s.get('recorded_eta') and datetime.fromisoformat(s['recorded_eta'])>promise:out.append('At risk')
   if s['status']=='Awaiting dispatch':out.append('Awaiting dispatch')
  if s['status']=='Delivered' and not s.get('pod_reference'):out.append('Missing POD')
  return out
 def get_operations_briefing(self):
  """Return reconciled metrics at the fixed business clock, with denominator definitions."""
  rows=self.state['shipments'];delivered=[s for s in rows if s['status']=='Delivered'];ontime=sum(datetime.fromisoformat(s['delivered_at'])<=datetime.fromisoformat(s['promised_at']) for s in delivered)
  result=dict(as_of=self.state['as_of'],total_shipments=len(rows),active=sum(s['status'] in ACTIVE for s in rows),delivered=len(delivered),cancelled=sum(s['status']=='Cancelled' for s in rows),overdue=sum('Overdue' in self.flags(s) for s in rows),at_risk=sum('At risk' in self.flags(s) for s in rows),missing_pod=sum('Missing POD' in self.flags(s) for s in rows),awaiting_dispatch=sum(s['status']=='Awaiting dispatch' for s in rows),on_time_delivered=ontime,on_time_rate=round(100*ontime/len(delivered),1) if delivered else None,definition='On-time rate uses delivered shipments only; cancelled and active shipments are excluded. At-risk ETA is recorded, not an AI forecast.')
  return result
 def list_delivery_exceptions(self,kind='All'):
  """List Overdue, At risk, Missing POD, Awaiting dispatch or All exception records."""
  if kind not in {'All','Overdue','At risk','Missing POD','Awaiting dispatch'}:raise ValueError('Unknown exception category')
  rows=[]
  for s in self.state['shipments']:
   flags=self.flags(s)
   if flags and (kind=='All' or kind in flags):rows.append(dict(**self._public(s),flags=flags))
  return dict(kind=kind,count=len(rows),records=rows,as_of=self.state['as_of'])
 def track_shipment(self,shipment_id):
  """Retrieve one shipment by its RLY-0000 ID. No live GPS is available."""
  s=self._record(shipment_id);return dict(record=self._public(s),flags=self.flags(s),as_of=self.state['as_of'],note='Recorded status and ETA; no GPS tracking or guaranteed arrival time.')
 def get_dispatch_capacity(self):
  """Inspect route compatibility, available weight and vehicle maintenance status."""
  self._dispatch();rows=[]
  for v in self.state['vehicles']:
   allocated=sum(s['weight_kg'] for s in self.state['shipments'] if s.get('vehicle_id')==v['vehicle_id'] and s['status'] in ACTIVE)
   rows.append(dict(**copy.deepcopy(v),allocated_kg=allocated,remaining_kg=max(0,v['capacity_kg']-allocated)))
  return dict(vehicles=rows,revision=self.state['revision'],note='Weight and lane checks only. No traffic, route optimisation, driver-hours or volume model.')
 def propose_dispatch_assignment(self,shipment_id,vehicle_id):
  """Validate a proposed allocation without changing records. Human confirmation is required."""
  self._dispatch();s=self._record(shipment_id)
  if s['status']!='Awaiting dispatch':raise ValueError('Only shipments awaiting dispatch can be assigned')
  candidates=self.get_dispatch_capacity()['vehicles'];v=next((x for x in candidates if x['vehicle_id']==vehicle_id),None)
  if not v:raise KeyError('Vehicle not found')
  if v['status'] not in {'Available','On route'}:raise ValueError('Vehicle is unavailable or in maintenance')
  if s['lane'] not in v['lanes']:raise ValueError('Vehicle is not compatible with this lane')
  if s['weight_kg']>v['remaining_kg']:raise ValueError('Remaining vehicle capacity is insufficient')
  return dict(shipment_id=s['shipment_id'],vehicle_id=vehicle_id,weight_kg=s['weight_kg'],lane=s['lane'],remaining_after_kg=v['remaining_kg']-s['weight_kg'],expected_revision=self.state['revision'],status='Proposal only — no records changed')
 def commit_assignment(self,proposal,confirmed=False):
  self._dispatch()
  if confirmed is not True:raise ValueError('Explicit human confirmation is required')
  if proposal.get('expected_revision')!=self.state['revision']:raise ValueError('Proposal is stale. Prepare it again against the current session.')
  current=self.propose_dispatch_assignment(proposal['shipment_id'],proposal['vehicle_id'])
  s=self._record(current['shipment_id']);before=self._public(s);s['vehicle_id']=current['vehicle_id'];s['status']='Assigned';self.state['revision']+=1
  action=dict(action_id=f"ACT-{len(self.state['actions'])+1:04d}",action='Simulated vehicle assignment',actor_role=self.role,as_of=self.state['as_of'],revision=self.state['revision'],before=before,after=self._public(s),external_dispatch=False)
  self.state['actions'].append(action);return copy.deepcopy(action)
 def get_audit_log(self):
  rows=copy.deepcopy(self.state['actions'])
  for row in rows:
   row['before']=self._public(row['before']);row['after']=self._public(row['after'])
  return rows
 def draft_customer_update(self,shipment_id):
  """Prepare a factual draft; do not send or promise a new arrival time."""
  s=self._record(shipment_id);flags=self.flags(s)
  text=f"Update for {s['shipment_id']}: the recorded status is {s['status']}. "
  if 'Overdue' in flags:text+='The delivery promise has passed. Our operations team needs to review the case and confirm the next update. '
  elif 'At risk' in flags:text+='The recorded ETA is later than the delivery promise. This estimate needs review; it is not a guaranteed arrival time. '
  elif s['status']=='Delivered':text+='Delivery is recorded'+(' and proof of delivery is available. ' if s.get('pod_reference') else '; proof of delivery is still pending. ')
  else:text+='The operations team can confirm the next handling step. '
  return dict(shipment_id=s['shipment_id'],draft=text.strip(),status='Draft only',sent=False,as_of=self.state['as_of'])

def scenario_answer(tools,message):
 q=message.lower();match=re.search(r'rly-\d{4}',q)
 if match and any(t in q for t in ['draft','update','message']):name='draft_customer_update';data=tools.draft_customer_update(match.group());text=data['draft']
 elif match:name='track_shipment';data=tools.track_shipment(match.group());s=data['record'];text=f"{s['shipment_id']} is {s['status']} on {s['origin']} → {s['destination']}. Flags: {', '.join(data['flags']) or 'None'}. {s['exception_note']}"
 elif 'capacity' in q or 'vehicle' in q:name='get_dispatch_capacity';data=tools.get_dispatch_capacity();text='Fleet capacity snapshot: '+', '.join(f"{v['vehicle_id']} · {v['remaining_kg']} kg remaining · {v['status']}" for v in data['vehicles'])+'. Check lane compatibility before preparing an allocation.'
 elif any(w in q for w in ['overdue','at risk','pod','exception','dispatch queue']):
  kind='Missing POD' if 'pod' in q else 'At risk' if 'at risk' in q else 'Overdue' if 'overdue' in q else 'Awaiting dispatch' if 'dispatch queue' in q else 'All';name='list_delivery_exceptions';data=tools.list_delivery_exceptions(kind);text=f"{data['count']} shipments match {kind}: "+', '.join(s['shipment_id'] for s in data['records'])+'. Review the recorded cause and assign the next handling step.'
 elif any(w in q for w in ['brief','attention','priority','priorities','overview']):
  name='get_operations_briefing';data=tools.get_operations_briefing();text=f"{data['active']} active shipments: {data['overdue']} overdue and {data['at_risk']} at risk. {data['awaiting_dispatch']} await dispatch; {data['missing_pod']} delivered shipments lack proof of delivery. Delivered-only on-time performance is {data['on_time_rate']}% ({data['on_time_delivered']}/{data['delivered']})."
 else:return dict(text='Scenario mode supports the example questions, shipment IDs, exception queues, dispatch capacity and customer drafts. Use Live AI for broader natural-language questions.',mode='scenario',trace=[])
 return dict(text=text,mode='scenario',trace=[dict(tool=name,result=data)])
