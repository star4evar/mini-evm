import json
from functools import lru_cache
from pathlib import Path

import redis
from eth_typing import BlockNumber
from eth_utils import to_wei, decode_hex

from eth import constants
from eth.chains.base import MiningChain
from eth.consensus.noproof import NoProofConsensus
from eth.db.atomic import AtomicDB
from eth.db.backends.redisdb import AtomicRedis
from eth.vm.forks.london import LondonVM


########################################################################################################################
##
##  get abi and bytecode
##
########################################################################################################################
# @param
#   json_path: e.g. "erc20_assets/ERC20.json"
# @return
#   (abi, bytecode)
def get_contract_info(json_path):
    path = Path(__file__).parent / json_path
    with open(path, 'r') as file:
        metadata = json.load(file)
        abi = metadata['abi']
        bytecode = metadata['data']['bytecode']['object']
        return abi, bytecode


########################################################################################################################
##
##  create accounts
##
########################################################################################################################
class Account:
    def __init__(self, public_key, private_key):
        self.private_key = private_key
        self.public_key = public_key


@lru_cache(maxsize=1)
def get_test_accounts():
    return [
        Account("0x90F8bf6A479f320ead074411a4B0e7944Ea8c9C1", "0x4f3edf983ac636a65a842ce7c78d9aa706d3b113bce9c46f30d7d21715b23b1d"),
        Account("0xFFcf8FDEE72ac11b5c542428B35EEF5769C409f0", "0x6cbed15c793ce57650b9877cf6fa156fbef513c4e6134f022a85b1ffdd59b2a1"),
        Account("0x22d491Bde2303f2f43325b2108D26f1eAbA1e32b", "0x6370fd033278c143179d81c5526140625662b8daa446c22ee2d73db3707e620c"),
        Account("0xE11BA2b4D45Eaed5996Cd0823791E0C93114882d", "0x646f1ce2fdad0e6deeeb5c7e8e5543bdde65e86029e2fd9fc169899c440a7913"),
        Account("0xd03ea8624C8C5987235048901fB614fDcA89b117", "0xadd53f9a7e588d003326d1cbf9e4a43c061aadd9bc938c843a79e7b4fd2ad743"),
        Account("0x95cED938F7991cd0dFcb48F0a06a40FA1aF46EBC", "0x395df67f0c2d2d9fe1ad08d1bc8b6627011959b79c53d7dd6a3536a33ab8a4fd"),
        Account("0x3E5e9111Ae8eB78Fe1CC3bb8915d5D461F3Ef9A9", "0xe485d098507f54e7733a205420dfddbe58db035fa577fc294ebd14db90767a52"),
        Account("0x28a8746e75304c0780E011BEd21C72cD78cd535E", "0xa453611d9419d0e56f499079478fd72c37b251a94bfde4d19872c44cf65386e3"),
        Account("0xACa94ef8bD5ffEE41947b4585a84BdA5a3d3DA6E", "0x829e924fdf021ba3dbbc4225edfece9aca04b929d6e75613329ca6f1d31c0bb4"),
        Account("0x1dF62f291b2E969fB0849d99D9Ce41e2F137006e", "0xb0057716d5917badaf911b193b12b910811c1497b5bada8d7711f758981c3773")
    ]



########################################################################################################################
##
##  create chain
##
########################################################################################################################
GENESIS_PARAMS = {
    'coinbase': constants.ZERO_ADDRESS,
    'transaction_root': constants.BLANK_ROOT_HASH,
    'receipt_root': constants.BLANK_ROOT_HASH,
    'difficulty': 1,
    'gas_limit': constants.GAS_LIMIT_MAXIMUM,
    'extra_data': constants.GENESIS_EXTRA_DATA,
    'nonce': constants.GENESIS_NONCE
}


@lru_cache(maxsize=1)
def get_redis_conn():
    return redis.StrictRedis(host='localhost', port=6379, db=0)


@lru_cache(maxsize=1)
def get_chain():

    atomic_db = AtomicDB()
    # atomic_db = AtomicRedis(get_redis_conn())

    balance = to_wei(10000, 'ether')
    accounts = get_test_accounts()

    genesis_state = {
        decode_hex(account.public_key):  {'balance': balance, 'nonce': 0, 'code': b'', 'storage': {} }
        for account in accounts
    }

    vm_class = LondonVM.configure( consensus_class = NoProofConsensus)
    vm_config = ( (BlockNumber(0), vm_class),  )

    chainclass = MiningChain.configure( vm_configuration = vm_config)
    chain = chainclass.from_genesis(atomic_db, GENESIS_PARAMS, genesis_state)

    return chain
