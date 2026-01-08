from db import get_db_cursor

def main():
    with get_db_cursor(commit=True) as cur:
        cur.execute("SELECT pg_get_serial_sequence('item', 'item_id') AS seq;")
        seq = cur.fetchone()["seq"]
        if not seq:
            raise Exception("Nem találtam sequence-t az item.item_id-hoz. Lehet, hogy nem SERIAL/IDENTITY.")

        cur.execute("SELECT COALESCE(MAX(item_id), 0) AS mx FROM item;")
        mx = int(cur.fetchone()["mx"])

        cur.execute("SELECT setval(%s, %s);", (seq, mx))

        cur.execute("SELECT nextval(%s) AS next;", (seq,))
        nxt = int(cur.fetchone()["next"])

        print("OK")
        print("sequence:", seq)
        print("max(item_id):", mx)
        print("nextval after fix:", nxt)

if __name__ == "__main__":
    main()
