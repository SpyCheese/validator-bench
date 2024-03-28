import utils
from config import *

RETRANSLATOR_SOURCE_TEMPLATE = """
{-
  _# id:uint16 seqno:uint32 public_key:uint256 code:^Cell = Storage;
-}

const workchain = 0;
const max_retranslators = {{max_retranslators}};
const preference_base = 65535;
const SPAM_CONFIG = -137;

int get_max_shard_depth() inline {
    slice cs = config_param(12).begin_parse();
    cell dict = cs~load_dict();
    (cs, _) = dict.udict_get?(32, 0); 
    cs~skip_bits(6 * 8);
    return cs.preload_uint(8);
}

(int, int, int, cell) load_data () inline {
  slice ds = get_data().begin_parse();
  return (ds~load_uint(16), ds~load_uint(32), ds~load_uint(256), ds.preload_ref());
}

cell pack_data(int id, int seqno, int public_key, cell code) inline {
  return begin_cell()
                     .store_uint(id, 16)
                     .store_uint(seqno, 32)
                     .store_uint(public_key, 256)
                     .store_ref(code)
         .end_cell();
}

cell calc_state_init(int id, int public_key, cell code) inline {
  return begin_cell()
          .store_uint(0,2)
          .store_dict(code)
          .store_dict(pack_data(id, 0, public_key, code))
          .store_uint(0,1)
         .end_cell();
}

slice calc_address(cell init_state) inline {
  return begin_cell().store_uint(4, 3)
                     .store_int(workchain, 8)
                     .store_uint(
                       cell_hash(init_state), 256)
                     .end_cell()
                     .begin_parse();
}

() retranslate(int preference, int remaining_hops, int split_hops, int id, int public_key, cell code, slice payload,
               int amount) impure {
  int next_hop = id; ;; send itself by default
  randomize_lt();
  if( amount | ((random() % preference_base) >= preference)) {
    next_hop = random() % max_retranslators;
  } else {
    int max_shard_depth = get_max_shard_depth();
    (_, int my_addr) = parse_std_addr(my_address());
    int my_shard = my_addr >> (256 - max_shard_depth);
    int not_found? = true;
    int iters = 5;
    while not_found? & (iters > 0) {
      iters -= 1;
      int next_hop' = random() % max_retranslators;
      cell next_hop_initstate = calc_state_init(next_hop', public_key, code);
      int next_hop_shard = cell_hash(next_hop_initstate) >> (256 - max_shard_depth);
      if (my_shard == next_hop_shard) {
        not_found? = false;
        next_hop = next_hop';
      }
    }
  }
  cell next_hop_initstate = calc_state_init(next_hop, public_key, code);
  slice next_hop_address = calc_address(next_hop_initstate);
  var msg = begin_cell()
    .store_uint(0x10, 6)
    .store_slice(next_hop_address)
    .store_coins(amount > 0 ? amount : 0)
    .store_uint(4 + 2 + 1, 1 + 4 + 4 + 64 + 32 + 1 + 1 + 1)
    .store_ref(next_hop_initstate);
  var msg_body = begin_cell()
    .store_uint(id, 16)
    .store_uint(remaining_hops, 16)
    .store_uint(split_hops, 8)
    .store_uint(preference, 16)
    .store_slice(payload)
    .end_cell();
  msg = msg.store_ref(msg_body);
  send_raw_message(msg.end_cell(), amount ? ( amount > 0 ? 3 : (128 + 2)) : 64); ;; revert on errors
}

() check_config() impure inline {
    cell config = config_param(SPAM_CONFIG);
    if (config.cell_null?()) {
        return ();
    }
    throw_if(666, config.begin_parse().preload_uint(16));
}

{-
    retransalate#_ id:uint16 remaining_hops:uint16 split_hops:uint8 preference:uint16 payload:Cell = IntMsgBody;
-}

() main (int msg_value, cell in_msg_full, slice in_msg_body) {

  if (in_msg_body.slice_empty?()) { ;; ignore empty messages
    return ();
  }
  
  check_config();

  slice cs = in_msg_full.begin_parse();
  int flags = cs~load_uint(4);
  if (flags & 1) {
    return ();
  }
  slice sender_address = cs~load_msg_addr();
  int sender_id = in_msg_body~load_uint(16);

  (int id, _, int public_key, cell code) = load_data();
  
  throw_unless(401, equal_slice_bits(
                       calc_address(calc_state_init(sender_id, public_key, code)), 
                       sender_address));

  int remaining_hops = in_msg_body~load_uint(16);
  int split_hops = in_msg_body~load_uint(8);
  int preference = in_msg_body~load_uint(16);

  ifnot(remaining_hops) {
    ;; return ();
    remaining_hops = 60000;
  }
  ;; if (remaining_hops < 65535) {
    remaining_hops -= 1;
  ;; }
  if(split_hops) {
    split_hops -= 1;

    ;; If there were some money on balance (for intstance from previous tests)
    ;; do not use it in current retranslation 
    raw_reserve(pair_first(get_balance()) - msg_value, 2);

    msg_value -= 273720; ;; gas + fwd, it will not make division by 2 ideal, but good enough
    retranslate(preference, remaining_hops, split_hops, id, public_key, code, in_msg_body, msg_value / 2);
    retranslate(preference, remaining_hops, split_hops, id, public_key, code, in_msg_body, -1);
  } else {
    retranslate(preference, remaining_hops, split_hops, id, public_key, code, in_msg_body, 0);
  }
}


() recv_external(slice in_msg) impure {
  var signature = in_msg~load_bits(512);
  var cs = in_msg;
  var (subwallet_id, valid_until, msg_seqno) = (cs~load_uint(32), cs~load_uint(32), cs~load_uint(32));
  throw_if(35, valid_until <= now());
  var (id, stored_seqno, public_key, code) = load_data();
  throw_unless(33, msg_seqno == stored_seqno);
  throw_unless(34, subwallet_id == id);
  throw_unless(35, check_signature(slice_hash(in_msg), signature, public_key));
  accept_message();
  var mode = cs~load_uint(8);
  if(mode == 255) {
      (int cnt,
       int hops,
       int split_hops,
       int amount,
       int preference) = (cs~load_uint(8),
                          cs~load_uint(16),
                          cs~load_uint(8),
                          cs~load_coins(),
                          cs~load_uint(16));
      while (cnt > 0) {
        retranslate(preference, hops, split_hops, id, public_key, code, cs, amount);
        cnt -= 1;
      }
  } else {
      send_raw_message(cs~load_ref(), mode);
  }
  set_data(pack_data(id, stored_seqno + 1, public_key, code));
}

;; Get methods

int seqno() method_id {
  var (id, stored_seqno, public_key, code) = load_data();
  return stored_seqno;
}

int get_public_key() method_id {
  var (id, stored_seqno, public_key, code) = load_data();
  return public_key;
}
"""

