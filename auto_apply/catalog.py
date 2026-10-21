"""Local renderings of the same simulated forms offered by the React site."""
import html
import json
from pathlib import Path

CATALOG = Path(__file__).resolve().parents[1] / 'fixtures/applications.json'


def applications():
    return json.loads(CATALOG.read_text(encoding='utf-8'))


def render_application(application_id):
    app = next((a for a in applications() if a['id'] == application_id), None)
    if app is None:
        raise ValueError(f'Unknown application: {application_id}')
    esc = lambda value: html.escape(str(value), quote=True)
    sections = {}
    for field in app['fields']:
        attrs = f'id="{esc(field["id"])}" name="{esc(field["id"])}"' + (' required' if field.get('required') else '')
        kind = field.get('type', 'text')
        if kind == 'textarea':
            control = f'<textarea {attrs}></textarea>'
        elif kind == 'select':
            control = f'<select {attrs}>' + ''.join(f'<option value="{esc(o)}">{esc(o or "Select an answer")}</option>' for o in field['options']) + '</select>'
        else:
            control = f'<input {attrs} type="{esc(kind)}">'
        sections.setdefault(field['section'], []).append(f'<label>{esc(field["label"])}{control}</label>')
    sections['Resume'] = ['<label>Resume<input id="resume" name="resume" type="file" accept=".txt,.pdf,.docx" required></label>']
    multipage = app['platform'] == 'Workday' or (app['platform'] == 'Other' and app['variant'] == 5)
    body = ''.join(f'<section class="step" data-step="{i}" {"hidden" if multipage and i else ""}><h2>{esc(name)}</h2>{"".join(controls)}</section>' for i, (name, controls) in enumerate(sections.items()))
    colors = {'Workday':'#285b87','Greenhouse':'#386446','Lever':'#805f3f','Other':'#6b5084'}
    script = ''
    if multipage:
        script = """<script>
        let step=0; const steps=[...document.querySelectorAll('.step')];
        function show(){steps.forEach((s,i)=>s.hidden=i!==step);document.querySelector('#next-step').hidden=step===steps.length-1;document.querySelector('#previous-step').hidden=step===0;document.querySelector('#submit').hidden=step!==steps.length-1;document.querySelector('#progress').textContent=`Step ${step+1} of ${steps.length}`;window.scrollTo(0,0)}
        document.querySelector('#next-step').onclick=()=>{step++;show()};
        document.querySelector('#previous-step').onclick=()=>{step--;show()};show();
        </script>"""
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><title>{esc(app['company'])} · {esc(app['title'])}</title>
    <style>body{{font:15px system-ui;background:#f3f5f2;color:#293b2c;margin:35px auto;max-width:850px}}main{{padding:32px;background:white;border-radius:12px}}h1{{margin:10px 0}}small{{color:{colors[app['platform']]}}}label{{display:flex;flex-direction:column;gap:7px;margin:18px 0}}input,select,textarea,button{{font:inherit;padding:11px;border:1px solid #b8c7b2;border-radius:5px}}textarea{{min-height:70px}}button{{background:{colors[app['platform']]};color:white;cursor:pointer;margin:15px 8px 0 0}}.banner{{padding:13px;background:#f1f4e9;margin:20px 0}}[hidden]{{display:none!important}}</style></head>
    <body><main><small>{esc(app['company'])} · {esc(app['platform'])} STYLE SIMULATION</small><h1>{esc(app['title'])}</h1><p>{esc(app['location'])}</p><div class="banner">Fictional application. Stored answers only; unknown answers stay empty. No submission without terminal approval.</div><p id="progress"></p>
    <form method="post" action="/submit" enctype="multipart/form-data">{body}
    <button type="button" id="previous-step" hidden>Previous</button><button type="button" id="next-step" {'' if multipage else 'hidden'}>Continue</button><button id="submit" type="submit">Submit simulated application</button></form></main>{script}</body></html>'''
