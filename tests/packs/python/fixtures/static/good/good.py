from pathlib import Path


def read_file(path: str) -> str:
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def query(cursor, user_id: int):
    return cursor.execute("select * from users where id = ?", (user_id,))
