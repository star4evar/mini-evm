
#This is a fork of [py-evm](https://github.com/ethereum/py-evm)

I have added a [redis db support](eth/db/backends/redisdb.py) for AtomicDB,
to save data in a separated process so as to keep python process clean.

Also provided web3 implementation so that you can interact with this EVM via web3 api , 
such as web3.py/js, ethers.js, please refer to [eth.demo](eth/demo) to see how to use it.
implemention code is at [eth.web3support](eth/web3support)

