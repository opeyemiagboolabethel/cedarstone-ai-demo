"""RelayPoint logistics demonstration with a dedicated deployment entry point."""
import copy,json,os
from pathlib import Path
import pandas as pd
import streamlit as st
from logistics_tools import LogisticsTools
from logistics_agent import ask
HERE=Path(__file__).resolve().parent
EXAMPLES={'Operating briefing':'What needs management attention?','Overdue deliveries':'Show overdue delivery exceptions','At-risk deliveries':'Show deliveries at risk','Missing POD':'Show missing POD','Dispatch capacity':'Show dispatch capacity','Customer update':'Draft a customer update for RLY-0025'}
ROLES={'manager':'Operations manager','dispatch':'Dispatch coordinator','customer_service':'Customer service'}

def render():
 st.set_page_config(page_title='RelayPoint AI | ONE Light Analytics',page_icon='🚚',layout='wide')
 st.markdown('''<style>.stApp{background:#f7f5ef;color:#071522}.relay-hero{background:linear-gradient(110deg,#071522,#173a50);padding:30px;border-radius:16px;color:white;margin-bottom:25px}.relay-hero h1{color:white;margin:10px 0;font-size:2.7rem}.relay-hero p{color:#d2dce3;max-width:820px}.relay-kicker{color:#e4bc78;font-size:11px;text-transform:uppercase;letter-spacing:.15em}[data-testid="stMetric"]{padding:20px;background:white;border:1px solid #d6dadd;border-radius:10px}[data-testid="stMetricValue"]{color:#071522}.stButton button{border-color:#b38842;min-height:44px}.stButton button p{color:#071522}button[role="tab"][aria-selected="true"]{color:#825918}.block-container{padding-top:2rem;padding-bottom:3rem}</style>''',unsafe_allow_html=True)
 if 'relay_state' not in st.session_state:st.session_state.relay_state=json.loads((HERE/'logistics_data/operations.json').read_text())
 with st.sidebar:
  st.subheader('RelayPoint AI');st.caption('Logistics operating demonstration')
  st.link_button('ONE Light Analytics case page','https://onelightanalytics.com/pages/case-logistics-ai')
  role=st.selectbox('Demo role',list(ROLES),format_func=ROLES.get,key='relay_role')
  key=os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY') or ''
  if not key:
   try:key=st.secrets.get('GEMINI_API_KEY','') or st.secrets.get('GOOGLE_API_KEY','')
   except Exception:key=''
  modes=['Scenario mode']+(['Live AI'] if key else [])
  mode=st.radio('Agent mode',modes,index=len(modes)-1,key='relay_mode')
  st.caption('Scenario mode uses deterministic database tools. Live AI chooses approved tools. Neither can execute external business transactions.')
  if st.button('Reset logistics session'):
   for k in ['relay_state','relay_messages','relay_pending','relay_proposal']:st.session_state.pop(k,None)
   st.rerun()
  st.caption('Fictional records · 9 Oct 2026, 09:00 WAT. Each session has its own state. Demo role switching is not production authentication.')
 context=(role,mode)
 if st.session_state.get('relay_context')!=context:
  st.session_state.relay_messages=[];st.session_state.pop('relay_pending',None);st.session_state.pop('relay_proposal',None);st.session_state.relay_context=context
 tools=LogisticsTools(st.session_state.relay_state,role);m=tools.get_operations_briefing()
 if st.session_state.get('relay_flash'):st.success(st.session_state.pop('relay_flash'))
 st.markdown('''<div class="relay-hero"><div class="relay-kicker">ONE Light Analytics · Sector AI 02 / Logistics</div><h1>RelayPoint AI</h1><p>See the delivery risk. Inspect the shipment. Coordinate the next step.</p><p>Fictional Lagos-based operation · recorded ETAs · human-confirmed simulated allocations</p></div>''',unsafe_allow_html=True)
 with st.expander('Start here · a three-minute logistics walkthrough'):
  st.markdown('**1. Read the operating picture.** Compare overdue and at-risk deliveries with missing proof of delivery.\n\n**2. Ask the agent.** Try a scenario or track RLY-0025; inspect the returned tool evidence.\n\n**3. Coordinate dispatch.** Prepare an allocation for RLY-0038 and VEH-01, review it and explicitly confirm. Inspect Audit Log afterwards. No vehicle is dispatched outside this sandbox.')
 tabs=st.tabs(['Operating overview','AI Agent','Shipment desk','Action Lab','Audit Log'])
 with tabs[0]:
  st.subheader('What needs attention now')
  for row,values in [(st.columns(3),[('Active shipments',m['active']),('Overdue deliveries',m['overdue']),('At-risk deliveries',m['at_risk'])]),(st.columns(3),[('Delivered-only on-time',f"{m['on_time_rate']}%"),('Missing POD',m['missing_pod']),('Awaiting dispatch',m['awaiting_dispatch'])])]:
   for col,(label,value) in zip(row,values):col.metric(label,value)
  st.caption(f"{m['total_shipments']} records reconcile to {m['active']} active + {m['delivered']} delivered + {m['cancelled']} cancelled. On-time rate = {m['on_time_delivered']} / {m['delivered']} delivered shipments. ETA risk is a recorded schedule comparison, not a predictive model.")
  a,b=st.columns(2)
  a.info('Delivery recovery: inspect the eight overdue records, confirm the handling issue and choose an owner. The source note is not an independently verified root cause.')
  b.info('Service closure: request the four missing proof-of-delivery records before treating delivery documentation as complete.')
  if role in {'manager','dispatch'}:st.dataframe(pd.DataFrame(tools.get_dispatch_capacity()['vehicles']),hide_index=True,width='stretch')
 with tabs[1]:
  left,right=st.columns([1.6,1])
  with left:
   st.subheader('Ask RelayPoint AI')
   st.caption('Live AI uses approved read/proposal tools. Committing an assignment requires the reviewed Action Lab.')
   for msg in st.session_state.relay_messages[-12:]:
    with st.chat_message(msg['role']):
     st.markdown(msg['content'])
     if msg.get('trace'):
      with st.expander('Inspect tool evidence'):st.json(msg['trace'])
   prompt=st.chat_input('Ask about deliveries, shipment IDs or dispatch capacity',key='relay_chat')
   if st.session_state.get('relay_pending'):prompt=st.session_state.pop('relay_pending')
   if prompt:
    prior=copy.deepcopy(st.session_state.relay_messages);st.session_state.relay_messages.append(dict(role='user',content=prompt))
    with st.chat_message('user'):st.markdown(prompt)
    with st.chat_message('assistant'):
     try:
      with st.spinner('Checking the operating records…'):result=ask(tools,prompt,key,mode=='Live AI',prior)
      st.markdown(result['text']);st.caption(f"Mode: {result['mode']} · Role: {ROLES[role]}")
      with st.expander('Inspect tool evidence'):st.json(result['trace'])
      st.session_state.relay_messages.append(dict(role='assistant',content=result['text'],trace=result['trace']))
     except Exception:
      st.error('This request could not complete. Try Scenario mode or a focused shipment question. No dispatch action was executed.')
  with right:
   st.subheader('Operating questions')
   for label,prompt in EXAMPLES.items():
    if st.button(label,key='relay_example_'+label,width='stretch'):st.session_state.relay_pending=prompt;st.rerun()
 with tabs[2]:
  st.subheader('Shipment evidence desk')
  kind=st.selectbox('Exception queue',['All','Overdue','At risk','Missing POD','Awaiting dispatch'])
  records=tools.list_delivery_exceptions(kind)['records'] if kind!='All' else [tools.track_shipment(s['shipment_id'])['record'] for s in tools.state['shipments']]
  frame=pd.DataFrame(records);st.caption(f'{len(records)} records in this view. Headline metrics above remain the full session cohort.')
  st.dataframe(frame,hide_index=True,width='stretch')
  st.download_button('Download selected shipment records',frame.to_csv(index=False),'relaypoint-shipments.csv','text/csv')
 with tabs[3]:
  st.subheader('Prepare. Review. Confirm.')
  st.caption('Assignments change only this private fictional session. Customer messages are drafts and are never sent.')
  if role in {'manager','dispatch'}:
   awaiting=[s['shipment_id'] for s in tools.state['shipments'] if s['status']=='Awaiting dispatch']
   if awaiting:
    with st.form('relay_prepare'):
     shipment=st.selectbox('Shipment to allocate',awaiting);vehicle=st.selectbox('Proposed vehicle',[v['vehicle_id'] for v in tools.state['vehicles']]);prepare=st.form_submit_button('Prepare allocation proposal')
    if prepare:
     st.session_state.pop('relay_proposal',None)
     try:st.session_state.relay_proposal=tools.propose_dispatch_assignment(shipment,vehicle)
     except (ValueError,KeyError,PermissionError) as exc:st.error(str(exc))
   proposal=st.session_state.get('relay_proposal')
   if proposal:
    st.json(proposal)
    with st.form('relay_confirm'):
     confirmed=st.checkbox('I reviewed the shipment, lane and remaining capacity; confirm this simulated allocation.')
     commit=st.form_submit_button('Confirm simulated allocation')
    if commit:
     try:
      action=tools.commit_assignment(proposal,confirmed);st.session_state.relay_flash=f"{action['action_id']}: {proposal['shipment_id']} assigned to {proposal['vehicle_id']} in this session. No external dispatch occurred.";st.session_state.pop('relay_proposal',None);st.rerun()
     except (ValueError,KeyError,PermissionError) as exc:st.error(str(exc))
  else:st.info('Customer service can draft updates. Vehicle allocation requires a dispatch or operations-manager role.')
  target=st.selectbox('Shipment for customer update',[s['shipment_id'] for s in tools.state['shipments']],index=24)
  if st.button('Prepare customer update draft'):
   draft=tools.draft_customer_update(target);st.text_area('Draft only — not sent',draft['draft'],height=130);st.caption('No email, WhatsApp or SMS delivery integration is enabled.')
 with tabs[4]:
  st.subheader('Session audit trail')
  if tools.state['actions']:st.json(tools.get_audit_log())
  else:st.info('No simulated allocations have been committed in this session.')
  st.download_button('Download session audit',json.dumps(tools.get_audit_log(),indent=2),'relaypoint-audit.json','application/json')
 st.caption('RelayPoint Logistics is fictional. These are demonstration operating records, not client results, live GPS or a production dispatch system.')
