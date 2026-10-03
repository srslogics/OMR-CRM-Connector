"""Run durable processing separately from the web server: python worker.py."""
import signal
from app import init, work_loop, stop, wake
from storage import close_pool


def shutdown(*_):
    stop.set()
    wake.set()


if __name__ == '__main__':
    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)
    init()
    try:
        work_loop()
    finally:
        close_pool()
