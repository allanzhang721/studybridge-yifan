import pytest
from pathlib import Path
from streamlit.testing.v1 import AppTest
from studybridge.current_ui import validate_paper

APP = Path(__file__).resolve().parents[1] / 'app.py'

def test_paper_rejects_wrong_marks_and_repeats():
    paper={'questions':[{'prompt':'Question A','marks':5},{'prompt':'Question B','marks':5},{'prompt':'Question C','marks':5}]}
    validate_paper(paper,3,15,[])
    with pytest.raises(ValueError): validate_paper(paper,3,20,[])
    with pytest.raises(ValueError): validate_paper(paper,3,15,['question a'])

def test_overview_and_key_gate(tmp_path,monkeypatch):
    monkeypatch.setenv('STUDYBRIDGE_DB_PATH',str(tmp_path/'workspace.sqlite'))
    monkeypatch.delenv('OPENAI_API_KEY',raising=False)
    app=AppTest.from_file(str(APP),default_timeout=30).run()
    assert not app.exception
    app.button(key='nav_Worksheet images').click().run()
    assert not app.exception
    assert any(x.value=='Enter your API key' for x in app.subheader)
    app.button(key='nav_Impact ledger').click().run()
    assert not app.exception
    assert len(app.tabs)==3

def test_empty_course_and_exam_pages(tmp_path,monkeypatch):
    monkeypatch.setenv('STUDYBRIDGE_DB_PATH',str(tmp_path/'workspace.sqlite'))
    app=AppTest.from_file(str(APP),default_timeout=30).run()
    app.button(key='nav_My courses').click().run()
    assert not app.exception

def test_ai_paper_uses_course_and_saves_review(tmp_path,monkeypatch):
    from studybridge import ai
    monkeypatch.setenv('STUDYBRIDGE_DB_PATH',str(tmp_path/'workspace.sqlite'))
    monkeypatch.setattr(ai,'configuration',lambda: ('test-key','test-model'))
    calls=[]
    def request(schema,instructions,payload,images=None):
        calls.append(payload)
        return {'title':'Practice paper','instructions':'Attempt every question','questions':[{'prompt':f'Solve x + {i} = 8','topic':'Equations','marks':6,'answer':str(8-i),'steps':['Subtract the constant.']} for i in range(5)]}
    monkeypatch.setattr(ai,'request',request)
    app=AppTest.from_file(str(APP),default_timeout=30).run()
    next(b for b in app.button if b.label=='Load sample course').click().run()
    assert not app.exception
    app.button(key='nav_Mock exams').click().run()
    next(x for x in app.text_area if x.label=='Exam requirements').set_value('Foundation equations')
    next(b for b in app.button if b.label=='Generate AI mock').click().run()
    assert not app.exception
    assert len(calls)==2 and calls[0]['materials']
    assert len(app.session_state['workspace']['ai_papers'])==1
    next(b for b in app.button if b.label=='Add to mistake board').click().run()
    assert not app.exception
    assert app.session_state['workspace']['courses'][0]['review_board']
    app.button(key='nav_Mock exams').click().run()
    assert not app.exception
