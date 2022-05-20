from eth.demo import _helper as helper

from eth_utils import from_wei, to_wei

from eth.web3support.local import LocalWeb3

from web3.eth import Contract

def run():

    chain = helper.get_chain()

    # 使用 py-evm 的 web3 provider. 如果要切换回默认的 http provider, 请注释掉此行
    accounts = helper.get_test_accounts()
    w3 = LocalWeb3(chain)

    abi, bytecode = helper.get_contract_info("erc20_assets/ERC20.json")
    pub, pri = accounts[0].public_key, accounts[0].private_key


    ####################################################################################################################
    ## deploy the contract
    ####################################################################################################################
    contract = depoly_erc20(w3, pub, pri, abi, bytecode, "wrapped BTC", "WBTC")

    totalSupply = contract.functions.totalSupply().call()
    print("total supply right after deploy:", from_wei(totalSupply, 'ether') )


    ####################################################################################################################
    ## mint some token and test
    ####################################################################################################################
    recp = mint(w3, contract, pub, pri, pub, to_wei(1000, 'ether'))

    totalSupply = contract.functions.totalSupply().call()
    balance0 = contract.functions.balanceOf(pub).call()
    print("\ntotal supply after mint:", from_wei(totalSupply, 'ether') )
    print("balance of account mint to:", from_wei(balance0, 'ether') )


    ####################################################################################################################
    ## transfer 200 to another account, and test
    ####################################################################################################################
    recp = transfer(w3, contract, pub, pri, accounts[1].public_key, to_wei(200, 'ether'))

    balance0 = contract.functions.balanceOf(pub).call()
    balance1 = contract.functions.balanceOf(accounts[1].public_key).call()
    print("\nbalance of sender after transfer:", from_wei(balance0, 'ether') )
    print("balance of receiver after transfer:", from_wei(balance1, 'ether') )


    ####################################################################################################################
    ## approve 99999 , and test
    ####################################################################################################################
    recp = approve(w3, contract, pub, pri, accounts[3].public_key, to_wei(99999, 'ether'))

    allowance = contract.functions.allowance(pub, accounts[3].public_key).call()
    print("\nallowance after approve:", from_wei(allowance, 'ether') )



def depoly_erc20(w3, public_key, private_key, abi, bytecode, name, symbol) -> Contract:
    eth = w3.eth
    offline_contract = eth.contract(abi=abi, bytecode=bytecode)
    constructor = offline_contract.constructor(name, symbol)

    signed_txn = eth.account.sign_transaction(constructor.buildTransaction({
        'gas': 30000000,
        'nonce':  eth.get_transaction_count(public_key)
    }), private_key=private_key)

    txn_hash = eth.send_raw_transaction(signed_txn.rawTransaction)
    txn_receipt = eth.wait_for_transaction_receipt(txn_hash)

    return eth.contract(
        address = txn_receipt.contractAddress,
        abi = abi
    )


def mint(w3, contract, public_key, private_key, to, amount):
    eth = w3.eth

    params = {
        'from': public_key,
        'gas': 30000000,
        'nonce':  eth.get_transaction_count(public_key),
    }

    trans  = contract.functions.mint(to, amount).buildTransaction(params)
    signed_txn = eth.account.sign_transaction(trans, private_key = private_key)

    hash = eth.send_raw_transaction(signed_txn.rawTransaction)
    txn_receipt = eth.wait_for_transaction_receipt(hash)

    return txn_receipt


def transfer(w3, contract, public_key, private_key, to, amount):
    eth = w3.eth
    params = {
        'from': public_key,
        'gas': 30000000,
        'nonce':  eth.get_transaction_count(public_key),
    }

    trans  = contract.functions.transfer(to, amount).buildTransaction(params)
    signed_txn = eth.account.sign_transaction(trans, private_key = private_key)

    hash = eth.send_raw_transaction(signed_txn.rawTransaction)
    txn_receipt = eth.wait_for_transaction_receipt(hash)

    return txn_receipt


def approve(w3, contract, public_key, private_key, spender, amount):
    eth = w3.eth
    params = {
        'from': public_key,
        'gas': 30000000,
        'nonce':  eth.get_transaction_count(public_key),
    }

    trans  = contract.functions.approve(spender, amount).buildTransaction(params)
    signed_txn = eth.account.sign_transaction(trans, private_key = private_key)

    hash = eth.send_raw_transaction(signed_txn.rawTransaction)
    txn_receipt = eth.wait_for_transaction_receipt(hash)

    return txn_receipt


if __name__ == "__main__":
    run()