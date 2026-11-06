"""显式练习执行与本地学习记录；完成状态由实际测试决定。"""
import hashlib,json,re,sqlite3,subprocess,sys,tempfile,uuid
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[4];PROJECT=Path(__file__).resolve().parents[1]
CATALOG=PROJECT/'exercises/catalog.json'

def catalog():return {e['id']:e for e in json.loads(CATALOG.read_text(encoding='utf-8'))['exercises']}

def run_exercise(exercise_id,submission):
    """由 Notebook/CLI 操作者选择本地文件；Agent 工具不接收任意代码或执行路径。"""
    exercise=catalog()[exercise_id];path=Path(submission)
    if path.is_symlink():raise ValueError('练习文件不接受符号链接')
    path=path.resolve()
    allowed=[(PROJECT/'exercises'/exercise_id).resolve(),(ROOT/'.local/student-submissions').resolve()]
    if not any(path.is_relative_to(root) for root in allowed):raise PermissionError('仅运行随课练习或操作者指定的本地提交目录')
    if path.suffix!='.py' or path.stat().st_size>16000:raise ValueError('只执行 16 KB 以内的 Python 练习')
    source=path.read_bytes();spec_hash=hashlib.sha256(CATALOG.read_bytes()).hexdigest()
    with tempfile.TemporaryDirectory() as workspace:
        # 不将模型凭据传入子进程。隔离模式/超时不是操作系统沙箱。
        try:
            completed=subprocess.run([sys.executable, '-X', 'utf8','-I','-S',str(PROJECT/'src/exercise_worker.py'),str(path)],
                input=json.dumps({'tests':exercise['tests']}),text=True,capture_output=True,
                cwd=workspace,env={},timeout=4, encoding='utf-8')
            if completed.returncode!=0:result={'passed':False,'tests':[],'execution_error':'process_exit'}
            else:result=json.loads(completed.stdout)
        except subprocess.TimeoutExpired:result={'passed':False,'tests':[],'execution_error':'timeout'}
    return {'attempt_id':uuid.uuid4().hex,'exercise_id':exercise_id,'source_sha256':hashlib.sha256(source).hexdigest(),
        'catalog_sha256':spec_hash,'recorded_at':datetime.now(timezone.utc).isoformat(),
        'execution':'actual_python_subprocess','result':result}

class LearningStore:
    """仅本机教学用；learner_id 是演示别名，不是已实现完整账号鉴权。"""
    def __init__(self,path):
        path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
        self.db=sqlite3.connect(path)
        self.db.executescript('''CREATE TABLE IF NOT EXISTS lessons(
            id TEXT PRIMARY KEY, learner TEXT, corpus_version TEXT, exercise TEXT, hint_level INTEGER, status TEXT);
            CREATE TABLE IF NOT EXISTS attempts(id TEXT PRIMARY KEY,lesson_id TEXT,body TEXT);
            CREATE TABLE IF NOT EXISTS hint_receipts(lesson_id TEXT,request_id TEXT,body TEXT,PRIMARY KEY(lesson_id,request_id));''')
    def create(self,learner,corpus_version,exercise_id):
        if not re.fullmatch(r'[a-zA-Z0-9_-]{1,40}',learner):raise ValueError('学习者使用简短演示别名')
        if exercise_id not in catalog():raise ValueError('未知练习')
        lesson_id=uuid.uuid4().hex
        with self.db:self.db.execute('INSERT INTO lessons VALUES(?,?,?,?,?,?)',
            (lesson_id,learner,corpus_version,exercise_id,0,'not_attempted'))
        return lesson_id
    def read(self,lesson_id,learner,corpus_version):
        row=self.db.execute('SELECT * FROM lessons WHERE id=? AND learner=?',(lesson_id,learner)).fetchone()
        if row is None:raise KeyError('学习记录不存在或别名不匹配')
        if row[2]!=corpus_version:raise ValueError('资料版本变化，先重新核查练习')
        attempts=[json.loads(r[0]) for r in self.db.execute('SELECT body FROM attempts WHERE lesson_id=? ORDER BY rowid',(lesson_id,))]
        return {'lesson_id':row[0],'learner':row[1],'corpus_version':row[2],'exercise_id':row[3],
                'hint_level':row[4],'status':row[5],'attempts':attempts}
    def add_attempt(self,lesson_id,learner,corpus_version,attempt):
        state=self.read(lesson_id,learner,corpus_version)
        if attempt['exercise_id']!=state['exercise_id']:raise ValueError('练习不匹配')
        if attempt['catalog_sha256']!=hashlib.sha256(CATALOG.read_bytes()).hexdigest():raise ValueError('题目版本变化')
        status='tests_passed' if attempt['result']['passed'] else 'needs_work'
        if attempt['result'].get('execution_error'):status='execution_error'
        with self.db:
            self.db.execute('INSERT INTO attempts VALUES(?,?,?)',(attempt['attempt_id'],lesson_id,json.dumps(attempt,ensure_ascii=False)))
            self.db.execute('UPDATE lessons SET status=? WHERE id=?',(status,lesson_id))
        return self.read(lesson_id,learner,corpus_version)
    def next_hint(self,lesson_id,learner,corpus_version,request_id):
        state=self.read(lesson_id,learner,corpus_version)
        if state['status']=='not_attempted':return {'level':0,'hint':'先写一次预测或尝试，再选择需要帮助的地方。'}
        if state['status']=='tests_passed':return {'level':state['hint_level'],'hint':'随课测试已通过。请解释边界条件，再用一组新输入自检；这还不是掌握证明。'}
        if state['status']=='execution_error':return {'level':0,'hint':'先检查运行错误或超时，再判断算法结果；现在不能说测试全部通过。'}
        if not isinstance(request_id,str) or not re.fullmatch(r'[a-zA-Z0-9_-]{1,80}',request_id):raise ValueError('提示请求标识不合法')
        # 同一个显式请求即使重复执行，也不能越过一级提示；事务内检查并写回。
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            receipt=self.db.execute('SELECT body FROM hint_receipts WHERE lesson_id=? AND request_id=?',(lesson_id,request_id)).fetchone()
            if receipt:return json.loads(receipt[0])
            current=self.db.execute('SELECT hint_level FROM lessons WHERE id=?',(lesson_id,)).fetchone()[0]
            hints=catalog()[state['exercise_id']]['hints'];level=min(current+1,len(hints))
            result={'level':level,'hint':hints[level-1],'scope':'只提供当前一级提示，不返回完整参考实现'}
            self.db.execute('UPDATE lessons SET hint_level=? WHERE id=?',(level,lesson_id))
            self.db.execute('INSERT INTO hint_receipts VALUES(?,?,?)',(lesson_id,request_id,json.dumps(result,ensure_ascii=False)))
        return result
    def close(self):self.db.close()

def verified_feedback(state,hint=None):
    """学生首先看到程序生成的实测摘要；模型补充建议另列为待核验内容。"""
    if not state['attempts']:return {'status':'not_attempted','message':'先完成一次尝试。'}
    result=state['attempts'][-1]['result'];tests=result['tests']
    if result.get('execution_error'):return {'status':'execution_error','message':'执行未完成，先排查错误。','error_type':result['execution_error']}
    failed=[t['id'] for t in tests if not t['passed']]
    message=f"随课用例 {len(tests)-len(failed)}/{len(tests)} 通过。"
    if not failed:message+='这不等于已经掌握；请解释一个边界并尝试新输入。'
    return {'status':state['status'],'message':message,'failed_test_ids':failed,
            'hint':hint.get('hint') if hint else None,'model_advice':'需对照上述实测记录核验'}
