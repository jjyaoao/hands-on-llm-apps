"""自编复习卡片；假设日期字符串事先满足 YYYY-MM-DD 格式。"""
def due_cards(cards, today, limit=3):
    if type(limit) is not int or limit < 1:
        raise ValueError('limit 必须是正整数')
    due = [card for card in cards if card['due'] <= today]
    return sorted(due, key=lambda card: card['due'])[:limit]
