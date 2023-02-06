from rq import Connection, Worker

from helpers.redis_commands import conn as redis_conn


if __name__ == '__main__':
    with Connection(redis_conn):
        worker = Worker(['default'])
        worker.work()
