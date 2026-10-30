"""学生明确运行这个自编脚本时才执行；资料导入不会自动运行。"""
from search import search

DOCUMENTS = [
    'An agent reads evidence before answering.',
    'A retrieval score is not a correctness probability.',
    'An agent can use retrieval to find evidence.',
]
if __name__ == '__main__':
    for result in search('agent evidence', DOCUMENTS, top_k=2):
        print(result)
