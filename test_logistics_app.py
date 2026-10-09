from pathlib import Path
from streamlit.testing.v1 import AppTest
at=AppTest.from_file(str(Path(__file__).parent/'relaypoint_app.py'));at.run(timeout=30)
assert not at.exception,at.exception
next(b for b in at.button if b.label=='Operating briefing').click().run(timeout=30)
assert not at.exception,at.exception
assert any('20 active shipments' in m.value for m in at.markdown)
next(s for s in at.selectbox if s.label=='Shipment to allocate').select('RLY-0038')
next(s for s in at.selectbox if s.label=='Proposed vehicle').select('VEH-01')
next(b for b in at.button if b.label=='Prepare allocation proposal').click().run(timeout=30)
assert not at.exception,at.exception
next(b for b in at.button if b.label=='Confirm simulated allocation').click().run(timeout=30)
assert at.error and at.session_state['relay_state']['revision']==0
next(c for c in at.checkbox if 'I reviewed' in c.label).check()
next(b for b in at.button if b.label=='Confirm simulated allocation').click().run(timeout=30)
assert not at.exception,at.exception
assert at.session_state['relay_state']['revision']==1
assert any('No external dispatch occurred' in s.value for s in at.success)
next(s for s in at.selectbox if s.label=='Demo role').select('customer_service').run(timeout=30)
assert not at.exception,at.exception
assert not at.session_state['relay_messages']
assert not any(b.label=='Prepare allocation proposal' for b in at.button)
print('PASS: standalone logistics app loads, scenario answers, confirmation guard, allocation, updated state and role isolation')
