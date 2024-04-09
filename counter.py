import threading

import utils
from config import *


class Counter:
    def __init__(self, duration: float):
        self.duration = duration
        self.blocks = 0
        self.transactions = 0
        self.mutex = threading.Lock()

    def add_block(self, txs: int):
        self.mutex.acquire()
        try:
            self.blocks += 1
            self.transactions += txs
        finally:
            self.mutex.release()

    def to_json(self) -> dict:
        return {
            "tps": self.transactions / self.duration,
            "bpm": self.blocks * 60 / self.duration
        }


class Stats:
    def __init__(self, start_time: float, end_time: float):
        self.start_time = start_time
        self.end_time = end_time
        self.minutes = []
        self.total = Counter(end_time - start_time)
        x1 = start_time
        while x1 < end_time - 30.0:
            x2 = min(end_time, x1 + 60.0)
            self.minutes.append(Counter(x2 - x1))
            x1 = x2

    def add_block(self, timestamp: float, txs: int):
        if timestamp < self.start_time or self.end_time < timestamp:
            return
        self.total.add_block(txs)
        i = int((timestamp - self.start_time) / 60.0)
        if 0 <= i < len(self.minutes):
            self.minutes[i].add_block(txs)

    def to_json(self) -> dict:
        return {
            "total": self.total.to_json(),
            "minutes": [x.to_json() for x in self.minutes]
        }


def get_block_header(block_id) -> tuple[int, str]:
    ts = 0
    prev = ""
    for s in utils.lite_client("gethead " + block_id).split("\n"):
        if s.startswith("block header of"):
            ts = int(s.split()[-5])
        if s.startswith("previous block #1"):
            prev = s.split()[-1]
    assert ts
    assert prev
    return ts, prev


def count_transactions(block_id: str) -> int:
    x = 0
    acc = ""
    lt = ""
    while True:
        for s in utils.lite_client("listblocktrans %s 1000 %s %s" % (block_id, acc, lt)).split("\n"):
            if s.startswith("transaction #"):
                x += 1
                s = s.split()
                acc = s[3]
                lt = s[5]
            elif "end of block transaction list" in s:
                return x


def count_stats_shard(stats: Stats, block_id: str):
    while True:
        ts, prev = get_block_header(block_id)
        if ts < stats.start_time:
            break
        if ts > stats.end_time:
            block_id = prev
            continue
        transactions = count_transactions(block_id)
        stats.add_block(ts, transactions)
        block_id = prev


MAX_THREADS = 4


def count_stats_thread(stats: Stats, shard_blocks: list[str]):
    for x in shard_blocks:
        count_stats_shard(stats, x)


def count_stats(result_json: dict, start_time: float, end_time: float):
    mc_block = ""
    shard_blocks = []
    for s in utils.lite_client("allshards").split("\n"):
        if s.startswith("latest masterchain block known to server is"):
            mc_block = s.split()[7]
        elif s.startswith("shard #"):
            shard_blocks.append(s.split()[3])
    assert mc_block
    master_stats = Stats(start_time, end_time)
    base_stats = Stats(start_time, end_time)

    threads = []
    for i in range(MAX_THREADS):
        cur_shard_blocks = shard_blocks[i::MAX_THREADS]
        if cur_shard_blocks:
            t = threading.Thread(target=count_stats_thread, args=[base_stats, cur_shard_blocks])
            threads.append(t)
            t.start()
    count_stats_shard(master_stats, mc_block)
    for t in threads:
        t.join()

    result_json["stats_base"] = base_stats.to_json()
    result_json["stats_mc"] = master_stats.to_json()


def get_total_queues_size() -> int:
    res = utils.lite_client("msgqueuesizes")
    i = res.find("Outbound message queue sizes:")
    if i == -1:
        raise Exception("Unexpected msgqueuesizes output: " + res)
    total = 0
    for s in res[i:].split("\n"):
        if s.startswith("(0,"):
            total += int(s.split()[1])
    return total
