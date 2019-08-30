from cbpromarketbbo import cbpromarketbbo


if __name__ == "__main__":

    # Sample list of products (multiple products)
    products = ["ETH-EUR", "ETH-BTC", "BTC-EUR"]

    # Sample list of products (single product)
    # products = ["BTC-EUR"]

    cbpro_market_bbo = cbpromarketbbo.CBProMarketBBO(products, output_file_name="cbpro-market-bbo.log", debug=True)

    # Program does not end running, it has to be interrupted by user
    cbpro_market_bbo.start()
