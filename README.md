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
  "node_start_time": 1712653520.5234292,
  "validation_start_time": 1712653595.6053903,
  "sharding_end_time": 1712653675.797849,
  "spam_start_time": 1712653680.8639894,
  "benchmark_start_time": 1712653800.9694803,
  "benchmark_end_time": 1712654100.9694803,
  "queue_sizes": [
    { "time": 1712653800.9981272, "size": 62899 },
    { "time": 1712653831.4748147, "size": 76872 },
    { "time": 1712653861.6970887, "size": 90692 },
    { "time": 1712653893.3904788, "size": 103214 },
    { "time": 1712653924.0423036, "size": 115894 },
    { "time": 1712653954.6987941, "size": 126731 },
    { "time": 1712653985.6303236, "size": 138799 },
    { "time": 1712654015.8613963, "size": 147207 },
    { "time": 1712654046.3349829, "size": 148836 },
    { "time": 1712654076.4971857, "size": 161187 },
    { "time": 1712654101.7564032, "size": 167854 }
  ],
  "stats_base": {
    "total": { "tps": 407.71, "bpm": 65.2 },
    "minutes": [
      { "tps": 530.6666666666666, "bpm": 84.0 },
      { "tps": 455.0833333333333, "bpm": 72.0 },
      { "tps": 454.48333333333335, "bpm": 72.0 },
      { "tps": 286.3, "bpm": 48.0 },
      { "tps": 312.01666666666665, "bpm": 50.0 }
    ]
  },
  "stats_mc": {
    "total": { "tps": 0.95, "bpm": 11.4 },
    "minutes": [
      { "tps": 0.9166666666666666, "bpm": 11.0 },
      { "tps": 0.9166666666666666, "bpm": 11.0 },
      { "tps": 1.1666666666666667, "bpm": 14.0 },
      { "tps": 0.8333333333333334, "bpm": 10.0 },
      { "tps": 0.9166666666666666, "bpm": 11.0 }
    ]
  }
}
```

* Stats are calculated between `benchmark_start_time` and `benchmark_end_time`.
* `stats_base` and `stats_mc` are stats for basechain and masterchain.
  * `total` are stats for the whole time period, `minutes` are stats for each minute of the benchmark.
  * `tps` - transactions per second, `bpm` - blocks per minute.
* `queue_sizes` - the total size of outbound message queues in basechain (calculated every 30s).