"""课程教学修订示例：先独立尝试，再阅读。"""
def solve(items, limit):
    if type(limit) is not int or limit < 1:
        raise ValueError('limit 必须是正整数')
    positive = [item for item in items if item['score'] > 0]
    # Python 排序稳定；同分元素的原始顺序保留。
    ordered = sorted(positive, key=lambda item: item['score'], reverse=True)
    return ordered[:limit]
