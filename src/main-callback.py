import cbpromarketbbo.cbpromarketbbo as bbo


def print_bbo(product_id, current_bbo) -> None:

    """This function is invoked every time when an update to the best bid and offer is detected

    Use this function as a starting point for your custom processing of received information.
    In this example we just print what we received

    """

    print("{}: {} @ {} -- {} @ {}".
          format(product_id,
                 current_bbo[bbo.BID_SIZE], current_bbo[bbo.BID_PRICE],
                 current_bbo[bbo.ASK_SIZE], current_bbo[bbo.ASK_PRICE]))


if __name__ == "__main__":

    # Sample list of products (multiple products)
    products = ["ETH-EUR", "ETH-BTC", "BTC-EUR"]

    # Sample list of products (single product)
    # products = ["BTC-EUR"]

    cbpro_market_bbo = bbo.CBProMarketBBO(products, callback_func=print_bbo)

    # Program does not end running, it has to be interrupted by user
    cbpro_market_bbo.start()
