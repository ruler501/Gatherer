import sqlite3

import mtgsdk


def main(dest="cards.sqlite3", cache="cards.pickle"):
    cards = []
    cards = mtgsdk.Card.where(language="English").all()
    conn = sqlite3.connect(dest)
    c = conn.cursor()
    create_command = "CREATE TABLE cards ("
    vars_dict = vars(cards[0])
    vars_list = list(vars_dict.keys())
    sql = 'INSERT INTO cards('
    for var in vars_list:
        print(var, vars_dict[var])
        create_command += '\n"' + var + '"'
        try:
            int(vars_dict[var])
            create_command += ' int'
        except:
            create_command += ' text'
        # if var == 'multiverse_id':
        #     create_command += ' PRIMARY KEY'
        create_command += ','
        sql += '"' + var + '",'
    sql = sql[:-1]
    sql += ')\nVALUES(' + '?,' * (len(vars_list) - 1) + '?)'
    create_command = create_command[:-1]
    create_command += '\n);'
    print(create_command)
    c.execute(create_command)
    conn.commit()
    print(vars_list)
    print()
    print(sql)
    print(len(cards))
    card_lists = [list(str(vars(card)[var]) for var in vars_list) for card in cards]
    c.executemany(sql, card_lists)
    conn.commit()
    conn.close()


main()
