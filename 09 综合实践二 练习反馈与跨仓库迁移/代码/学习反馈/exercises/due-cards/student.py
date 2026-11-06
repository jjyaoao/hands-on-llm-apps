"""练习模板中的边界错误：观察今天到期的卡片是否被漏掉。"""
def solve(cards, today, limit):
    if type(limit) is not int or limit < 1:
        raise ValueError('limit 必须是正整数')
    due = [card for card in cards if card['due'] < today]
    return sorted(due, key=lambda card: card['due'])[:limit]
