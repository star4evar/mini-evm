from eth.demo import _helper as helper
from eth.web3support.rpc_server import Web3RPCServer

def run():
    chain = helper.get_chain()

    server = Web3RPCServer(chain)
    server.start(8545)



if __name__ == "__main__":
    run()