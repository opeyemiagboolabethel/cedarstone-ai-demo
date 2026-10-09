from pathlib import Path
import tempfile,shutil,sqlite3
from streamlit.testing.v1 import AppTest
from cedarstone_tools import CedarStoneTools,ToolContext
from offline_agent import OfflineDemoAgent
HERE=Path(__file__).parent
with tempfile.TemporaryDirectory() as d:
 p=Path(d)/'cases.db';shutil.copy2(HERE/'CedarStone_AI_Agent_Demo.db',p)
 tools=CedarStoneTools(p,ToolContext(employee_id='EMP-001',role='executive'))
 unit=sqlite3.connect(p).execute("SELECT unit_id FROM units WHERE property_id='PROP-001' LIMIT 1").fetchone()[0]
 fresh=tools.create_maintenance_ticket('PROP-001',unit,'Electrical','New critical test case','Critical')
 answer=OfflineDemoAgent(tools).ask('Show critical maintenance issues open for more than 48 hours')
 assert fresh['ticket_id'] not in [r['ticket_id'] for r in answer['data']]
 assert len(answer['data'])==3
at=AppTest.from_file(str(HERE/'streamlit_app.py')).run(timeout=30)
assert not at.exception,at.exception
at.button(key='scenario_SCN-001').click().run(timeout=30) if any(b.key=='scenario_SCN-001' for b in at.button) else next(b for b in at.button if b.label=='CEO Morning Briefing').click().run(timeout=30)
assert not at.exception,at.exception
assert any('1,929,562,159' in m.value for m in at.markdown)
next(s for s in at.selectbox if s.label=='Demo role').select('sales').run(timeout=30)
assert not at.exception,at.exception
assert not any('Management attention is required across six areas' in m.value for m in at.markdown)
assert len(at.session_state['messages'])==1
print('PASS: fresh critical tickets excluded from 48h queue; app loads, answers a scenario and clears transcript on role switch')
