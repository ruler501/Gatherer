from gatherer import get_card

for i in range(1, 416917):
    card = get_card(i)
    if card is not None:
        print(card)
