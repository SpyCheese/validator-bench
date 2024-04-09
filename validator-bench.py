#!/usr/bin/python3
import base64
import logging
import os
import shutil
import time

import counter
import gen_zerostate
import global_config
import spam
import utils
from config import *

result_json = dict()


def prepare_dirs():
    logging.info("Working dir is " + WORK_DIR)
    utils.run_cmd(["rm", "-rf", "--", WORK_DIR])
    utils.run_cmd(["mkdir", "-p", "--", WORK_DIR])
    os.chdir(WORK_DIR)
    utils.run_cmd(["mkdir", "-p", "--", "ton-work/db/keyring/"])
    utils.run_cmd(["mkdir", "-p", "--", "ton-work/db/static/"])
    utils.run_cmd(["mkdir", "-p", "--", "ton-work/logs/"])


val_id_hex = ""


def prepare_net():
    logging.info("Generating zerostate")
    global val_id_hex
    val_id_hex, _ = utils.generate_random_id("keys", "validator-key")
    shutil.copy("validator-key", "ton-work/db/keyring/" + val_id_hex)
    zerostate_rhash_hex, zerostate_fhash_hex, basestate_fhash_hex = gen_zerostate.gen()
    shutil.move("zerostate.boc", "ton-work/db/static/" + zerostate_fhash_hex)
    shutil.move("basestate0.boc", "ton-work/db/static/" + basestate_fhash_hex)
    logging.info("Zerostate root hash = " + zerostate_rhash_hex)
    logging.info("Zerostate file hash = " + zerostate_fhash_hex)
    global_config.init(zerostate_rhash_hex, zerostate_fhash_hex)


def prepare_node():
    validator_version = utils.run_cmd([VALIDATOR_ENGINE_BIN, "--version"]).strip()
    logging.info("Node version: " + validator_version)
    result_json["node_version"] = validator_version.strip()
    logging.info("Running validator-engine for the first time")
    utils.run_cmd([VALIDATOR_ENGINE_BIN, "-C", global_config.GLOBAL_CONFIG_FILENAME, "--db", "ton-work/db/", "--ip",
                   "127.0.0.1:%d" % ADNL_PORT] + get_node_flags(), timeout=3.0)
    logging.info("Initializing validator console")
    server_id_hex, server_id_base64 = utils.generate_random_id("keys", "server")
    _, client_id_base64 = utils.generate_random_id("keys", "client")
    shutil.move("server", "ton-work/db/keyring/" + server_id_hex)
    with open("ton-work/db/config.json", "r") as f:
        cfg = json.loads(f.read())
    cfg["control"] = [{
        "@type": "engine.controlInterface",
        "id": server_id_base64,
        "port": CONSOLE_PORT,
        "allowed": [
            {
                "@type": "engine.controlProcess",
                "id": client_id_base64,
                "permissions": 15
            }
        ]
    }]
    with open("ton-work/db/config.json", "w") as f:
        print(json.dumps(cfg, indent=2), file=f)

    logging.info("Starting preliminary validator run")
    proc = utils.validator_engine()
    time.sleep(1.0)
    now = int(time.time())
    logging.info("Validator key = " + val_id_hex)
    val_adnl_hex = utils.validator_console("newkey").split()[-1]
    logging.info("Validator adnl = " + val_adnl_hex)
    liteserver_id_hex = utils.validator_console("newkey").split()[-1]
    logging.info("Liteserver id = " + liteserver_id_hex)
    liteserver_key_base64 = utils.validator_console("exportpub " + liteserver_id_hex).split()[-1]
    liteserver_key_base64 = str(base64.b64encode(base64.b64decode(liteserver_key_base64)[4:]), "utf-8")
    utils.validator_console("addpermkey %s 0 %d" % (val_id_hex, now + 1000000))
    utils.validator_console("addtempkey %s %s %d" % (val_id_hex, val_id_hex, now + 1000000))
    utils.validator_console("addadnl %s 0" % val_adnl_hex)
    utils.validator_console("addadnl %s 0" % val_id_hex)
    utils.validator_console("addvalidatoraddr %s %s %d" % (val_id_hex, val_adnl_hex, now + 1000000))
    utils.validator_console("addliteserver %d %s" % (LITESERVER_PORT, liteserver_id_hex))
    global_config.add_liteserver(liteserver_key_base64)
    logging.info("Stopping preliminary validator run")
    proc.kill()


