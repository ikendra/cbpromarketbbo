__all__ = ['CBProMarketBBO', 'timer']
__version__ = '0.1'
__author__ = 'Ivo Kendra'

import websocket
import time
import logging
import urllib.request
import json
import math
import functools
from typing import Dict, List, Callable


URL_WS = "wss://ws-feed.pro.coinbase.com/"
URL_PRODUCTS = "https://api.pro.coinbase.com/products"
URL_USER_AGENT = "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:12.0) Gecko/20100101 Firefox/12.0"

MSG_SNAPSHOT = "snapshot"
MSG_L2UPDATE = "l2update"
MSG_SUBCRIPTIONS = "subscriptions"

BOOK_BIDS = "bids"
BOOK_ASKS = "asks"

BID_PRICE = "bid_price"
BID_SIZE = "bid_size"
ASK_PRICE = "ask_price"
ASK_SIZE = "ask_size"


def timer(method):

    @functools.wraps(method)
    def wrapper(*args):

        t_start = time.time()
        method_return = method(*args)
        t_finish = time.time()

        logging.debug("Time spent in {0}: {1:.6f} s".format(method.__name__, t_finish - t_start))

        return method_return

    return wrapper


class CBProMarketBBO:

    def __init__(
            self, products: List, output_file_name: str = None,
            callback_func: Callable[[], None] = None, debug: bool = False) -> None:

        self.book: Dict = {}
        self.bbo: Dict = {}
        self.ws = None
        self.event_count: int = 0
        self.logfile_enabled: bool = False
        self.callback_func = callback_func

        for key in products:
            self.bbo[key] = {
                BID_PRICE: None,
                BID_SIZE: None,
                ASK_PRICE: None,
                ASK_SIZE: None
            }

        if output_file_name is None:
            logging.disable()
        else:
            if debug:
                _logging_level = logging.DEBUG
            else:
                _logging_level = logging.INFO
            self.logfile_enabled = True
            logging.basicConfig(format='%(asctime)s - %(message)s', level=_logging_level, filename=output_file_name)

        self.products = self._initialize_products(products)

    @timer
    def _initialize_products(self, products: List) -> Dict[str, int]:

        """Retrieve relevant details about the products from Coinbase Pro

        We need to know at least the quote increment for the products so that we display the prices
        with the correct number of decimal places

        """

        product_request = urllib.request.Request(url=URL_PRODUCTS, headers={'User-Agent': URL_USER_AGENT})
        product_response = urllib.request.urlopen(product_request)
        all_products = json.load(product_response)

        product_details = {}

        for product in products:
            for cbpro_product in all_products:
                if cbpro_product["id"] == product:
                    quote_increment = float(cbpro_product["quote_increment"])
                    num_decimal_places = int(math.log10(1 / quote_increment))
                    product_details[product] = num_decimal_places
                    logging.debug(
                        "Retrieved quote increment for {}: {} = {} decimal places".
                        format(product, quote_increment, num_decimal_places))

        return product_details

    def start(self) -> None:

        self.ws = websocket.WebSocketApp(
            URL_WS,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close,
            on_open=self.on_open)

        if self.ws:
            self.ws.run_forever()

    def on_open(self) -> None:

        """Subscribe to events from Coinbase Pro

        """

        channel = [{"name": "level2", "product_ids": list(self.products.keys())}]
        msg_subscribe = {"type": "subscribe", "channels": channel}

        subscribe_payload = json.dumps(msg_subscribe)
        self.ws.send(subscribe_payload)

    def on_error(self, msg) -> None:

        logging.error(msg)

    def on_close(self) -> None:

        logging.debug("Websocket closed")
        logging.debug("Total events received: {} ".format(self.event_count))

    def on_message(self, msg) -> None:

        """Receive and process an event from Coinbase Pro

        On MSG_SUBSCRIPTIONS we receive acknowledgement that we're successfully subscribed. On MSG_SNAPSHOT we
        receive the entire order book for given product. ON MSG_L2UPDATE we receive updates to the book, which we
        have to put on top of the snapshot. (Level 2 means aggregated updates for up to 50 levels of the order book)

        """

        decoded_msg = json.loads(msg)
        message_type = decoded_msg["type"]

        if message_type == MSG_SUBCRIPTIONS:

            product_ids = decoded_msg["channels"]
            logging.debug("Subscriptions: {}".format(product_ids))

        elif message_type == MSG_SNAPSHOT:

            product_id = decoded_msg["product_id"]
            self._snapshot(decoded_msg)

            # Old best bid and ask doesn't exist yet, this will always set a new bbo
            self.set_if_new_bbo(product_id)

        elif message_type == MSG_L2UPDATE:

            product_id = decoded_msg["product_id"]
            self.update(decoded_msg)

            self.set_if_new_bbo(product_id)

        self.event_count += 1

    @timer
    def _snapshot(self, msg) -> None:

        """Process a snapshot message

        Store the snapshot of the order book in memory. Snapshot is stored in such data structure that will be easy
        to update with subsequent incremental order book update events

        """

        product_id = msg["product_id"]
        logging.debug("Received snapshot for {}".format(product_id))
        price_precision = "%.{}f".format(self.products[product_id])

        self.book[product_id] = {}

        for book_side in [BOOK_BIDS, BOOK_ASKS]:
            self.book[product_id][book_side] = \
                {(price_precision % float(level[0])): float(level[1]) for level in msg[book_side]}

    def update(self, msg) -> None:

        product_id = msg["product_id"]
        price_precision = "%.{}f".format(self.products[product_id])

        for change in msg["changes"]:

            side = change[0]
            price = float(change[1])
            size = float(change[2])

            book_side = BOOK_BIDS if side == "buy" else BOOK_ASKS

            if size == 0:
                self.book[product_id][book_side].pop((price_precision % price))
            else:
                self.book[product_id][book_side][(price_precision % price)] = size

    def set_if_new_bbo(self, product_id) -> bool:

        """Sets the new best bid and ask, if found in the order book

        If no new best bid and ask is detected in the order book, no data structure is modified

        """

        bbo_has_changed = False

        max_bid_price = max(self.book[product_id][BOOK_BIDS], key=lambda x: float(x))
        max_bid_size = self.book[product_id][BOOK_BIDS][max_bid_price]
        min_ask_price = min(self.book[product_id][BOOK_ASKS], key=lambda x: float(x))
        min_ask_size = self.book[product_id][BOOK_ASKS][min_ask_price]

        current_bbo = {
            BID_PRICE: max_bid_price,
            BID_SIZE: max_bid_size,
            ASK_PRICE: min_ask_price,
            ASK_SIZE: min_ask_size}

        if current_bbo != self.bbo[product_id]:

            if self.callback_func:
                self.callback_func(product_id, current_bbo)

            self.bbo[product_id] = current_bbo
            logging.info("{}: {} @ {} -- {} @ {}".
                         format(product_id, max_bid_size, max_bid_price, min_ask_size, min_ask_price))

            bbo_has_changed = True

        return bbo_has_changed
