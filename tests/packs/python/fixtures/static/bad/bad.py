def bare():
    try:
        work()
    except:
        pass


def swallowed():
    try:
        work()
    except Exception:
        pass


def mutable(items=[]):
    return items


def sql(cursor, value):
    query = f"select * from users where name = '{value}'"
    return cursor.execute(query)


def secret():
    api_token = "abcdefgh1234"
    return api_token


def resource(path):
    return open(path)


def output(value):
    print(value)
