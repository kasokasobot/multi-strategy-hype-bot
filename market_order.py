import argparse
import eth_account
import utils
from eth_account.signers.local import LocalAccount
from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants

def place_market_order(coin, is_buy, sz):
    config = utils.get_config()
    account: LocalAccount = eth_account.Account.from_key(config["secret_key"])
    exchange = Exchange(account, constants.MAINNET_API_URL)

    print(f"We try to Market {'Buy' if is_buy else 'Sell'} {sz} {coin}.")

    order_result = exchange.market_open(coin, is_buy, sz)
    if order_result["status"] == "ok":
        for status in order_result["response"]["data"]["statuses"]:
            try:
                filled = status["filled"]
                print(f'Order #{filled["oid"]} filled {filled["totalSz"]} @{filled["avgPx"]}')
            except KeyError:
                print(f'Error: {status["error"]}')

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Market Order Script')
    parser.add_argument('coin', type=str, help='Cryptocurrency for the order (e.g., BTC)')
    parser.add_argument('order_type')
    parser.add_argument('sz', type=float, help='Size of the order')
    args = parser.parse_args()

    place_market_order(args.coin, is_buy, args.sz)
