import copy,json,math,unittest
from pathlib import Path
from evaluation_lab import grade_trial,pass_metrics,typed_equal,summarize
HERE=Path(__file__).resolve().parents[1]
ROOT=HERE.parent
TASKS=json.loads((HERE/'数据/tasks.json').read_text(encoding='utf-8'))['tasks']

def valid_trial(task):
    # 来自已经真实执行的 MCP 记录；改的是待评分回答，不冒充一次新模型运行。
    record=json.loads((ROOT/'06 Harness 与持续任务运行/数据/实验记录/deepseek-harness.json').read_text(encoding='utf-8'))
    answer={'answer':task['expected'],'evidence':[{'path':'config.py','start':7,'end':11}], 'explanation':'教学用正确结构示例'}
    return {'state':{'status':'final_answer','answer':json.dumps(answer,ensure_ascii=False),'usage':[], 'turns':0,'tool_calls':0},
        'source_unchanged':True,'artifacts':record['artifacts'],'variant':'example','task_id':task['id'],'elapsed_seconds':0}

class EvaluationTests(unittest.TestCase):
    def test_all_reference_structures(self):
        for task in TASKS:self.assertTrue(grade_trial(task,valid_trial(task))['passed'])
    def test_boolean_is_not_integer(self):
        self.assertFalse(typed_equal(True,1));self.assertFalse(typed_equal({'x':0},{'x':False}))
    def test_correct_fact_without_read_evidence_fails(self):
        trial=valid_trial(TASKS[0]);trial['artifacts']=[]
        g=grade_trial(TASKS[0],trial);self.assertTrue(g['checks']['facts']);self.assertFalse(g['checks']['citations'])
    def test_missing_decisive_line_fails(self):
        trial=valid_trial(TASKS[2]);obj=json.loads(trial['state']['answer']);obj['evidence'][0]['end']=10
        trial['state']['answer']=json.dumps(obj)
        self.assertFalse(grade_trial(TASKS[2],trial)['checks']['citations'])
    def test_task_stop_and_source_change(self):
        trial=valid_trial(TASKS[0]);trial['state']['status']='turn_budget';trial['source_unchanged']=False
        g=grade_trial(TASKS[0],trial);self.assertFalse(g['passed']);self.assertFalse(g['checks']['source_unchanged'])
    def test_non_json_and_outside_line_rejected(self):
        trial=valid_trial(TASKS[0]);trial['state']['answer']='已经完成，答案肯定正确。'
        self.assertFalse(grade_trial(TASKS[0],trial)['passed'])
        trial=valid_trial(TASKS[0]);obj=json.loads(trial['state']['answer']);obj['evidence'][0]['end']=12
        trial['state']['answer']=json.dumps(obj);self.assertFalse(grade_trial(TASKS[0],trial)['checks']['citations'])
    def test_estimator_enumeration(self):
        from itertools import combinations
        outcomes=[True,False,True,False]; pairs=list(combinations(outcomes,2));actual=pass_metrics(outcomes,2)
        self.assertAlmostEqual(actual['pass_at_k'],sum(any(p) for p in pairs)/len(pairs))
        self.assertAlmostEqual(actual['pass_power_k'],sum(all(p) for p in pairs)/len(pairs))
        with self.assertRaises(ValueError):pass_metrics(outcomes,5)
    def test_macro_does_not_pool_unequal_tasks(self):
        trials=[]
        for i,results in enumerate([[True],[False,False,False]]):
            for outcome in results:
                trial=valid_trial(TASKS[i]);trial['grade']={'passed':outcome};trials.append(trial)
        row=summarize(trials)[0];self.assertEqual(row['macro_pass_at_k'],.5)
        self.assertEqual(row['passed_trials']/row['trials'],.25)
    def test_rule_grade_does_not_claim_semantics(self):
        task=TASKS[2];trial=valid_trial(task);obj=json.loads(trial['state']['answer'])
        obj['explanation']='函数总是返回字典。';trial['state']['answer']=json.dumps(obj)
        g=grade_trial(task,trial);self.assertTrue(g['passed']);self.assertTrue(g['ungraded'])
if __name__=='__main__':unittest.main()
