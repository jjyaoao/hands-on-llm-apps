"""学习反馈环境：读取实测结果，一次用户请求至多推进一级提示。"""
from pathlib import Path
import sys
ROOT_FOR_IMPORT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT_FOR_IMPORT / '08 综合实践一 资料与仓库导读/代码/学习助手/src'))

import hashlib,json
from study_runtime import StudyRuntime
from exercise_lab import catalog,CATALOG,LearningStore
from agent_lab import declaration

class TutorRuntime(StudyRuntime):
    allowed={'read_learning_state','request_next_hint'}
    def __init__(self,directory,learning_store,lesson_id,learner,hint_request=None):
        super().__init__(directory)
        self.learning,self.lesson_id,self.learner=learning_store,lesson_id,learner
        self.hint_request=hint_request
        self.learning_state()  # 创建环境时先核对学生与资料版本。
        self.identity+=':lesson:'+lesson_id+':learner:'+learner+':hint:'+str(hint_request)
    def learning_state(self):
        return self.learning.read(self.lesson_id,self.learner,self.corpus.fingerprint)
    def snapshot(self):
        result=super().snapshot();state=self.learning_state()
        result['exercise/catalog']=hashlib.sha256(CATALOG.read_bytes()).hexdigest()
        result['learning/attempts']=hashlib.sha256(json.dumps(state['attempts'],sort_keys=True).encode()).hexdigest()
        return result
    def instructions(self,library):
        state=self.learning_state();exercise=catalog()[state['exercise_id']]
        return ('你是面向大学初学者的练习反馈助手。当前阶段只处理宿主绑定的练习。'
            '先读取本次学习记录；只依据实际测试说明状态。'
            '测试通过只能说随课用例通过，不能宣称已经掌握。若有提示请求，最多调用一次 request_next_hint；'
            '给当前一级提示，不给参考实现，不替学生修改或执行代码。200字以内，让学生自己尝试。'
            '\n练习要求：'+exercise['prompt']+'\n本轮是否由学生明确请求提示：'+str(self.hint_request is not None))
    def declarations(self,tools):
        # 反馈阶段只暴露所需动作；导读阶段仍由 StudyRuntime 提供资料工具。
        return [
            declaration('read_learning_state','读取宿主绑定的当前练习、最新实测结果与提示级别。',{},[]),
            declaration('request_next_hint','学生明确请求后，取得当前一级提示；重复调用返回同一提示。',{},[])]
    async def execute(self,client,library,name,args,remote_names):
        if name in {'read_learning_state','request_next_hint'}:
            if args!={}:raise ValueError('学习工具不接受学生 ID、路径或代码参数')
            if name=='read_learning_state':
                state=self.learning_state()
                return {'ok':True,'data':{k:v for k,v in state.items() if k!='attempts'}|
                    {'latest_attempt':state['attempts'][-1] if state['attempts'] else None}}
            if self.hint_request is None:raise PermissionError('本轮没有学生提示请求')
            return {'ok':True,'data':self.learning.next_hint(self.lesson_id,self.learner,self.corpus.fingerprint,self.hint_request)}
        return await super().execute(client,library,name,args,remote_names)
