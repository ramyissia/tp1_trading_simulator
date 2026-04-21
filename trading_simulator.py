
import json
import os
from datetime import datetime, timezone

import requests


URL = "https://api.coingecko.com/api/v3/simple/price"
COINS = ["bitcoin", "ethereum", "solana"]
VS_CURRENCY = "usd"
PORTFOLIO_FILE = "portfolio.json"
INITIAL_CASH = 10000.0


def fetch_prices(coins=COINS, vs_currency=VS_CURRENCY):
    # appel API CoinGecko
    params = {"ids": ",".join(coins), "vs_currencies": vs_currency}
    r = requests.get(URL, params=params, timeout=10)
    r.raise_for_status()
    return r.json()


def show_prices(prices):
    print("Reponse brute de l'API :")
    print(prices)
    print()
    print("Prix (USD) :")
    for coin, data in prices.items():
        print("  " + coin.capitalize().ljust(10) + " " + f"{data[VS_CURRENCY]:,.2f}" + " USD")


def default_portfolio():
    # structure initiale
    return {
        "cash": INITIAL_CASH,
        "positions": {},
        "trades": [],
    }


def save_portfolio(portfolio, path=PORTFOLIO_FILE):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(portfolio, f, indent=2)


def load_portfolio(path=PORTFOLIO_FILE):
    # si le fichier n'existe pas encore, on retourne un portefeuille neuf
    if not os.path.exists(path):
        return default_portfolio()
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def buy(portfolio, coin, usd_amount, prices):
    # on verifie que le montant est ok et qu'on a assez de cash
    if usd_amount <= 0:
        raise ValueError("Montant invalide")
    if usd_amount > portfolio["cash"]:
        raise ValueError("Pas assez de cash (" + f"{portfolio['cash']:.2f}" + " USD dispo)")
    if coin not in prices:
        raise ValueError("Coin inconnu : " + coin)

    price = prices[coin][VS_CURRENCY]
    qty = usd_amount / price

    portfolio["cash"] -= usd_amount
    if coin in portfolio["positions"]:
        portfolio["positions"][coin] += qty
    else:
        portfolio["positions"][coin] = qty

    portfolio["trades"].append({
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "side": "BUY",
        "coin": coin,
        "quantity": qty,
        "price": price,
        "usd_amount": usd_amount,
    })
    return qty


def sell(portfolio, coin, quantity, prices):
    if quantity <= 0:
        raise ValueError("Quantite invalide")
    if coin not in prices:
        raise ValueError("Coin inconnu : " + coin)

    held = portfolio["positions"].get(coin, 0)
    if quantity > held:
        raise ValueError("Pas assez de " + coin + " (" + f"{held:.8f}" + " dispo)")

    price = prices[coin][VS_CURRENCY]
    usd_amount = quantity * price

    portfolio["cash"] += usd_amount
    portfolio["positions"][coin] = held - quantity
    # si la position est vide (ou presque), on l'enleve
    if portfolio["positions"][coin] < 0.00000001:
        del portfolio["positions"][coin]

    portfolio["trades"].append({
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "side": "SELL",
        "coin": coin,
        "quantity": quantity,
        "price": price,
        "usd_amount": usd_amount,
    })
    return usd_amount


def portfolio_summary(portfolio, prices):
    print()
    print("--- Portefeuille ---")
    print("Cash : " + f"{portfolio['cash']:,.2f}" + " USD")

    total_pos = 0
    if len(portfolio["positions"]) == 0:
        print("Pas de positions")
    else:
        print("Positions :")
        for coin, qty in portfolio["positions"].items():
            price = prices[coin][VS_CURRENCY]
            value = qty * price
            total_pos += value
            print("  " + coin.ljust(10) + f" {qty:.8f}" + "  @ " + f"{price:,.2f}" + "  =  " + f"{value:,.2f}" + " USD")

    total = portfolio["cash"] + total_pos
    print("Valeur des positions : " + f"{total_pos:,.2f}" + " USD")
    print("Total : " + f"{total:,.2f}" + " USD")

    if len(portfolio["trades"]) > 0:
        print()
        print("Derniers trades :")
        for t in portfolio["trades"][-5:]:
            print("  " + t["timestamp"] + " " + t["side"] + " " + t["coin"]
                  + " qty=" + f"{t['quantity']:.8f}"
                  + " prix=" + f"{t['price']:,.2f}")
    print()


def main():
    portfolio = load_portfolio()
    prices = fetch_prices()
    print("Portefeuille charge depuis " + PORTFOLIO_FILE)
    print("Coins : " + ", ".join(COINS))
    print()

    while True:
        print("1) Voir les prix")
        print("2) Acheter")
        print("3) Vendre")
        print("4) Resume du portefeuille")
        print("5) Reset")
        print("6) Quitter")
        choix = input("> ").strip()

        try:
            if choix == "1":
                prices = fetch_prices()
                show_prices(prices)

            elif choix == "2":
                prices = fetch_prices()
                coin = input("Coin (" + "/".join(COINS) + ") : ").strip().lower()
                usd = float(input("Montant USD : "))
                qty = buy(portfolio, coin, usd, prices)
                save_portfolio(portfolio)
                print("Achete " + f"{qty:.8f}" + " " + coin + " pour " + f"{usd:.2f}" + " USD")

            elif choix == "3":
                prices = fetch_prices()
                coin = input("Coin (" + "/".join(COINS) + ") : ").strip().lower()
                qty = float(input("Quantite : "))
                usd = sell(portfolio, coin, qty, prices)
                save_portfolio(portfolio)
                print("Vendu " + f"{qty:.8f}" + " " + coin + " pour " + f"{usd:.2f}" + " USD")

            elif choix == "4":
                prices = fetch_prices()
                portfolio_summary(portfolio, prices)

            elif choix == "5":
                portfolio = default_portfolio()
                save_portfolio(portfolio)
                print("Portefeuille reset")

            elif choix == "6":
                save_portfolio(portfolio)
                print("Bye")
                break

            else:
                print("Choix invalide")

        except Exception as e:
            print("Erreur : " + str(e))


if __name__ == "__main__":
    main()
