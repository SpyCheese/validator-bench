import base64
from config import *

GLOBAL_CONFIG_TEMPLATE = """
{
  "@type": "config.global",
  "dht": {
    "@type": "dht.config.global",
    "k": 3,
    "a": 3,
    "static_nodes": {
      "@type": "dht.nodes",
      "nodes": []
    }
  },
  "validator": {
    "@type": "validator.config.global",
    "zero_state": {
      "workchain": -1,
      "shard": -9223372036854775808,
      "seqno": 0,
      "root_hash": "",
      "file_hash": ""
    },
    "init_block": {
      "workchain": -1,
      "shard": -9223372036854775808,
      "seqno": 0,
      "root_hash": "",
      "file_hash": ""
    }
  }
}
"""

GLOBAL_CONFIG_FILENAME = "my.global.config.json"


def init(zerostate_rhash_hex: str, zerostate_fhash_hex: str):
    cfg = json.loads(GLOBAL_CONFIG_TEMPLATE)
    block_id = cfg["validator"]["zero_state"]
    block_id["root_hash"] = str(base64.b64encode(bytes.fromhex(zerostate_rhash_hex)), "utf-8")
    block_id["file_hash"] = str(base64.b64encode(bytes.fromhex(zerostate_fhash_hex)), "utf-8")
    cfg["validator"]["init_block"] = block_id
    with open(GLOBAL_CONFIG_FILENAME, "w") as f:
        print(json.dumps(cfg, indent=2), file=f)


def add_liteserver(key_base64: str):
    with open(GLOBAL_CONFIG_FILENAME, "r") as f:
        cfg = json.loads(f.read())
    cfg["liteservers"] = [
        {
            "id": {
                "@type": "pub.ed25519",
                "key": key_base64
            },
            "ip": 2130706433,  # 127.0.0.1
            "port": str(LITESERVER_PORT)
        }
    ]
    with open(GLOBAL_CONFIG_FILENAME, "w") as f:
        print(json.dumps(cfg, indent=2), file=f)
