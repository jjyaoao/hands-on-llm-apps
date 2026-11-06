"""独立 Python 进程执行操作者明确选择的本地练习。不是不可信代码沙箱。"""
import contextlib,copy,importlib.util,io,json,sys

def typed_equal(a,b):
    if type(a) is not type(b):return False
    if isinstance(b,dict):return a.keys()==b.keys() and all(typed_equal(a[k],v) for k,v in b.items())
    if isinstance(b,list):return len(a)==len(b) and all(typed_equal(x,y) for x,y in zip(a,b))
    return a==b

def run(path,tests):
    captured=io.StringIO();rows=[]
    with contextlib.redirect_stdout(captured),contextlib.redirect_stderr(captured):
        spec=importlib.util.spec_from_file_location('course_submission',path)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        for case in tests:
            try:
                actual=module.solve(*copy.deepcopy(case['args']))
                # 本练习约定 JSON 可表示的输出；不偷偷转字符串当作正确类型。
                json.dumps(actual,allow_nan=False)
                passed='expected' in case and typed_equal(actual,case['expected'])
                row={'id':case['id'],'passed':passed,'actual':actual}
            except Exception as error:
                row={'id':case['id'],'passed':type(error).__name__==case.get('expected_exception'),
                     'exception_type':type(error).__name__}
            rows.append(row)
    return {'tests':rows,'passed':all(r['passed'] for r in rows),'stdout_preview':captured.getvalue()[:1000]}

if __name__=='__main__':
    try:
        request=json.load(sys.stdin);result=run(sys.argv[1],request['tests'])
        print(json.dumps(result,ensure_ascii=False,allow_nan=False))
    except Exception as error:
        print(json.dumps({'passed':False,'tests':[],'execution_error':type(error).__name__}))
