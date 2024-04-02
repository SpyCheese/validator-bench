# Validator benchmark

This tool creates a private TON network with single validator, runs transactions on it and outputs stats.

Usage:

```
./validator-bench.py config.json
```

## Configuration

Edit `config.json` file:

```json
{
  "ton_bin": "/usr/bin/ton/",
  "fift_lib_path": "/usr/src/ton/crypto/fift/lib/",
  "smartcont_path": "/usr/src/ton/crypto/smartcont/",
  "work_dir": "/var/validator-benchmark/",
  "node": {
    "adnl_port": 61001,
    "liteserver_port": 61002,
    "console_port": 61003,
    "threads": 8,
    "verbosity": 1,
    "celldb_compress_depth": 0
  },
  "blockchain": {
    "split": 3,
    "lim_mul": 1.0
  },
  "benchmark": {
    "sharding_timeout": 300.0,
    "max_retranslators": 1024,
    "spam_chains": 20,
    "spam_split_hops": 7,
    "spam_preference": 1.0,
    "spam_preliminary_wait": 120.0,
    "benchmark_duration": 600.0
  }
}
```

1. `ton_bin`, `fift_lib_path`, `smartcont_path` - set to your TON installation directories.
2. `work_dir` - directory for the database. *Note that the script wipes this directory on startup*.
3. `node`: set `threads`, `verbosity`, `celldb_compress_depth` to desired values.
4. `blockchain`:
    1. `split` - min and max split for the basechain. The number of shards will be `2^split`.
    2. `lim_mul` - multiplier for the block limits relative to the standard limits (i.e. `lim_mul=1` means the limits
       are the same as in mainnet, `lim_mul=2` - two times larger).
5. `benchmark` - see below.

## Benchmark

The benchmark runs in the following way:

1. Create a new blockchain with a single validator. Start validator-engine.
2. Wait for the node to start validating, wait for `2^split` shards. Timeout for this step is `sharding_timeout`
   seconds.
3. Start transactions.
    1. Transactions are executed in basechain.
    2. Transactions are executed on a special smart-contract (retranslator).
    3. The number of retranslators is `max_retranslators` (up to `2^64`).
    4. `spam_chains * 2^spam_split_hops` chains of transactions are executed.
    5. `spam_preference` controls the proportion of cross-shard transactions. `1` means that all transactions have
       source and destination in the same shard. `0` means that all destinations are random.
4. Wait for `spam_preliminary_wait` seconds. This is required to skip the period with low TPS.
5. Record benchmark start time and wait for `benchmark duration` seconds.
6. Compute final stats.

## Results
At the end, the script outputs the results to stdout.

```json
{
  "node_start_time": 1711635420.6139314,
  "validation_start_time": 1711635484.7034965,
  "sharding_end_time": 1711635579.9333284,
  "spam_start_time": 1711635585.0027502,
  "benchmark_start_time": 1711635705.109025,
  "benchmark_end_time": 1711636305.109025,
  "stats_base": {
    "total": { "tps": 932.0933333333334, "bpm": 180.3 },
    "minutes": [
      { "tps": 859.7833333333333, "bpm": 166.0 },
      { "tps": 982.9833333333333, "bpm": 190.0 },
      { "tps": 977.7666666666667, "bpm": 189.0 },
      { "tps": 982.6666666666666, "bpm": 190.0 },
      { "tps": 883.6, "bpm": 171.0 },
      { "tps": 940.65, "bpm": 182.0 },
      { "tps": 961.0, "bpm": 186.0 },
      { "tps": 950.5166666666667, "bpm": 184.0 },
      { "tps": 971.05, "bpm": 188.0 },
      { "tps": 810.9166666666666, "bpm": 157.0 }
    ]
  },
  "stats_mc": {
    "total": { "tps": 2.15, "bpm": 25.8 },
    "minutes": [
      { "tps": 2.0833333333333335, "bpm": 25.0 },
      { "tps": 2.1666666666666665, "bpm": 26.0 },
      { "tps": 2.25, "bpm": 27.0 },
      { "tps": 2.25, "bpm": 27.0 },
      { "tps": 2.0833333333333335, "bpm": 25.0 },
      { "tps": 2.1666666666666665, "bpm": 26.0 },
      { "tps": 2.1666666666666665, "bpm": 26.0 },
      { "tps": 2.1666666666666665, "bpm": 26.0 },
      { "tps": 2.1666666666666665, "bpm": 26.0 },
      { "tps": 2.0, "bpm": 24.0 }
    ]
  }
}
```

Stats are calculated between `benchmark_start_time` and `benchmark_end_time`.

`stats_base` and `stats_mc` are stats for basechain and masterchain.

`total` are stats for the whole time period, `minutes` are stats for each minute of the benchmark.

`tps` - transactions per second, `bpm` - blocks per minute.