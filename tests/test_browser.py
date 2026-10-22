import asyncio
import json
from pathlib import Path
import urllib.request
import urllib.error
import pytest
from auto_apply.agent import fill_application
from auto_apply.fixture import serve
from auto_apply.safety import SubmissionGuard
from auto_apply.trajectory import Trajectory
from auto_apply.upstream import make_env
from auto_apply.inference import smoke
from auto_apply.evaluation import evaluate_fixture, export_episode
from auto_apply.computer import fill_with_computer

ROOT = Path(__file__).resolve().parents[1]


def test_complete_workflow_and_submission_defenses(tmp_path):
    asyncio.run(workflow(tmp_path))


async def workflow(tmp_path):
    with serve() as (origin, token, records):
        env = make_env()
        try:
            await env.setup()
            guard = SubmissionGuard(origin, token)
            await guard.install(env.context)
            await env.page.goto(origin + "/apply")
            trace = Trajectory(tmp_path / "run")
            await trace.record(env, {"name": "goto_url", "args": {"url": origin + "/apply"}}, {"success": True})
            result = await fill_application(env, ROOT / "profiles/dummy.json", trace)
            evaluation = await evaluate_fixture(env.page, ROOT / "fixtures/expected.json")
            assert evaluation["all_correct"] and evaluation["score"] == 1.0
            trace.write("fixture_evaluation.json", evaluation)
            episode = export_episode(trace.directory)
            assert episode["metadata"]["reward"] == 1.0
            assert set(episode["metadata"]["action_extensions"]) == {"profile_fill", "scroll_to_field", "upload_resume"}
            assert episode["messages"][1]["content"][0]["image_url"]["url"].startswith("data:image/png;base64,")
            task = json.loads((trace.directory / "benchmark.jsonl").read_text())
            assert task["metadata"]["start_url"] == origin + "/apply"
            expected = json.loads((ROOT / "fixtures/expected.json").read_text())
            for key, value in expected.items():
                assert await env.page.locator("#" + key).input_value() == value
            assert await env.page.locator("#resume").evaluate("e => e.files[0].name") == "dummy-resume.txt"
            assert len(result["filled"]) == 11
            assert {q["field_id"] for q in result["needs_human"]} == {"salary", "motivation"}
            assert result["all_fills_verified"]
            await env.page.evaluate("""() => {const f=document.createElement('iframe');f.name='sink';f.hidden=true;
                document.body.append(f);document.querySelector('form').target='sink'}""")
            # Click, implicit keyboard submission, JS submit, and JS fetch cannot send an application.
            for attack in [
                "document.querySelector('#submit').click()",
                "HTMLFormElement.prototype.submit.call(document.querySelector('form'))",
                "fetch('/submit', {method:'POST',body:'bypass'}).catch(()=>{})",
                "fetch('/submit?email=leaked').catch(()=>{})",
            ]:
                await env.page.evaluate(attack)
                await env.page.wait_for_timeout(150)
                if not env.page.url.endswith("/apply"):
                    await env.page.goto(origin + "/apply")
            await env.page.locator("#email").press("Enter")
            await env.page.wait_for_timeout(150)
            assert records == []
            assert len(guard.blocked) >= 4
            # Even clients outside the guarded browser cannot submit without server capability.
            with pytest.raises(urllib.error.HTTPError) as exc:
                urllib.request.urlopen(urllib.request.Request(origin + "/submit", data=b"bypass"))
            assert exc.value.code == 403
            assert not await guard.approve_from_terminal(env.page, reader=lambda _: "yes")
            assert await guard.approve_from_terminal(env.page, reader=lambda _: f"APPROVE LOCAL APPLICATION {guard.nonce}")
            # Changed application invalidates approval.
            await env.page.locator("#city").fill("Changed City")
            await env.page.locator("#submit").click()
            await env.page.wait_for_timeout(150)
            assert records == []
            await env.page.locator("#city").fill("Example City")
            assert await guard.approve_from_terminal(env.page, reader=lambda _: f"APPROVE LOCAL APPLICATION {guard.nonce}")
            await env.page.evaluate("document.querySelector('form').target='_self'")
            await env.page.locator("#submit").click()
            await env.page.locator("#receipt").wait_for()
            assert len(records) == 1
            assert records[0]["email"] == "alex@example.test"
            assert records[0]["resume"]["filename"] == "dummy-resume.txt"
            assert records[0]["resume"]["bytes"] > 0
            assert guard.consumed
        finally:
            await env.exit()


def test_inference_wiring_with_fake_model_is_not_pretrained_validation(tmp_path):
    class FakeModel:
        model = "TEST DOUBLE - NOT PRETRAINED"
        def generate(self, prompt, screenshot):
            assert screenshot.startswith(b"\x89PNG")
            return '<tool_call>{"name":"write","arguments":{"message":"ORCHID"}}</tool_call>'

    async def exercise():
        with serve() as (origin, token, _):
            env = make_env()
            try:
                await env.setup()
                guard = SubmissionGuard(origin, token)
                await guard.install(env.context)
                await env.page.goto(origin + "/smoke")
                result = await smoke(env, FakeModel(), Trajectory(tmp_path / "fake"))
                assert result["success"]
                assert not result["training_launched"]
            finally:
                await env.exit()
    asyncio.run(exercise())


