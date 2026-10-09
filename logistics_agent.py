"""Tool-grounded logistics AI; write commits are deliberately absent from the model tools."""
import os
from logistics_tools import scenario_answer

def ask(tools,message,api_key='',live=False,history=None):
 if not live:return scenario_answer(tools,message)
 if not api_key:raise ValueError('Live AI unavailable. Choose Scenario mode.')
 from google import genai
 from google.genai import types
 trace=[]
 def run(name,**args):
  try:result=getattr(tools,name)(**args)
  except (ValueError,KeyError,PermissionError) as exc:result=dict(error=str(exc))
  trace.append(dict(tool=name,result=result));return result
 def get_operations_briefing()->dict:
  """Retrieve reconciled delivery, delay and proof-of-delivery metrics at the fixed clock."""
  return run('get_operations_briefing')
 def list_delivery_exceptions(kind:str='All')->dict:
  """List exception records. kind must be All, Overdue, At risk, Missing POD or Awaiting dispatch."""
  return run('list_delivery_exceptions',kind=kind)
 def track_shipment(shipment_id:str)->dict:
  """Read a shipment by RLY-0000 ID and its recorded exception flags."""
  return run('track_shipment',shipment_id=shipment_id)
 def get_dispatch_capacity()->dict:
  """Inspect vehicle lanes, maintenance status and remaining weight. Dispatch roles only."""
  return run('get_dispatch_capacity')
 def propose_dispatch_assignment(shipment_id:str,vehicle_id:str)->dict:
  """Validate allocation without changing data. Return proposal for human review in Action Lab."""
  return run('propose_dispatch_assignment',shipment_id=shipment_id,vehicle_id=vehicle_id)
 def draft_customer_update(shipment_id:str)->dict:
  """Prepare a factual customer update draft. Never sends messages or guarantees arrival."""
  return run('draft_customer_update',shipment_id=shipment_id)
 prompt=f'''You are RelayPoint AI for a fictional logistics company. Role: {tools.role}. Business clock: {tools.state['as_of']} (Africa/Lagos). Always call relevant tools before making claims about shipment records, figures or capacity. Quote record IDs and actual tool evidence. Do not invent traffic, GPS, root causes or arrival forecasts. Recorded ETA is an estimate. On-time performance is delivered-only. Report tool errors and permissions; never bypass them. You can propose assignments but cannot commit them. Direct the user to the human-confirmed Action Lab. Drafting never sends a message. Never claim dispatch, delivery or sending occurred without an action result. Recommendations are proposed next steps. Use concise business language.'''
 context='\n'.join(f"{m['role']}: {m['content']}" for m in (history or [])[-6:])
 client=genai.Client(api_key=api_key,http_options=types.HttpOptions(timeout=45000))
 response=client.models.generate_content(model=os.getenv('GEMINI_MODEL','gemini-3.5-flash-lite'),contents=(context+'\nUser: '+message).strip(),config=types.GenerateContentConfig(system_instruction=prompt,temperature=0.1,tools=[get_operations_briefing,list_delivery_exceptions,track_shipment,get_dispatch_capacity,propose_dispatch_assignment,draft_customer_update],automatic_function_calling=types.AutomaticFunctionCallingConfig(maximum_remote_calls=6)))
 return dict(text=response.text or 'No answer returned. Please try a focused operating question.',mode='live-ai',trace=trace)
