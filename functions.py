import emoji


def emojies(num):
    one = emoji.emojize(':keycap_1:')
    two = emoji.emojize(':keycap_2:')
    three = emoji.emojize(':keycap_3:')
    four = emoji.emojize(':keycap_4:')
    five = emoji.emojize(':keycap_5:')
    six = emoji.emojize(':keycap_6:')
    seven = emoji.emojize(':keycap_7:')
    eight = emoji.emojize(':keycap_8:')
    nine = emoji.emojize(':keycap_9:')
    ten = emoji.emojize(':keycap_10:')
    zero = emoji.emojize(':keycap_0:')
    em = {0: zero, 1: one, 2: two, 3: three, 4: four,
          5: five, 6: six, 7: seven, 8: eight, 9: nine, 10: ten}
    return em.get(num)
