import copy,json,unittest
from pathlib import Path
from logistics_tools import LogisticsTools,scenario_answer
FIXTURE=json.loads((Path(__file__).parent/'logistics_data/operations.json').read_text())
class LogisticsTests(unittest.TestCase):
 def setUp(self):self.state=copy.deepcopy(FIXTURE);self.tools=LogisticsTools(self.state)
 def test_reconciliation(self):
  m=self.tools.get_operations_briefing();self.assertEqual((m['total_shipments'],m['active'],m['delivered'],m['cancelled']),(48,20,24,4));self.assertEqual((m['overdue'],m['at_risk'],m['missing_pod'],m['awaiting_dispatch']),(8,5,4,7));self.assertEqual(m['on_time_rate'],87.5)
 def test_queues_disjoint(self):
  a={s['shipment_id'] for s in self.tools.list_delivery_exceptions('Overdue')['records']};b={s['shipment_id'] for s in self.tools.list_delivery_exceptions('At risk')['records']};self.assertFalse(a&b)
 def test_cancelled_excluded(self):self.assertEqual(self.tools.track_shipment('RLY-0048')['flags'],[])
 def test_unknown_shipment(self):
  with self.assertRaises(KeyError):self.tools.track_shipment('RLY-9999')
 def test_invalid_queue(self):
  with self.assertRaises(ValueError):self.tools.list_delivery_exceptions('Predicted fraud')
 def test_role_valid(self):
  with self.assertRaises(PermissionError):LogisticsTools(self.state,'superuser')
 def test_redaction(self):
  for role in ['dispatch','customer_service']:
   t=LogisticsTools(self.state,role);self.assertNotIn('declared_value_ngn',t.track_shipment('RLY-0025')['record']);self.assertNotIn('delivery_fee_ngn',t.list_delivery_exceptions()['records'][0])
 def test_customer_capacity_denied(self):
  with self.assertRaises(PermissionError):LogisticsTools(self.state,'customer_service').get_dispatch_capacity()
 def test_customer_allocation_denied(self):
  with self.assertRaises(PermissionError):LogisticsTools(self.state,'customer_service').propose_dispatch_assignment('RLY-0038','VEH-01')
 def test_proposal_does_not_write(self):
  before=copy.deepcopy(self.state);self.tools.propose_dispatch_assignment('RLY-0038','VEH-01');self.assertEqual(before,self.state)
 def test_confirmation_required(self):
  p=self.tools.propose_dispatch_assignment('RLY-0038','VEH-01')
  with self.assertRaises(ValueError):self.tools.commit_assignment(p)
  self.assertEqual(self.state['revision'],0)
 def test_wrong_lane(self):
  with self.assertRaises(ValueError):self.tools.propose_dispatch_assignment('RLY-0039','VEH-01')
 def test_maintenance_vehicle(self):
  with self.assertRaises(ValueError):self.tools.propose_dispatch_assignment('RLY-0039','VEH-04')
 def test_delivered_cannot_allocate(self):
  with self.assertRaises(ValueError):self.tools.propose_dispatch_assignment('RLY-0001','VEH-01')
 def test_capacity_guard(self):
  self.state['vehicles'][0]['capacity_kg']=1
  with self.assertRaises(ValueError):self.tools.propose_dispatch_assignment('RLY-0038','VEH-01')
 def test_commit_audit_and_capacity(self):
  p=self.tools.propose_dispatch_assignment('RLY-0038','VEH-01');a=self.tools.commit_assignment(p,True);self.assertEqual(a['after']['status'],'Assigned');self.assertFalse(a['external_dispatch']);self.assertEqual(self.state['revision'],1);self.assertEqual(self.tools.get_operations_briefing()['awaiting_dispatch'],6);self.assertEqual(self.tools.get_dispatch_capacity()['vehicles'][0]['remaining_kg'],600-p['weight_kg'])
 def test_stale_proposal_rejected(self):
  a=self.tools.propose_dispatch_assignment('RLY-0038','VEH-01');b=self.tools.propose_dispatch_assignment('RLY-0039','VEH-03');self.tools.commit_assignment(a,True)
  with self.assertRaises(ValueError):self.tools.commit_assignment(b,True)
 def test_duplicate_commit_rejected(self):
  p=self.tools.propose_dispatch_assignment('RLY-0038','VEH-01');self.tools.commit_assignment(p,True)
  with self.assertRaises(ValueError):self.tools.commit_assignment(p,True)
 def test_draft_is_not_sent(self):self.assertFalse(self.tools.draft_customer_update('RLY-0025')['sent']);self.assertIn('promise has passed',self.tools.draft_customer_update('RLY-0025')['draft']);self.assertEqual(self.state['actions'],[])
 def test_missing_pod_not_arrival_claim(self):self.assertIn('proof of delivery is still pending',self.tools.draft_customer_update('RLY-0001')['draft'])
 def test_session_isolation(self):
  other=copy.deepcopy(FIXTURE);p=self.tools.propose_dispatch_assignment('RLY-0038','VEH-01');self.tools.commit_assignment(p,True);self.assertEqual(other['shipments'][37]['status'],'Awaiting dispatch')
 def test_scenario_evidence(self):
  for q in ['What needs attention?','Show overdue','Show at risk','Missing POD','Dispatch capacity','Draft update for RLY-0025','Track RLY-0025']:self.assertTrue(scenario_answer(self.tools,q)['trace'])
 def test_audit_redacts_after_role_switch(self):
  p=self.tools.propose_dispatch_assignment('RLY-0038','VEH-01');self.tools.commit_assignment(p,True);audit=LogisticsTools(self.state,'customer_service').get_audit_log();self.assertNotIn('declared_value_ngn',audit[0]['before']);self.assertNotIn('delivery_fee_ngn',audit[0]['after'])
 def test_exact_deadline_boundary(self):
  s=self.state['shipments'][24];s['promised_at']=self.state['as_of'];s['recorded_eta']=self.state['as_of'];self.assertNotIn('Overdue',self.tools.flags(s));self.assertNotIn('At risk',self.tools.flags(s))
 def test_empty_delivered_denominator(self):
  self.state['shipments']=[s for s in self.state['shipments'] if s['status']!='Delivered'];self.assertIsNone(self.tools.get_operations_briefing()['on_time_rate'])
if __name__=='__main__':unittest.main()
