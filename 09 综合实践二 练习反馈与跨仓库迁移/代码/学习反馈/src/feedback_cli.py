"""明确选择可信本地练习，保存实测结果；默认不调用模型。"""
from pathlib import Path
import sys
ROOT_FOR_IMPORT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT_FOR_IMPORT / '08 综合实践一 资料与仓库导读/代码/学习助手/src'))

import argparse,json
from exercise_lab import ROOT,PROJECT,LearningStore,run_exercise,catalog,verified_feedback
from corpus import Corpus

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--db',required=True);p.add_argument('--learner',default='student-a')
    p.add_argument('--exercise',choices=sorted(catalog()),required=True)
    p.add_argument('--lesson-id');p.add_argument('--submission');p.add_argument('--hint-request')
    a=p.parse_args();path=__import__('pathlib').Path(a.db).resolve()
    if not path.is_relative_to(ROOT/'.local/student-runs'):raise ValueError('学习数据库应放在 .local/student-runs')
    version=Corpus(ROOT/'08 综合实践一 资料与仓库导读/代码/学习助手/fixtures'/catalog()[a.exercise]['corpus']).fingerprint
    store=LearningStore(path)
    try:
        lesson=a.lesson_id or store.create(a.learner,version,a.exercise)
        state=store.read(lesson,a.learner,version)
        if state['exercise_id']!=a.exercise:raise ValueError('练习与已有学习记录不符')
        if a.submission:store.add_attempt(lesson,a.learner,version,run_exercise(a.exercise,a.submission))
        hint=store.next_hint(lesson,a.learner,version,a.hint_request) if a.hint_request else None
        state=store.read(lesson,a.learner,version)
        print(json.dumps({'state':state,'hint':hint,'feedback':verified_feedback(state,hint)},ensure_ascii=False))
    finally:store.close()
if __name__=='__main__':main()
