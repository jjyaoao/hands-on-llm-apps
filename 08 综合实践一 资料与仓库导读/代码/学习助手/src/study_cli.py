"""在明确资料范围内运行导读任务，可复用 run_id 继续；默认固定教学动作回放。"""
import argparse,asyncio,json,sys
from pathlib import Path
from study_runtime import StudyRuntime,Harness,citation_check,request_evidence_revision,ROOT
from checkpoint_store import CheckpointStore
from agent_lab import DeepSeekModel,ReplayModel,tool_response,validate_deepseek_model

def demo_model(corpus,state):
    # 固定脚本只验证工具与状态，不代表模型自主规划；数据读取仍然实际执行。
    hit=corpus.search('检索 分数 search',1)['hits'][0];cid=hit['id']
    script=[tool_response('activate','activate_skill',{'name':'study-coach'}),
        tool_response('map','mcp_source_map',{}),
        tool_response('search','mcp_search_corpus',{'query':'检索 分数 search','k':1}),
        tool_response('read','mcp_read_chunk',{'chunk_id':cid}),
        {'role':'assistant','content':f'教学回放：查看这段实际资料，再解释其中一个概念。[{cid}]'}]
    # 已完成模型次数决定下一段回放，不能在不确定模型结果时假装无损恢复。
    return ReplayModel(script[state['turns']:])

async def run(args):
    db=Path(args.db).resolve();db.relative_to(ROOT/'.local/student-runs')
    runtime=StudyRuntime(args.corpus);store=CheckpointStore(db)
    try:
        h=Harness(store,args.run_id,db.with_suffix('.jsonl'),runtime=runtime) if args.run_id else Harness.create(
            store,args.goal,db.with_suffix('.jsonl'),max_turns=7,max_tools=12,context_chars=24000,runtime=runtime)
        if args.revise_evidence:request_evidence_revision(h)
        if args.mode=='deepseek':
            selected,available=validate_deepseek_model()
            print('本次选择的模型:',selected)
            print('当前账号可用模型:',available)
            model=DeepSeekModel(selected)
        else:model=demo_model(runtime.corpus,h.state)
        state=await h.drive(model,max_steps=args.steps)
        artifacts=[{**a,'body':store.read_artifact(h.run_id,a['id'])} for a in state['artifacts']]
        checked=citation_check(state['answer'],artifacts,runtime.corpus)
        if state['status']=='final_answer' and not checked['all_citations_read']:
            h.stop('citation_review_required');state=h.state
        return {'run_id':h.run_id,'state':state,'artifacts':artifacts,
            'citations':checked,
            'source_map':runtime.corpus.map(),'model_kind':args.mode}
    finally:store.close()

def main():
    p=argparse.ArgumentParser();p.add_argument('--corpus',required=True);p.add_argument('--db',required=True)
    group=p.add_mutually_exclusive_group(required=True);group.add_argument('--run-id');group.add_argument('--goal')
    p.add_argument('--revise-evidence',action='store_true')
    p.add_argument('--mode',choices=['replay','deepseek'],default='replay');p.add_argument('--steps',type=int,default=50)
    args=p.parse_args();print(json.dumps(asyncio.run(run(args)),ensure_ascii=False,indent=2))
if __name__=='__main__':main()