START_SPAM_FIF_TEMPLATE = """
"TonUtil.fif" include
"Asm.fif" include

"retranslator.fif" include =: contract_code

"wallet-retranslator.pk" load-generate-keypair 
=: privkey
=: pubkey
<b 0 16 u, 0 32 u, pubkey B, contract_code .s ref, b> =: contract_storage

<b b{00110} s, contract_code ref, contract_storage ref, b>
dup =: state_init

dup hashu 0 swap 2constant contract_address

."retranslator_address " contract_address .addr cr

<b 
  0 32 u, now 3600 + 32 u, 0 32 u, // subwallet until seqno
  255 8 u,            // mode = retranslate
  {{chains}} 8 u,     // chains
  65535 16 u,         // hops

  {{split_hops}} 8 u,                 // split hops
  1000000000 Gram* {{chains}} / Gram, // first message size
  {{preference}} 16 u,                // preference
b> =: init_message


init_message hashu privkey ed25519_sign_uint =: signature
<b b{1000100} s, contract_address addr, b{000010} s, state_init <s s, b{1} s, <b signature B,
   init_message <s s, b> ref, b>
2 boc+>B dup Bx. cr
"query-retranslator.boc" tuck B>file
"""


def compile_retranslator():
    src = RETRANSLATOR_SOURCE_TEMPLATE
    src = src.replace("{{max_retranslators}}", str(config_json["benchmark"]["max_retranslators"]))
    utils.run_cmd([FUNC_BIN, "-PAI", os.path.join(SMARTCONT_PATH, "stdlib.fc"), "-o", "retranslator.fif"],
                  stdin=src)


def prepare_retranslator() -> str:
    compile_retranslator()
    fif = START_SPAM_FIF_TEMPLATE
    fif = fif.replace("{{chains}}", str(config_json["benchmark"]["spam_chains"]))
    fif = fif.replace("{{split_hops}}", str(config_json["benchmark"]["spam_split_hops"]))
    fif = fif.replace("{{preference}}",
                str(min(65535, max(0, int(config_json["benchmark"]["spam_preference"] * 65535)))))
    res = utils.fift(fif)
    for s in res.split("\n"):
        if s.startswith("retranslator_address"):
            retranslator_addr = s.split()[1]
            break
    else:
        raise Exception("No retranslator_address")
    utils.fift_script(["wallet.fif", "main-wallet", retranslator_addr, "0", "2000000000", "-n"])
    return retranslator_addr


def stop_spam():
    utils.fift('<b 1 16 u, b> boc>B "conf-137.boc" B>file')
    utils.create_state_script(["update-config.fif", "config-master", "0", "-137", "conf-137.boc"])
    utils.lite_client("sendfile config-query.boc")