def test_workday_multiple_steps_use_profile_without_submission(tmp_path):
    async def exercise():
        with serve(application_id='workday-1') as (origin, token, records):
            env = make_env()
            try:
                await env.setup()
                guard = SubmissionGuard(origin, token)
                await guard.install(env.context)
                await env.page.goto(origin + '/apply')
                trace = Trajectory(tmp_path / 'workday')
                result = await fill_application(env, ROOT / 'profiles/dummy.json', trace)
                assert result['all_fills_verified']
                assert len(result['filled']) == 11
                assert {q['field_id'] for q in result['needs_human']} == {'linkedin','salary','motivation','custom_answer'}
                assert await env.page.locator('#full_name').input_value() == 'Alex Example'
                assert await env.page.locator('#resume').evaluate('e => e.files[0].name') == 'dummy-resume.txt'
                assert await env.page.locator('#submit').is_visible()
                assert records == []
                events = [json.loads(line) for line in (trace.directory / 'trajectory.jsonl').read_text().splitlines()]
                assert sum(e['action']['name'] == 'application_next_step' for e in events) == 3
            finally:
                await env.exit()
    asyncio.run(exercise())


def test_visual_loop_executes_model_actions_uploads_and_audits(tmp_path):
    """Scripted model double validates wiring only, not pretrained competence."""
    async def exercise():
        with serve() as (origin, token, records):
            env = make_env()
            try:
                await env.setup()
                guard = SubmissionGuard(origin, token)
                await guard.install(env.context)
                await env.page.goto(origin + '/apply')
                await env.page.set_content('<form method="post" action="/submit"><label>Full name<input id="random-name" name="name"></label><label>Resume<input id="random-file" type="file" name="resume"></label><label>Are you authorized to work in the United States?<select id="random-select"><option value="">Choose</option><option value="yes">Yes</option></select></label><button id="random-submit" type="submit">Submit</button></form>')
                points = []
                for selector in ('#random-name', '#random-file', '#random-select', '#random-submit'):
                    box = await env.page.locator(selector).bounding_box()
                    points.append([(box['x'] + box['width'] / 2) * 1000 / 1279,
                                   (box['y'] + box['height'] / 2) * 1000 / 899])
                actions = [
                    {'name': 'write', 'arguments': {'message': 'Alex Example'}},
                    [{'name': 'click', 'arguments': {'point_2d': points[0]}},
                     {'name': 'write', 'arguments': {'message': 'Alex Example'}}],
                    {'name': 'click', 'arguments': {'point_2d': points[3]}},
                    {'name': 'click', 'arguments': {'point_2d': points[2]}},
                    {'name': 'done', 'arguments': {'response': 'Ready for review.'}},
                    {'name': 'select_option', 'arguments': {'point_2d': points[2], 'label': 'Yes'}},
                    {'name': 'upload_resume', 'arguments': {'point_2d': points[1], 'resume_index': 0}},
                    {'name': 'done', 'arguments': {'response': 'Ready for review.'}},
                ]

                class ModelDouble:
                    model = 'TEST DOUBLE - NOT PRETRAINED'
                    turns = 0

                    def generate(self, prompt, screenshot):
                        assert screenshot.startswith(b'\x89PNG')
                        assert 'candidate_facts' in prompt
                        assert 'random-name' not in prompt and 'random-file' not in prompt
                        if self.turns:
                            assert 'feedback' in prompt
                        if self.turns == 1:
                            assert 'No editable input is focused' in prompt
                        if self.turns == 3:
                            assert 'Final submission is blocked' in prompt
                        if self.turns == 4:
                            assert 'native dropdown' in prompt
                        if self.turns == 5:
                            assert 'Independent review found fields needing correction' in prompt
                        action = actions[self.turns]
                        self.turns += 1
                        return '<tool_call>' + json.dumps(action if isinstance(action, list) else [action]) + '</tool_call>'

                trace = Trajectory(tmp_path / 'visual')
                await trace.record(env, {'name': 'goto_url', 'args': {'url': origin + '/apply'}}, {'success': True})
                result = await fill_with_computer(env, ROOT / 'profiles/dummy.json', trace, ModelDouble(), max_steps=9,
                                                  coordinate_space='normalized')
                assert result['success'] and result['policy'] == 'openwebrl_visual'
                assert len(result['filled']) == 3 and result['stop_reason'] == 'done'
                assert result['review_retries'] == 1
                assert await env.page.locator('#random-name').input_value() == 'Alex Example'
                assert records == []
                assert guard.blocked == []  # Submission click was blocked before any request.
                assert export_episode(trace.directory)['metadata']['policy'] == 'openwebrl_visual'
            finally:
                await env.exit()
    asyncio.run(exercise())
