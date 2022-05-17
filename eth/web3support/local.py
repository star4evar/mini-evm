from collections import deque
from typing import Any, Dict, Deque

import rlp
from eth_utils import encode_hex, decode_hex
from rlp.sedes import Binary, big_endian_int, binary

from eth.abc import VirtualMachineAPI
from eth.chains.base import ChainAPI
from eth.vm.message import Message
from eth.vm.spoof import SpoofTransaction

from web3 import Web3
from web3.providers.base import BaseProvider
from web3.types import RPCEndpoint, RPCResponse


class Transaction(rlp.Serializable):
    fields = [
        ("nonce", big_endian_int),
        ("gas_price", big_endian_int),
        ("gas", big_endian_int),
        ("to", Binary.fixed_length(20, allow_empty=True)),
        ("value", big_endian_int),
        ("data", binary),
        ("v", big_endian_int),
        ("r", big_endian_int),
        ("s", big_endian_int),
    ]


class LocalWeb3(Web3):
    def __init__(self, chain: ChainAPI):
        super().__init__( provider=LocalWeb3Provider(chain) )



class LocalWeb3Provider(BaseProvider):

    def __init__(self, chain: ChainAPI):
        self.chain = chain
        self.vm: VirtualMachineAPI = chain.get_vm()
        self._id = 0
        self.receipt_hashes: Deque = deque()
        self.receipts: Dict = dict()

    def isConnected(self) -> bool:
            return True


    ###################################################################################
    ##
    ##  recent transaction receipts are cahced in memory(only keep latest 100 records)
    ##
    ###################################################################################
    def get_receipt(self, tx_hash):
        if isinstance(tx_hash, str):
            tx_hash = decode_hex(tx_hash)

        result = self.receipts.get(tx_hash)
        return result


    def add_receipt(self, tx_index, tx, receipt, computation, block):
        hash_bytes = tx.hash
        tx_hash = encode_hex(hash_bytes)
        tx_index = hex(tx_index)
        block_hash = encode_hex(block.hash)
        block_num = hex(block.number)

        logs = []
        for i, raw_log in enumerate(receipt.logs):
            # each topic is a number
            topics = list(f"0x{topic:064x}" for topic in raw_log.topics)
            logs.append({
                'removed': False,
                'logIndex': hex(i),
                'transactionIndex': tx_index,
                'transactionHash': tx_hash,
                'blockHash': block_hash,
                'blockNumber': block_num,
                'address': encode_hex(raw_log.address),
                'data': encode_hex(raw_log.data),
                'topics': topics
            })

        receipt = {
            'transactionHash': tx_hash,
            'transactionIndex': tx_index,
            'blockHash': block_hash,
            'blockNumber': block_num,
            'from': encode_hex(computation.msg.sender),
            'to': encode_hex(computation.msg.to),
            'cumulativeGasUsed': receipt.gas_used,
            'gasUsed': hex(computation.get_gas_used()),
            'contractAddress': encode_hex(computation.msg.storage_address),
            'logs': logs,
            'logsBloom': "{:0512x}".format(receipt.bloom),
            # not sure what does the type and status field means, just use constants
            'type': '0x0',
            'status': '0x1',
            'effectiveGasPrice': hex(block.header.base_fee_per_gas),
        }


        self.receipt_hashes.append(hash_bytes)
        self.receipts[hash_bytes] = receipt

        # remove oldest cache if size reaches limit.
        if len(self.receipt_hashes) > 100:
            oldest_hash = self.receipt_hashes.popleft()
            self.receipts.pop(oldest_hash, None)



    def make_request(self, method: RPCEndpoint, params: Any) -> RPCResponse:
        func = getattr(self, method, None)
        if not callable(func):
            raise NotImplementedError(f"(LocalWeb3Provider) method {method} did not implemented yet.")

        response: RPCResponse = func(params)
        return response


    @property
    def nextId(self):
        self._id += 1
        return self._id


    # params:  <class 'tuple'>:
    #   ({'from': '0x90F8bf6A479f320ead074411a4B0e7944Ea8c9C1', 'data': '0x*********'},)
    def eth_estimateGas(self, params: Any):
        param = params[0]
        data = decode_hex(param['data'])
        from_ = param.get("from")
        from_ = decode_hex(from_) if from_ else bytes(20)

        canonical_params = {}
        field_sedes ={
            "nonce": big_endian_int,
            "gas_price": big_endian_int,
            "gas": big_endian_int,
            "to": Binary.fixed_length(20, allow_empty=True),
            "value": big_endian_int,
            "data": binary,
        }
        for param_name, param_value in param.items():
            param_sede = field_sedes.get(param_name)
            if param_sede is not None:
                param_bytes = decode_hex(param_value)
                value = param_sede.deserialize(param_bytes)
                canonical_params[param_name] = value

        allow_gas = 2 ** 256 -1
        raw_tx = self.vm.create_unsigned_transaction(
            nonce= canonical_params.get("nonce", 0),
            gas_price = canonical_params.get("gas_price", 0),
            gas = canonical_params.get("gas", allow_gas),
            to= canonical_params.get("to",  b''),
            value = canonical_params.get("value", 0),
            data =canonical_params.get("data", b''),
        )
        tx = SpoofTransaction(raw_tx, from_= from_)

        # state = self.chain.get_vm().state
        state = self.vm.state
        snapshot = state.snapshot()
        # state.set_balance(from_, 2**256-1)
        computation = state.apply_transaction(tx)
        state.revert(snapshot)

        if computation.is_success:
            gas_estimation: int = allow_gas - computation._gas_meter.gas_remaining
            return {'jsonrpc': '2.0', 'id': self.nextId, 'result': hex(gas_estimation)}
        else:
            error_type = type(computation.error).__name__
            error_info = str(computation.output[4:].replace(b'\x00', b'')[2:], 'ascii')
            return {
                'jsonrpc': '2.0', 'id': self.nextId,
                'error':( f"VM Exception while processing transaction ({error_type}):'{error_info}'" )
            }



    # request_data = {bytes} b'{"jsonrpc": "2.0", "method": "eth_gasPrice", "params": [], "id": 150}'
    # response = {dict} <class 'dict'>: {'jsonrpc': '2.0', 'id': 150, 'result': '0x3f2379d4'}
    def eth_gasPrice(self, params: Any):
        # params:
        #   <class 'tuple'>: ()
        gas_price = self.vm.get_header().base_fee_per_gas
        return {'jsonrpc': '2.0', 'id': self.nextId, 'result': hex(gas_price)}


    def eth_chainId(self, params: Any):
        # params:
        #   <class 'tuple'>: ()
        # chainId = self.chain.chain_id
        return {'jsonrpc': '2.0', 'id': self.nextId, 'result': hex(1337)}



    # method = {str} 'eth_sendRawTransaction'
    # params = {list} <class 'list'>: ['0x******']
    def eth_sendRawTransaction(self, params: Any):

        detail = decode_hex(params[0])
        tx = rlp.decode(detail, Transaction)
        tx = self.vm.get_transaction_builder().new_transaction(
            tx.nonce,
            tx.gas_price,
            tx.gas,
            tx.to,
            tx.value,
            tx.data,
            tx.v,
            tx.r,
            tx.s,
        )
        # self.chain.mine_block()
        new_block, receipt, computation = self.chain.apply_transaction(tx)

        self.chain.mine_block()
        self.add_receipt(0, tx, receipt, computation, new_block)

        if computation.is_success:
            return {'jsonrpc': '2.0', 'id': self.nextId, 'result': tx.hash}
        else:
            error_type = type(computation.error).__name__
            error_info = str(computation.output[4:].replace(b'\x00', b'')[2:], 'ascii')
            return {
                'jsonrpc': '2.0', 'id': self.nextId,
                'error':( f"VM Exception while processing transaction ({error_type}):'{error_info}'" )
            }


    # params = {list} <class 'list'>: ['0xc6c234b439a2d39ad08081ad5ea3e41f94335fb6e42511563bed5863f5b62f4a']
    # response = {dict} <class 'dict'>: {'jsonrpc': '2.0', 'id': 147, 'result': {'transactionHash': '0xc6c234b439a2d39ad08081ad5ea3e41f94335fb6e42511563bed5863f5b62f4a', 'transactionIndex': '0x0', 'blockHash': '0x53de40d48918f308722b62ee8a53bdde5d4ccebf5886d29d6509fa8ed9cba94a',
    def eth_getTransactionReceipt(self, params: Any):
        hash = params[0]
        # receipt = self.chain.get_transaction_receipt(decode_hex(hash))
        return {'jsonrpc': '2.0', 'id': self.nextId, 'result': self.get_receipt(hash)}


    # params = {list} <class 'list'>: ['0x90F8bf6A479f320ead074411a4B0e7944Ea8c9C1', 'latest']
    # response = {dict} <class 'dict'>: {'jsonrpc': '2.0', 'id': 148, 'result': '0x15'}
    def eth_getTransactionCount(self, params: Any):
        address = params[0]
        count = self.chain.get_vm().state.get_nonce(decode_hex(address))
        return {'jsonrpc': '2.0', 'id': self.nextId, 'result': hex(count)}


    # "params": [{"to": "0xb09bCc172050fBd4562da8b229Cf3E45Dc3045A6",
    #               "data": "0x70a0823100000000000000000000000090f8bf6a479f320ead074411a4b0e7944ea8c9c1"}, "latest"],
    # response = {dict} <class 'dict'>: {'jsonrpc': '2.0', 'id': 154, 'result': '0x0000000000000000000000000000000000000000000014ea0fb67c9a6f140000'}
    def eth_call(self, params: Any):
        param, state = params[0], self.chain.get_vm().state
        to = decode_hex(param["to"])
        data = decode_hex(param['data'])
        code = state.get_code(to)
        message = Message(
            gas = 2**256-1,
            to= to,
            sender= bytes(20),
            value=0,
            data= data,
            code= code,
        )
        transaction_context = state.get_transaction_context_class()(
            0, bytes(20)
        )
        computation = state.computation_class.apply_computation( state,  message, transaction_context)
        return {'jsonrpc': '2.0', 'id': self.nextId, 'result': encode_hex(computation.output)}


    def eth_getCode(self, params: Any):
        # print("getting code: ", params)
        addr = params[0]
        addr_bytes = decode_hex(addr)
        code = self.chain.vm.state.get_code(addr_bytes)
        return { 'jsonrpc': '2.0', 'id': self.nextId, 'result': encode_hex(code) }
