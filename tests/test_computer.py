"""Computer-use protocol boundaries; these tests do not validate pretrained ability."""
import copy
import io
import json
from pathlib import Path

import pytest

from auto_apply.computer import approved_resumes, to_pixel_action, validate_action
from auto_apply.inference import EndpointModel, parse_actions
from auto_apply.profile import Profile

ROOT = Path(__file__).resolve().parents[1]


def validate(name, args):
    return validate_action({"name": name, "args": args}, width=1280, height=900,
                           facts={"personal.full_name": "Alex Example"}, resume_count=1)


def test_openwebrl_list_and_native_envelopes():
    output = '<thinking>Inspecting the form.</thinking><action>I will focus the name field.</action><tool_call>[{"name":"click","arguments":{"x":200,"y":150}}]</tool_call>'
    action = parse_actions(output)[0]
    assert validate_action(action, width=1280, height=900, facts={}, resume_count=0) == {
        "name": "click", "args": {"point_2d": [200, 150]},
    }
    assert parse_actions('{"name":"done","arguments":{"response":"Ready for review."}}')[0]["name"] == "done"


@pytest.mark.parametrize("name,args", [
    ("goto_url", {"url": "https://example.org"}),
    ("evaluate", {"code": "document.forms[0].submit()"}),
    ("write", {"message": "Invented salary: 200000"}),
    ("select_option", {"point_2d": [100, 100], "label": "Invented eligibility"}),
    ("press_keys", {"keys": ["Control", "l"]}),
    ("press_keys", {"keys": ["A"]}),
    ("press_keys", {"keys": ["Tab"], "presses": 100000}),
    ("click", {"point_2d": [-1, 0]}),
    ("click", {"point_2d": [float("nan"), 0]}),
    ("click", {"point_2d": [1280, 900]}),
    ("upload_resume", {"point_2d": [100, 100], "resume_index": -1}),
    ("upload_resume", {"point_2d": [100, 100], "resume_index": True}),
    ("scroll", {"direction": "down", "amount": float("inf")}),
    ("wait", {"seconds": 1000}),
    ("done", {"response": ""}),
])
def test_model_cannot_invent_facts_navigate_or_escape_bounds(name, args):
    with pytest.raises((ValueError, TypeError)):
        validate(name, args)


def test_exact_profile_facts_and_navigation_are_allowed():
    assert validate("write", {"message": "Alex Example"})["args"]["message"] == "Alex Example"
    assert validate("write", {"message": ""})["args"]["message"] == ""
    assert validate("press_keys", {"keys": ["ArrowDown", "Enter"]})["args"]["is_hotkey"] is False


def test_qwen_function_tags_and_coordinate_conversion():
    calls = parse_actions('<tool_call><function=click><parameter=point_2d>[375, 320]</parameter></function></tool_call>')
    point = to_pixel_action(calls[0], 1280, 900)['args']['point_2d']
    assert point == pytest.approx([479.625, 287.68])
    assert parse_actions('<tool_call><function=write><parameter=message>Alex Example</parameter></function></tool_call>')[0]['args']['message'] == 'Alex Example'
    with pytest.raises(ValueError):
        to_pixel_action({'name':'click','args':{'point_2d':[1001,0]}},1280,900)


def test_resume_paths_and_hashes_are_validated_before_model_runs(tmp_path):
    profile = Profile.load(ROOT / "profiles/dummy.json")
    assert approved_resumes(profile, ROOT / "profiles/dummy.json")[0].name == "dummy-resume.txt"
    bad = copy.deepcopy(profile)
    bad.resume_files[0].path = "../dummy.json"
    with pytest.raises(ValueError, match="inside"):
        approved_resumes(bad, tmp_path / "profile.json")
    (tmp_path / "resume.txt").write_text("modified")
    bad.resume_files[0].path = "resume.txt"
    with pytest.raises(ValueError, match="hash"):
        approved_resumes(bad, tmp_path / "profile.json")


def test_endpoint_sends_visual_tools_and_parses_native_tool_calls(monkeypatch):
    def respond(request, timeout):
        body = json.loads(request.data)
        assert body['messages'][0] == {'role': 'system', 'content': 'Use candidate facts.'}
        assert body['messages'][1]['content'][1]['image_url']['url'].startswith('data:image/png;base64,')
        tools = {tool['function']['name'] for tool in body['tools']}
        assert {'click', 'write', 'select_option', 'upload_resume'} <= tools
        assert not {'goto_url', 'new_tab', 'evaluate'} & tools
        assert body['max_tokens'] == 2048
        return io.BytesIO(json.dumps({'choices': [{'message': {'content': None, 'tool_calls': [
            {'function': {'name': 'click', 'arguments': '{"point_2d":[350,320]}'}}
        ]}}]}).encode())
    monkeypatch.setattr('urllib.request.urlopen', respond)
    model = EndpointModel('http://127.0.0.1:30000/v1', 'test-policy', max_tokens=2048, computer_use=True)
    assert parse_actions(model.generate('Use candidate facts.', b'screenshot')) == [
        {'name': 'click', 'args': {'point_2d': [350, 320]}},
    ]
