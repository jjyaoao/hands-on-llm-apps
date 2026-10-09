"""真实 stdio 验证加 Skill 路由测试；不调用云端模型。"""
import asyncio,contextlib,io,json,tempfile,unittest
from pathlib import Path
from mcp_connection import connect,probe
from skill_lab import SkillLibrary
from skill_mcp_agent import ROOT,run_skill_agent
from agent_lab import ReplayModel,tool_response

class SkillsTests(unittest.TestCase):
    def test_discovery_activation_and_resource_are_distinct(self):
        s=SkillLibrary(ROOT/'05 MCP 与 Skills 能力扩展/代码/skills')
        self.assertEqual(set(s.catalog()[0]),{'name','description'})
        self.assertFalse(s.active)
        with self.assertRaises(PermissionError):s.read_resource('repo-guide','references/conditions.md')
        self.assertIn('references/conditions.md',s.activate('repo-guide'))
        self.assertIn('相对路径',s.read_resource('repo-guide','references/conditions.md'))
        with self.assertRaises(PermissionError):s.read_resource('repo-guide','../SKILL.md')
        self.assertEqual([e['stage'] for e in s.events],['discover','activate','resource'])

    def test_package_name_and_scope(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);p=root/'repo-guide';p.mkdir()
            (p/'SKILL.md').write_text('---\nname: WRONG\ndescription: demo\n---\n正文', encoding='utf-8')
            with self.assertRaises(ValueError):SkillLibrary(root)
            (p/'SKILL.md').write_text('---\nname: repo-guide\ndescription: demo\n---\n正文', encoding='utf-8')
            s=SkillLibrary(root)
            with self.assertRaises(ValueError):s.activate('unknown')

class MCPTests(unittest.IsolatedAsyncioTestCase):
    async def test_real_stdio_with_notebook_style_stderr(self):
        # StringIO 和 Notebook 展示流一样，没有可交给子进程的 fileno。
        with contextlib.redirect_stderr(io.StringIO()):
            r = await probe()
        self.assertFalse(r['config'].get('isError', False))
        self.assertTrue(r['events'])

    async def test_real_protocol_and_scope(self):
        r=await probe()
        self.assertEqual(r['files']['content'][0]['type'],'text')
        self.assertTrue(r['denied']['isError'])
        requests=[e['message'] for e in r['events'] if e['direction']=='client_to_server']
        self.assertEqual([x['method'] for x in requests],['tools/list','tools/call','tools/call','tools/call'])
        for request in requests:
            self.assertEqual(request['params']['_meta']['io.modelcontextprotocol/protocolVersion'],'2026-07-28')
        responses=[e['message'] for e in r['events'] if e['direction']=='server_to_client']
        self.assertEqual({x['id'] for x in requests},{x['id'] for x in responses})
        lines=json.loads(r['config']['content'][0]['text'])['lines']
        self.assertEqual(lines[6]['text'],'def load_settings():')

    async def test_invalid_args_and_unknown_tools(self):
        async with connect() as client:
            missing=await client.call_tool('read_file',{})
            unknown=await client.call_tool('not_registered',{})
            self.assertTrue(missing.is_error)
            self.assertTrue(unknown.is_error)

    async def test_joint_replay_executes_real_mcp_and_skill_files(self):
        responses=[tool_response('a','activate_skill',{'name':'repo-guide'}),
            tool_response('b','read_skill_resource',{'name':'repo-guide','path':'references/conditions.md'}),
            tool_response('c','mcp_read_file',{'path':'config.py'}),
            {'role':'assistant','content':'教学回放结束；这不是模型自主选择的证据。'}]
        r=await run_skill_agent('回放路由测试',ReplayModel(responses))
        self.assertEqual(r['status'],'final_answer');self.assertEqual(r['tool_calls'],3)
        self.assertTrue(all(e['result']['ok'] for e in r['trace']))
        self.assertEqual([e['stage'] for e in r['skill_events']],['discover','activate','resource'])

    async def test_unknown_tool_and_budget_do_not_execute_extra_action(self):
        model=ReplayModel([tool_response('x','write_file',{'path':'config.py'}),{'role':'assistant','content':'停止'}])
        r=await run_skill_agent('边界测试',model)
        self.assertFalse(r['trace'][0]['result']['ok'])
        self.assertFalse(any(e['message'].get('method')=='tools/call' for e in r['mcp_events']))
        same=tool_response('repeat','activate_skill',{'name':'repo-guide'})
        r=await run_skill_agent('重复 ID',ReplayModel([same,same]))
        self.assertEqual(r['status'],'invalid_call_ids');self.assertEqual(r['tool_calls'],1)
        r=await run_skill_agent('一轮',ReplayModel([same]),max_turns=1)
        self.assertEqual(r['status'],'turn_budget')

if __name__=='__main__':unittest.main()
