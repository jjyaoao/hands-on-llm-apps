import asyncio,json,sys,tempfile,unittest,subprocess
from pathlib import Path
from pypdf import PdfWriter
from corpus import Corpus
from study_runtime import StudyRuntime,Harness,citation_check,request_evidence_revision,ROOT,PROJECT
from checkpoint_store import CheckpointStore

class CorpusTests(unittest.TestCase):
    def test_pdf_positions_and_actual_content(self):
        c=Corpus(PROJECT/'fixtures/mini-guide');hits=c.search('检索 分数 概率')['hits']
        pdf=next(h for h in hits if h['location']['page']==1)
        self.assertIn('不代表事实正确',c.read(pdf['id'])['text'])
        self.assertEqual(pdf['location']['line_unit'],'extracted_text_line')
    def test_unknown_id_and_changed_source(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/'notes.md';p.write_text('旧资料', encoding='utf-8');old=Corpus(directory).chunks[0].id
            p.write_text('新的资料', encoding='utf-8');c=Corpus(directory)
            with self.assertRaises(ValueError):c.read(old)
            with self.assertRaises(ValueError):c.read('../notes.md')
    def test_import_does_not_execute_or_follow_links(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'sentinel.py').write_text("raise RuntimeError('不能运行')", encoding='utf-8')
            try:
                (root/'outside.txt').symlink_to('/etc/hosts')
            except OSError as error:
                if getattr(error, 'winerror', None) == 1314:
                    self.skipTest('Windows 当前账号未授权创建符号链接')
                raise
            c=Corpus(root);self.assertEqual([x['path'] for x in c.documents],['sentinel.py'])
    def test_blank_pdf_page_is_reported(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'notes.md').write_text('可读取的说明', encoding='utf-8')
            writer=PdfWriter();writer.add_blank_page(width=300,height=300)
            with (root/'scan.pdf').open('wb') as f:writer.write(f)
            pdf=next(x for x in Corpus(root).documents if x['kind']=='pdf')
            self.assertEqual(pdf['empty_pages'],[1])
    def test_search_input_bounds(self):
        c=Corpus(PROJECT/'fixtures/flashcards')
        for k in [0,6,True]:
            with self.assertRaises(ValueError):c.search('due',k)
        self.assertEqual(c.search('unfindable987xyz')['hits'],[])
    def test_citation_requires_actual_read(self):
        c=Corpus(PROJECT/'fixtures/mini-guide');cid=c.chunks[0].id
        self.assertFalse(citation_check(f'结论[{cid}]',[],c)['all_citations_read'])
        body={'ok':True,'mcp_result':{'content':[{'type':'text','text':json.dumps(c.read(cid))}]}}
        self.assertTrue(citation_check(f'结论[{cid}]',[{'body':body}],c)['all_citations_read'])
    def test_wrong_environment_cannot_resume(self):
        with tempfile.TemporaryDirectory() as d:
            store=CheckpointStore(Path(d)/'runs.db')
            try:
                a=StudyRuntime(PROJECT/'fixtures/mini-guide');b=StudyRuntime(PROJECT/'fixtures/flashcards')
                h=Harness.create(store,'导读',Path(d)/'log.jsonl',runtime=a)
                with self.assertRaises(ValueError):Harness(store,h.run_id,Path(d)/'log.jsonl',runtime=b)
            finally:store.close()
    def test_whole_source_and_pdf_page(self):
        c=Corpus(PROJECT/'fixtures/mini-guide')
        whole=c.read_document('search.py')
        self.assertIn('scored.sort',whole['text'])
        self.assertEqual(whole['location']['end'],12)
        self.assertEqual(c.read_document('learning-notes.pdf',2)['location']['page'],2)
        with self.assertRaises(ValueError):c.read_document('../other.py')
        with self.assertRaises(ValueError):c.read_document('learning-notes.pdf',0)
    def test_revision_keeps_goal_and_consumed_budget(self):
        with tempfile.TemporaryDirectory() as d:
            store=CheckpointStore(Path(d)/'runs.db')
            try:
                runtime=StudyRuntime(PROJECT/'fixtures/mini-guide')
                h=Harness.create(store,'保持原目标',Path(d)/'log.jsonl',runtime=runtime)
                h.state.update(status='citation_review_required',phase='finished',answer='未带引用',turns=3,tool_calls=4)
                h.checkpoint();request_evidence_revision(h)
                self.assertEqual((h.state['turns'],h.state['tool_calls']),(3,4))
                self.assertEqual(h.state['goal'],'保持原目标')
                self.assertEqual(h.state['messages'][-2]['content'],'未带引用')
                self.assertEqual(h.state['phase'],'model_ready')
            finally:store.close()
    def test_real_mcp_process_resume(self):
        directory=ROOT/'.local/student-runs/l08/test-process';directory.mkdir(parents=True,exist_ok=True)
        command=[sys.executable, '-X', 'utf8',str(PROJECT/'src/study_cli.py'),'--corpus',str(PROJECT/'fixtures/mini-guide'),
                 '--db',str(directory/'runs.db')]
        first=json.loads(subprocess.check_output(command+['--goal','导读资料','--steps','2'],text=True, encoding='utf-8'))
        second=json.loads(subprocess.check_output(command+['--run-id',first['run_id']],text=True, encoding='utf-8'))
        self.assertEqual(first['state']['tool_calls'],1)
        self.assertEqual(second['state']['tool_calls'],4)
        self.assertEqual(second['state']['status'],'final_answer')
        self.assertTrue(second['citations']['all_citations_read'])
if __name__=='__main__':unittest.main()
