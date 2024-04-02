import atexit
import logging
import subprocess
import typing

import global_config
from config import *


def run_cmd(cmd: typing.List[str], timeout: float = 10.0, stdin: typing.Optional[str] = None,
            allow_error: bool = False) -> str:
    logging.debug("Running command `%s`" % " ".join(cmd))
    if stdin is not None:
        stdin = stdin.encode("utf-8")
    try:
        res = subprocess.run(cmd, capture_output=True, timeout=timeout, input=stdin)
    except subprocess.TimeoutExpired:
        if allow_error:
            return "Timeout"
        else:
            raise
    stdout = str(res.stdout, "utf-8")
    stderr = str(res.stderr, "utf-8")
    if res.returncode == 0 or allow_error:
        return stdout
    raise Exception("Error running %s:\n%s\n%s" % (" ".join(cmd), stderr, stdout))


def generate_random_id(mode: str, filename: str) -> tuple[str, str]:
    res = run_cmd([GEN_KEY_BIN, "-m", mode, "-n", filename])
    id_hex, id_base64 = res.split()
    return id_hex, id_base64


def create_state(code: str):
    return run_cmd([CREATE_STATE_KEY_BIN, "-i"], stdin=code)


def create_state_script(cmd: list[str]):
    return run_cmd([CREATE_STATE_KEY_BIN, "-s"] + cmd)


def fift(code: str):
    return run_cmd([FIFT_BIN, "-s"], stdin=code)


def fift_script(cmd: list[str]):
    return run_cmd([FIFT_BIN, "-s"] + cmd)


def validator_console(cmd: str) -> str:
    return run_cmd(
        [VALIDATOR_CONSOLE_BIN, "-v", "0", "-a", "127.0.0.1:%d" % CONSOLE_PORT, "-k", "client", "-p", "server.pub",
         "-r", "-c", cmd])


def validator_engine() -> subprocess.Popen:
    cmd = [VALIDATOR_ENGINE_BIN, "-C", global_config.GLOBAL_CONFIG_FILENAME, "--db", "ton-work/db/", "--logname",
           "ton-work/logs/node.log"] + NODE_FLAGS
    logging.info("Running node: `%s`" % " ".join(cmd))
    proc = subprocess.Popen(cmd)
    atexit.register(lambda: proc.kill())
    return proc


def lite_client(cmd: str, allow_error: bool = False, retries: int = 10) -> str:
    while True:
        try:
            return run_cmd(
                [LITE_CLIENT_BIN, "-v", "0", "-C", global_config.GLOBAL_CONFIG_FILENAME, "-r", "-c", cmd],
                allow_error=allow_error, timeout=10.0)
        except Exception as e:
            if retries == 0:
                raise
            logging.info("lite-client `%s` error, retrying: %s" % (cmd, e))
            retries -= 1
