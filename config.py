import json
import os
import sys

if len(sys.argv) != 2:
    print("Usage: ./validator-bench.py config.json")
    exit(2)

with open(sys.argv[1], "r") as f:
    config_json = json.loads(f.read())

TON_BIN: str = config_json["ton_bin"]

LITE_CLIENT_BIN = os.path.join(TON_BIN, "lite-client/lite-client")
VALIDATOR_ENGINE_BIN = os.path.join(TON_BIN, "validator-engine/validator-engine")
VALIDATOR_CONSOLE_BIN = os.path.join(TON_BIN, "validator-engine-console/validator-engine-console")
GEN_KEY_BIN = os.path.join(TON_BIN, "utils/generate-random-id")
FIFT_BIN = os.path.join(TON_BIN, "crypto/fift")
CREATE_STATE_KEY_BIN = os.path.join(TON_BIN, "crypto/create-state")
FUNC_BIN = os.path.join(TON_BIN, "crypto/func")

WORK_DIR: str = config_json["work_dir"]

os.environ["FIFTPATH"] = config_json["fift_lib_path"] + ":" + config_json["smartcont_path"]
SMARTCONT_PATH = config_json["smartcont_path"]

ADNL_PORT: int = config_json["node"]["adnl_port"]
LITESERVER_PORT: int = config_json["node"]["liteserver_port"]
CONSOLE_PORT: int = config_json["node"]["console_port"]

NODE_FLAGS: list[str] = ["--threads", str(config_json["node"]["threads"]), "--verbosity",
                         str(config_json["node"]["verbosity"])]

SHARDING_TIMEOUT: float = config_json["benchmark"]["sharding_timeout"]
BENCHMARK_DURATION: float = config_json["benchmark"]["benchmark_duration"]
