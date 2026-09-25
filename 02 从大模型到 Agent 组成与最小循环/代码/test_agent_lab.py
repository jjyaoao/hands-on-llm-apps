"""失败路径、协议关联与文件边界测试；真实 DeepSeek 质量另行验收。"""
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from agent_lab import (RepoTools, ReplayModel, run_agent, success_replay, tool_response,
                       DeepSeekModel, ModelError, validate_deepseek_model)
from unittest.mock import patch

DATA = Path(__file__).resolve().parents[1] / "数据/demo-repo"

class AgentTests(unittest.TestCase):
    def setUp(self):
        self.tools = RepoTools(DATA)
    def test_real_file_evidence_and_call_ids(self):
        run = run_agent("定位配置加载入口", success_replay(), self.tools)
        self.assertEqual(run['status'], 'final_answer')
        results = [m for m in run['messages'] if m['role'] == 'tool']
        self.assertEqual([m['tool_call_id'] for m in results], ['c1','c2','c3'])
        data = json.loads(results[-1]['content'])['data']
        self.assertEqual(data['lines'][6]['text'], 'def load_settings():')
        self.assertEqual(run['task_success'], 'requires_evidence_review')
    def test_argument_and_tool_errors(self):
        for name, arg, code in [('delete_file', '{}', 'unknown_tool'), ('read_file', '{', 'invalid_arguments'),
                                ('read_file', {'path': 42}, 'invalid_arguments'), ('list_files', {'extra': 1}, 'invalid_arguments'),
                                ('search_text', {'query': ''}, 'invalid_arguments')]:
            self.assertEqual(self.tools.execute(name, arg)['error']['code'], code)
    def test_path_boundary_and_symlink(self):
        self.assertEqual(self.tools.execute('read_file', {'path':'../README.md'})['error']['code'], 'out_of_scope')
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)/'repo'; root.mkdir()
            (Path(d)/'secret.txt').write_text('should not be read', encoding='utf-8')
            try:
                (root/'main.py').symlink_to(Path(d)/'secret.txt')
            except OSError as exc:
                if getattr(exc, 'winerror', None) == 1314:
                    self.skipTest('当前 Windows 账户没有创建符号链接的权限')
                raise
            self.assertEqual(RepoTools(root).execute('read_file', {'path':'main.py'})['error']['code'], 'out_of_scope')
    def test_missing_then_recovery(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'repo'; shutil.copytree(DATA,root); (root/'settings.json').unlink()
            model=ReplayModel([tool_response('x1','read_file',{'path':'settings.json'}), tool_response('x2','list_files',{}),
                               {'role':'assistant','content':'文件缺失，需要提供配置文件。'}])
            run=run_agent('查配置',model,RepoTools(root))
            self.assertEqual(run['trace'][1]['result']['error']['code'],'not_found')
            self.assertEqual(run['status'],'final_answer')
    def test_budgets_and_duplicate_ids(self):
        calls=[tool_response(f'x{i}','list_files',{}) for i in range(4)]
        self.assertEqual(run_agent('test',ReplayModel(calls),self.tools,max_turns=2)['status'],'turn_budget')
        self.assertEqual(run_agent('test',ReplayModel(calls),self.tools,max_tool_calls=1)['status'],'tool_budget')
        self.assertEqual(run_agent('test',ReplayModel([calls[0],calls[0]]),self.tools)['status'],'duplicate_call_id')
    def test_batch_results_are_all_returned(self):
        msg=tool_response('b1','list_files',{})
        msg['tool_calls'] += tool_response('b2','search_text',{'query':'load_settings'})['tool_calls']
        run=run_agent('test',ReplayModel([msg,{'role':'assistant','content':'完成'}]),self.tools)
        self.assertEqual([m['tool_call_id'] for m in run['messages'] if m['role']=='tool'], ['b1','b2'])
    def test_empty_answer_and_missing_key(self):
        self.assertEqual(run_agent('test',ReplayModel([{'role':'assistant','content':''}]),self.tools)['status'],'empty_answer')
        with patch.dict('os.environ',{},clear=True):
            with self.assertRaises(ModelError): DeepSeekModel()
    def test_imagined_answer_is_not_success(self):
        run=run_agent('test',ReplayModel([{'role':'assistant','content':'入口是不存在的 foo.py'}]),self.tools)
        self.assertEqual(run['tool_calls'],0)
        self.assertEqual(run['task_success'],'requires_evidence_review')


class DeepSeekContractTests(unittest.TestCase):
    @patch('agent_lab.list_deepseek_models', return_value=['deepseek-flash', 'future-model'])
    def test_validate_selected_model(self, mocked):
        selected, available = validate_deepseek_model('future-model', 'test-key')
        self.assertEqual(selected, 'future-model')
        self.assertIn(selected, available)
        mocked.assert_called_once_with('test-key')

    @patch('agent_lab.list_deepseek_models', return_value=['future-model'])
    def test_validate_rejects_retired_model(self, mocked):
        with self.assertRaisesRegex(ModelError, 'future-model'):
            validate_deepseek_model('retired-model', 'test-key')

    def test_http_payload_and_tool_response(self):
        import io
        captured = {}
        response = {'choices':[{'finish_reason':'tool_calls','message':tool_response('real-format-1','list_files',{})}],
                    'usage':{'prompt_tokens':12,'completion_tokens':8}}
        def transport(request, timeout):
            captured['payload']=json.loads(request.data)
            captured['timeout']=timeout
            return io.BytesIO(json.dumps(response).encode())
        with patch.dict('os.environ',{'DEEPSEEK_API_KEY':'test-only-not-a-key','DEEPSEEK_MODEL':'course-test-model'}):
            model=DeepSeekModel()
            with patch('agent_lab.urllib.request.urlopen',side_effect=transport):
                result=model([{'role':'user','content':'找入口'}],[])
        self.assertEqual(captured['payload']['thinking'],{'type':'disabled'})
        self.assertEqual(captured['payload']['model'],'course-test-model')
        self.assertEqual(result['tool_calls'][0]['id'],'real-format-1')
        self.assertEqual(model.usage,[response['usage']])
    def test_truncated_output_is_a_failure(self):
        import io
        response={'choices':[{'finish_reason':'length','message':{'role':'assistant','content':'半句'}}]}
        with patch.dict('os.environ',{'DEEPSEEK_API_KEY':'test-only-not-a-key'}):
            model=DeepSeekModel()
            with patch('agent_lab.urllib.request.urlopen',return_value=io.BytesIO(json.dumps(response).encode())):
                with self.assertRaises(ModelError):model([],[])
    def test_connection_error_stops_loop(self):
        import urllib.error
        with patch.dict('os.environ',{'DEEPSEEK_API_KEY':'test-only-not-a-key'}):
            model=DeepSeekModel()
            with patch('agent_lab.urllib.request.urlopen',side_effect=urllib.error.URLError('offline')) as transport:
                run=run_agent('找入口',model,RepoTools(DATA))
                self.assertEqual(transport.call_count,1)
        self.assertEqual(run['status'],'model_error')

if __name__ == '__main__': unittest.main()
