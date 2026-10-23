"""可独立阅读的任务评分与统计；不调用模型，不执行被评测答案。"""
import json, math, statistics
from collections import defaultdict


def parse_answer(text):
    """允许整段 JSON 或单个完整 JSON 代码块；不从任意散文中猜答案。"""
    text = text.strip()
    if text.startswith('```json\n') and text.endswith('\n```'):
        text = text[8:-4]
    value = json.loads(text)
    if not isinstance(value, dict): raise ValueError('答案顶层应为对象')
    return value


def typed_equal(actual, expected):
    # Python 的 True == 1；评分时不应把布尔值当作整数正确答案。
    if type(actual) is not type(expected): return False
    if isinstance(expected, dict):
        return actual.keys() == expected.keys() and all(typed_equal(actual[k], v) for k,v in expected.items())
    if isinstance(expected, list):
        return len(actual) == len(expected) and all(typed_equal(a,b) for a,b in zip(actual,expected))
    return actual == expected


def observed_files(artifacts):
    """只接纳真正 MCP read_file 成功结果里的逐行文本；不能用最终回答自证。"""
    observed = {}
    for artifact in artifacts:
        body = artifact.get('body', {})
        if not body.get('ok'): continue
        mcp = body.get('mcp_result', {})
        if mcp.get('isError'): continue
        for block in mcp.get('content', []):
            if block.get('type') != 'text': continue
            try: data = json.loads(block.get('text', ''))
            except (ValueError, TypeError): continue
            if not isinstance(data,dict): continue
            if isinstance(data.get('path'),str) and isinstance(data.get('lines'),list):
                observed[data['path']] = {line['line']:line['text'] for line in data['lines']}
    return observed


def grade_trial(task, trial):
    """输出分项检查；只检验本任务声明的结构事实与引用覆盖，不替代开放文本审阅。"""
    state = trial['state']
    checks = {'completed':state['status']=='final_answer', 'schema':False,
              'facts':False, 'citations':False, 'source_unchanged':trial.get('source_unchanged') is True}
    reasons=[]
    try:
        obj=parse_answer(state['answer'])
        checks['schema']=(set(obj)=={'answer','evidence','explanation'} and isinstance(obj['answer'],dict)
            and isinstance(obj['explanation'],str) and bool(obj['explanation'].strip())
            and isinstance(obj['evidence'],list) and bool(obj['evidence']))
        checks['facts']=typed_equal(obj.get('answer'),task['expected'])
        observed=observed_files(trial.get('artifacts',[])); covered=set(); valid=True
        evidence=obj.get('evidence')
        if not isinstance(evidence,list) or not evidence: valid=False
        else:
            for item in evidence:
                if (not isinstance(item,dict) or set(item)!={'path','start','end'}
                    or not isinstance(item['path'],str) or type(item['start']) is not int
                    or type(item['end']) is not int):
                    valid=False;continue
                path,start,end=item['path'],item['start'],item['end']
                if not 1<=start<=end<=1000: valid=False;continue
                lines=observed.get(path,{})
                if any(i not in lines for i in range(start,end+1)): valid=False;continue
                covered.update((path,i) for i in range(start,end+1))
            valid=valid and all((task['source'],i) in covered for i in task['required_lines'])
        checks['citations']=bool(valid)
    except (ValueError,TypeError,KeyError): reasons.append('未得到要求的 JSON 结构')
    reasons += [k for k,v in checks.items() if not v]
    return {'passed':all(checks.values()),'checks':checks,'failed_checks':reasons,
            'ungraded':['explanation 的自然语言事实一致性','教学表达质量']}


def pass_metrics(outcomes, k):
    """一个任务 n 次独立试验中抽取 k 次的无偏估计；不同任务最后等权平均。"""
    if not outcomes or any(type(x) is not bool for x in outcomes): raise ValueError('结果必须是非空布尔列表')
    n=len(outcomes);c=sum(outcomes)
    if type(k) is not int or not 1<=k<=n: raise ValueError('需要 1 <= k <= n')
    combinations=math.comb(n,k)
    return {'pass_at_k':1-(math.comb(n-c,k) if n-c>=k else 0)/combinations,
            'pass_power_k':(math.comb(c,k) if c>=k else 0)/combinations}


def summarize(trials,k=1):
    """按 variant 和 task 聚合；失败试验仍留在分母与资源统计中。"""
    variants=defaultdict(lambda:defaultdict(list))
    for trial in trials: variants[trial['variant']][trial['task_id']].append(trial)
    rows=[]
    for variant,tasks in sorted(variants.items()):
        per_task={name:pass_metrics([t['grade']['passed'] for t in runs],k) for name,runs in tasks.items()}
        flat=[t for runs in tasks.values() for t in runs]
        rows.append({'variant':variant,'tasks':len(tasks),'trials':len(flat),
            'passed_trials':sum(t['grade']['passed'] for t in flat),
            'macro_pass_at_k':statistics.mean(v['pass_at_k'] for v in per_task.values()),
            'macro_pass_power_k':statistics.mean(v['pass_power_k'] for v in per_task.values()),
            'known_total_tokens':sum(sum(u.get('total_tokens',0) for u in t.get('observed_request_usage',t['state']['usage'])) for t in flat),
            'usage_complete':all(len(t.get('observed_request_usage',t['state']['usage']))==t['state']['turns'] for t in flat),
            'model_requests':sum(t['state']['turns'] for t in flat),
            'tool_calls':sum(t['state']['tool_calls'] for t in flat),
            'mean_elapsed_seconds':statistics.mean(t['elapsed_seconds'] for t in flat),'per_task':per_task})
    return rows


def diagnose_format(task,trial):
    """只作为复盘：从唯一 JSON 围栏提取内容，不改变原始格式失败判定。"""
    import copy,re
    blocks=re.findall(r'```json\s*\n(.*?)\n```',trial['state']['answer'],flags=re.S)
    if len(blocks)!=1:return {'available':False,'reason':'没有唯一完整 JSON 围栏'}
    extracted=copy.deepcopy(trial);extracted['state']['answer']=blocks[0]
    grade=grade_trial(task,extracted)
    return {'available':True,'extracted_grade':grade,
            'note':'诊断提取后事实与引用检查；不豁免原任务的输出格式要求，仍需核验围栏之外的文字。'}
