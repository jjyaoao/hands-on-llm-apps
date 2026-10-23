"""显式运行有上限的真实评估。单条提示是 A/B 的唯一预设差异；每轮独立状态。"""
import asyncio, copy, getpass, hashlib, json, os, sys, time, uuid
from pathlib import Path
from datetime import datetime, timezone
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'06 Harness 与持续任务运行/代码'))
from harness_lab import Harness, source_snapshot
from checkpoint_store import CheckpointStore
from agent_lab import DeepSeekModel, ModelError, validate_deepseek_model
from evaluation_lab import grade_trial, summarize
HERE=Path(__file__).resolve().parents[1]
CHANGE='回答前逐项核对运行条件：区分源码保证与样例文件；区分相对路径与绝对路径；没有检查的类型和字段不要声称有保证。'

class PromptVariant:
    def __init__(self,model,variant):
        if variant not in {'base','condition_check'}:raise ValueError('未知对照')
        self.inner,self.variant=model,variant
        self.errors=[]
    @property
    def usage(self):return self.inner.usage
    def __call__(self,messages,tools):
        actual=copy.deepcopy(messages)
        if self.variant=='condition_check': actual[0]['content']+='\n'+CHANGE
        try:return self.inner(actual,tools)
        except ModelError as error:
            self.errors.append(str(error));raise

async def run_suite(target, key, selected_model, available_models, resume=False):
    task_path=HERE/'数据/tasks.json'; dataset=json.loads(task_path.read_text(encoding='utf-8'))
    report={'kind':'real_deepseek_agent_evaluation','recorded_at':datetime.now(timezone.utc).isoformat(),
        'model':selected_model,'available_models_at_start':available_models,'thinking':'disabled',
        'max_tokens_per_call':1000,'automatic_retries':0,'trials_per_task_variant':2,
        'limits':{'max_turns':4,'max_tools':8,'context_chars':18000},'single_change':CHANGE,
        'dataset_sha256':hashlib.sha256(task_path.read_bytes()).hexdigest(),
        'source_snapshot':source_snapshot(),'trials':[],'complete':False,
        'limitations':['四题两次属于开发集演示，不能估计总体能力或稳定提升。','自然语言 explanation 未被规则评分覆盖。']}
    if resume:
        saved=json.loads(target.read_text(encoding='utf-8'))
        for field in ['model','limits','single_change','dataset_sha256','source_snapshot']:
            if saved[field]!=report[field]:raise ValueError('设置变化，不能接续同一实验')
        report=saved
    elif target.exists():raise FileExistsError('已有记录；使用 --resume 跳过已记录试验，或另存原始结果后新建实验')
    done={(t['task_id'],t['repeat'],t['variant']) for t in report['trials']}
    work=ROOT/'.local/student-runs/l07'/uuid.uuid4().hex;work.mkdir(parents=True)
    def save():
        encoded=json.dumps(report,ensure_ascii=False,indent=2)
        if key and key in encoded:raise RuntimeError('结果含凭据，拒绝保存')
        target.parent.mkdir(parents=True,exist_ok=True);target.write_text(encoded+'\n', encoding='utf-8')
    for repeat in range(2):
        for number,task in enumerate(dataset['tasks']):
            # 交替两种版本的先后次序，减少总把某版本放前面的时间顺序偏差。
            order=['base','condition_check'] if (repeat+number)%2==0 else ['condition_check','base']
            for variant in order:
                if (task['id'],repeat+1,variant) in done:continue
                store=CheckpointStore(work/f'{repeat}-{task["id"]}-{variant}.sqlite3')
                try:
                    question=dataset['format_instruction']+'\n'+task['question']
                    h=Harness.create(store,question,work/f'{repeat}-{task["id"]}-{variant}.jsonl',**report['limits'])
                    model=PromptVariant(DeepSeekModel(selected_model),variant);start=time.perf_counter()
                    state=await h.drive(model)
                    trial={'task_id':task['id'],'repeat':repeat+1,'variant':variant,'state':state,
                        'model_errors':model.errors,'observed_request_usage':model.usage,
                        'elapsed_seconds':round(time.perf_counter()-start,4),
                        'source_unchanged':source_snapshot()==report['source_snapshot'],
                        'artifacts':[{**a,'body':store.read_artifact(h.run_id,a['id'])} for a in state['artifacts']]}
                    trial['grade']=grade_trial(task,trial);report['trials'].append(trial);save()
                    print(task['id'],repeat+1,variant,state['status'],trial['grade']['checks'],flush=True)
                    if state['status']=='needs_review':
                        print('服务或未确定结果需要检查；停止后续请求，已有记录保留。',flush=True);return
                finally:store.close()
    report['complete']=True;report['summary_k1']=summarize(report['trials'],1)
    report['summary_k2']=summarize(report['trials'],2);save()
    print('Saved',len(report['trials']),'trials; all failures retained.',flush=True)

def main():
    if '--live' not in sys.argv: raise SystemExit('真实模型请求需显式传入 --live')
    key=os.environ.get('DEEPSEEK_API_KEY') or getpass.getpass('DeepSeek temporary key (hidden): ')
    previous=os.environ.get('DEEPSEEK_API_KEY');os.environ['DEEPSEEK_API_KEY']=key
    try:
        selected,available=validate_deepseek_model(api_key=key)
        print('本次选择的模型:',selected)
        print('当前账号可用模型:',available)
        asyncio.run(run_suite(ROOT/'.local/student-runs/l07/NEW-evaluation.json',key,selected,available,resume='--resume' in sys.argv))
    finally:
        if previous is None:os.environ.pop('DEEPSEEK_API_KEY',None)
        else:os.environ['DEEPSEEK_API_KEY']=previous
        key=''
if __name__=='__main__':main()