def do_benchmark():
    proc = utils.validator_engine()
    logging.info("Running validator-engine, pid=%d" % proc.pid)
    node_start_time = time.time()
    result_json["node_start_time"] = node_start_time

    logging.info("BENCHMARK PHASE 1: Wait for validation to start, wait for basechain to split")
    timeout = node_start_time + SHARDING_TIMEOUT
    while True:
        res = utils.lite_client("last", allow_error=True)
        if "latest masterchain block" in res:
            result_json["validation_start_time"] = time.time()
            logging.info("Validation started")
            break
        if time.time() > timeout:
            raise Exception("Validation did not start (timeout=%.1f)" % SHARDING_TIMEOUT)
        time.sleep(5.0)
    max_shards = 2 ** config_json["blockchain"]["split"]
    logging.info("Waiting for %d shards" % max_shards)
    while True:
        res = utils.lite_client("allshards", allow_error=True)
        shards = res.count("shard #")
        if shards:
            logging.info("Waiting: %d/%d shards" % (shards, max_shards))
            if shards == max_shards:
                result_json["sharding_end_time"] = time.time()
                break
        if time.time() > timeout:
            raise Exception("Validation did not start (timeout=%.1f)" % SHARDING_TIMEOUT)
        time.sleep(5.0)

    logging.info("BENCHMARK PHASE 2: Running transactions")
    retranslator_addr = spam.prepare_retranslator()
    logging.info("Sending TONs to retranslator " + retranslator_addr)
    utils.lite_client("sendfile wallet-query.boc")
    timeout = time.time() + 60.0
    while True:
        time.sleep(5.0)
        res = utils.lite_client("getaccount " + retranslator_addr, allow_error=True)
        if "account balance is" in res:
            break
        if time.time() > timeout:
            raise Exception("Retranslator did not get TONs (timeout=%.1f)" % 60.0)
    result_json["spam_start_time"] = time.time()
    logging.info("Starting transactions, waiting for %.1fs" % config_json["benchmark"]["spam_preliminary_wait"])
    utils.lite_client("sendfile query-retranslator.boc")
    time.sleep(config_json["benchmark"]["spam_preliminary_wait"])

    logging.info("Benchmark started, waiting for %.1fs" % BENCHMARK_DURATION)
    bench_start = time.time()
    result_json["benchmark_start_time"] = bench_start
    bench_end = bench_start + BENCHMARK_DURATION
    result_json["benchmark_end_time"] = bench_end

    result_json["queue_sizes"] = []
    done = False
    while True:
        queue_size = counter.get_total_queues_size()
        logging.info("Current msg queue size: %d" % queue_size)
        now = time.time()
        result_json["queue_sizes"].append({"time": now, "size": queue_size})
        if done:
            break
        remaining = max(0.0, bench_end - now)
        if remaining < 30.0:
            time.sleep(remaining)
            done = True
        else:
            time.sleep(30.0)

    logging.info("Benchmark ended")
    logging.info("BENCHMARK PHASE 3: Collecting results")
    logging.info("Wait for 30s")
    time.sleep(30.0)
    logging.info("Stopping transactions")
    spam.stop_spam()
    logging.info("Computing stats")
    counter.count_stats(result_json, bench_start, bench_end)


def run():
    logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s', level=logging.INFO)
    prepare_dirs()
    prepare_net()
    prepare_node()

    do_benchmark()

    logging.info("Done. Printing results to stdout")
    logging.info("Validator logs are available in " + os.path.join(WORK_DIR, "ton-work/logs/"))
    print(json.dumps(result_json, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    run()
