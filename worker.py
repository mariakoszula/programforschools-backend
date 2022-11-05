from rq import Connection, Worker
import redis
from os import environ
from helpers.config_parser import config_parser

redis_url = environ.get('REDIS_URL', config_parser.get('Redis', 'url'))
conn = redis.from_url(redis_url)

if __name__ == '__main__':
    with Connection(conn):
        worker = Worker(['default'])
        worker.work()
