"""课程教学修订示例：日期已按题目前提规范化为有效 YYYY-MM-DD 字符串。"""
def solve(cards, today, limit):
    if type(limit) is not int or limit < 1:
        raise ValueError('limit 必须是正整数')
    due = [card for card in cards if card['due'] <= today]
    return sorted(due, key=lambda card: card['due'])[:limit]
