"""课堂自编关键词检索器：小写匹配、零分过滤、稳定排序。"""
def search(question, documents, top_k=2):
    if type(top_k) is not int or top_k < 1:
        raise ValueError('top_k 必须是正整数')
    words = set(question.lower().split())
    scored = []
    for index, text in enumerate(documents):
        score = sum(word in text.lower() for word in words)
        if score > 0:
            scored.append((score, index, text))
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [{'text':text,'score':score} for score, _, text in scored[:top_k]]
