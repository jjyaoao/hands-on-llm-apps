"""测试执行反馈、状态作用域和提示重放；不调用模型。"""
from pathlib import Path
import sys
ROOT_FOR_IMPORT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT_FOR_IMPORT / '08 综合实践一 资料与仓库导读/代码/学习助手/src'))

import asyncio,tempfile,unittest
from pathlib import Path
from exercise_lab import ROOT,PROJECT,LearningStore,catalog,run_exercise
from tutor_runtime import TutorRuntime
from corpus import Corpus

class ExercisesTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'learning.sqlite3'
        self.store=LearningStore(self.path);self.source=ROOT/'08 综合实践一 资料与仓库导读/代码/学习助手/fixtures/flashcards';self.version=Corpus(self.source).fingerprint
        self.lesson=self.store.create('student-a',self.version,'due-cards')
    def tearDown(self):self.store.close();self.tmp.cleanup()
    def record(self,name='student.py'):
        a=run_exercise('due-cards',PROJECT/'exercises/due-cards'/name)
        return self.store.add_attempt(self.lesson,'student-a',self.version,a)
    def test_actual_reference_and_buggy(self):
        for exercise in catalog():
            bad=run_exercise(exercise,PROJECT/'exercises'/exercise/'student.py')
            good=run_exercise(exercise,PROJECT/'exercises'/exercise/'teaching_revision.py')
            self.assertFalse(bad['result']['passed']);self.assertTrue(good['result']['passed'])
            self.assertEqual(len(good['result']['tests']),len(catalog()[exercise]['tests']))
    def test_failure_then_pass_reopen(self):
        self.assertEqual(self.record()['status'],'needs_work')
        self.assertEqual(self.record('teaching_revision.py')['status'],'tests_passed')
        self.store.close();self.store=LearningStore(self.path)
        self.assertEqual(len(self.store.read(self.lesson,'student-a',self.version)['attempts']),2)
    def test_scope(self):
        with self.assertRaises(KeyError):self.store.read(self.lesson,'student-b',self.version)
        with self.assertRaises(ValueError):self.store.read(self.lesson,'student-a','new-version')
    def test_outside_code_rejected(self):
        outside=Path(self.tmp.name)/'code.py';outside.write_text('def solve():return 1', encoding='utf-8')
        with self.assertRaises(PermissionError):run_exercise('due-cards',outside)
    def test_no_attempt_no_hint(self):
        self.assertEqual(self.store.next_hint(self.lesson,'student-a',self.version,'a')['level'],0)
    def test_hint_replay_and_progress(self):
        self.record();a=self.store.next_hint(self.lesson,'student-a',self.version,'a')
        self.assertEqual(a,self.store.next_hint(self.lesson,'student-a',self.version,'a'))
        self.assertEqual(a['level'],1)
        self.assertEqual(self.store.next_hint(self.lesson,'student-a',self.version,'b')['level'],2)
    def test_tool_cannot_select_other_student_or_write_status(self):
        r=TutorRuntime(self.source,self.store,self.lesson,'student-a')
        self.assertNotIn('run_code',r.allowed);self.assertNotIn('set_status',r.allowed)
        with self.assertRaises(ValueError):asyncio.run(r.execute(None,None,'read_learning_state',{'learner':'b'},set()))
        with self.assertRaises(PermissionError):asyncio.run(r.execute(None,None,'request_next_hint',{},set()))
    def test_new_attempt_changes_snapshot(self):
        r=TutorRuntime(self.source,self.store,self.lesson,'student-a');old=r.snapshot()
        self.record();self.assertNotEqual(old,r.snapshot())
    def test_pass_is_not_mastery(self):
        self.record('teaching_revision.py');hint=self.store.next_hint(self.lesson,'student-a',self.version,'a')
        self.assertIn('不是掌握证明',hint['hint'])

if __name__=='__main__':unittest.main()
