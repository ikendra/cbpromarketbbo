CBProMarketBBO is a Python module which provides the real time best bid and offer (BBO) feed for one or multiple
products of choice on Coinbase Pro. The module is written for Python 3.

The module can be used in two ways:

* With a callback function which gets invoked every time an update to BBO is detected, see ```main-callback.py```
* With a log file where BBO updates are written into (optionally also with debug information), see ```main-log.py``` 

CBProMarketBBO receives updates to the order books specified by user via WebSocket connection with Coinbase Pro
production public API. The idea behind this module is to hide the implementation details of Coinbase Pro API 
as well as usage of WebSocket from the module user. Therefore, it is suitable for beginners or for study purposes.

Note that this module was not optimized for performance.
