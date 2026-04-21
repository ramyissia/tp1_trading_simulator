# Interface graphique du simulateur (Tkinter)
# On reutilise les fonctions de trading_simulator.py

import tkinter as tk
from tkinter import messagebox, ttk

from trading_simulator import (
    COINS,
    PORTFOLIO_FILE,
    VS_CURRENCY,
    buy,
    default_portfolio,
    fetch_prices,
    load_portfolio,
    save_portfolio,
    sell,
)


class TradingApp(tk.Tk):

    def __init__(self):
        super().__init__()
        self.title("TP1 - Trading Simulator")
        self.geometry("900x640")

        # on charge le portefeuille (ou on en cree un neuf)
        self.portfolio = load_portfolio()
        self.prices = {}

        # theme un peu plus propre que le theme par defaut
        style = ttk.Style(self)
        if "clam" in style.theme_names():
            style.theme_use("clam")
        style.configure("Titre.TLabel", font=("Segoe UI", 16, "bold"))
        style.configure("Header.TLabel", font=("Segoe UI", 11, "bold"))
        style.configure("Prix.TLabel", font=("Consolas", 14))
        style.configure("Equity.TLabel", font=("Segoe UI", 13, "bold"), foreground="#0a7d32")

        self.build_ui()
        # on recupere les prix au lancement
        self.refresh_prices()

    def build_ui(self):
        # barre du haut
        top = ttk.Frame(self, padding=(12, 10))
        top.pack(fill="x")
        ttk.Label(top, text="TP1 - Trading Simulator", style="Titre.TLabel").pack(side="left")
        ttk.Button(top, text="Refresh prices", command=self.refresh_prices).pack(side="right")
        ttk.Button(top, text="Reset portfolio", command=self.reset_portfolio).pack(side="right", padx=(0, 8))

        main = ttk.Frame(self, padding=(12, 0, 12, 12))
        main.pack(fill="both", expand=True)
        main.columnconfigure(0, weight=1, uniform="c")
        main.columnconfigure(1, weight=1, uniform="c")
        main.rowconfigure(1, weight=1)

        # --- prix ---
        prix_frame = ttk.LabelFrame(main, text="Prix live (USD)", padding=10)
        prix_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 6), pady=(0, 8))
        self.price_labels = {}
        i = 0
        for coin in COINS:
            ttk.Label(prix_frame, text=coin.capitalize(), style="Header.TLabel").grid(row=i, column=0, sticky="w", pady=2)
            lbl = ttk.Label(prix_frame, text="—", style="Prix.TLabel")
            lbl.grid(row=i, column=1, sticky="e", padx=12, pady=2)
            self.price_labels[coin] = lbl
            i += 1
        prix_frame.columnconfigure(1, weight=1)

        # --- ordre (achat/vente) ---
        order_frame = ttk.LabelFrame(main, text="Passer un ordre", padding=10)
        order_frame.grid(row=0, column=1, sticky="nsew", padx=(6, 0), pady=(0, 8))

        ttk.Label(order_frame, text="Coin").grid(row=0, column=0, sticky="w")
        self.coin_var = tk.StringVar(value=COINS[0])
        cb = ttk.Combobox(order_frame, textvariable=self.coin_var, values=COINS, state="readonly", width=18)
        cb.grid(row=0, column=1, sticky="ew", padx=6, pady=4)

        ttk.Label(order_frame, text="Montant USD").grid(row=1, column=0, sticky="w")
        self.usd_var = tk.StringVar()
        # a chaque fois qu'on tape, on recalcule la conversion
        self.usd_var.trace_add("write", self.on_usd_change)
        ttk.Entry(order_frame, textvariable=self.usd_var).grid(row=1, column=1, sticky="ew", padx=6, pady=4)

        # petit cadre pour afficher la conversion dans les autres cryptos
        conv_frame = ttk.LabelFrame(order_frame, text="Equivaut a", padding=6)
        conv_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(4, 0))
        self.conv_labels = {}
        j = 0
        for coin in COINS:
            ttk.Label(conv_frame, text=coin.capitalize()).grid(row=j, column=0, sticky="w")
            lbl = ttk.Label(conv_frame, text="—", font=("Consolas", 10))
            lbl.grid(row=j, column=1, sticky="e", padx=8)
            self.conv_labels[coin] = lbl
            j += 1
        conv_frame.columnconfigure(1, weight=1)

        btns = ttk.Frame(order_frame)
        btns.grid(row=3, column=0, columnspan=2, pady=(8, 0), sticky="ew")
        ttk.Button(btns, text="ACHETER", command=self.on_buy).pack(side="left", fill="x", expand=True, padx=(0, 4))
        ttk.Button(btns, text="VENDRE", command=self.on_sell).pack(side="left", fill="x", expand=True, padx=(4, 0))
        ttk.Button(order_frame, text="Vendre tout ce coin", command=self.on_sell_all).grid(row=4, column=0, columnspan=2, sticky="ew", pady=(6, 0))
        order_frame.columnconfigure(1, weight=1)

        # --- portefeuille ---
        pf_frame = ttk.LabelFrame(main, text="Portefeuille", padding=10)
        pf_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 6))

        self.cash_lbl = ttk.Label(pf_frame, text="Cash : —", style="Header.TLabel")
        self.cash_lbl.pack(anchor="w")
        self.equity_lbl = ttk.Label(pf_frame, text="Total : —", style="Equity.TLabel")
        self.equity_lbl.pack(anchor="w", pady=(0, 8))

        cols = ("coin", "qty", "prix", "valeur")
        self.pos_tree = ttk.Treeview(pf_frame, columns=cols, show="headings", height=6)
        self.pos_tree.heading("coin", text="Coin")
        self.pos_tree.heading("qty", text="Quantite")
        self.pos_tree.heading("prix", text="Prix (USD)")
        self.pos_tree.heading("valeur", text="Valeur (USD)")
        self.pos_tree.column("coin", width=90, anchor="w")
        self.pos_tree.column("qty", width=140, anchor="e")
        self.pos_tree.column("prix", width=120, anchor="e")
        self.pos_tree.column("valeur", width=120, anchor="e")
        self.pos_tree.pack(fill="both", expand=True)

        # --- historique des trades ---
        hist_frame = ttk.LabelFrame(main, text="Historique des trades", padding=10)
        hist_frame.grid(row=1, column=1, sticky="nsew", padx=(6, 0))

        cols2 = ("time", "side", "coin", "qty", "prix", "usd")
        self.trade_tree = ttk.Treeview(hist_frame, columns=cols2, show="headings", height=12)
        self.trade_tree.heading("time", text="Date (UTC)")
        self.trade_tree.heading("side", text="Sens")
        self.trade_tree.heading("coin", text="Coin")
        self.trade_tree.heading("qty", text="Quantite")
        self.trade_tree.heading("prix", text="Prix")
        self.trade_tree.heading("usd", text="USD")
        self.trade_tree.column("time", width=160, anchor="w")
        self.trade_tree.column("side", width=60, anchor="center")
        self.trade_tree.column("coin", width=90, anchor="w")
        self.trade_tree.column("qty", width=120, anchor="e")
        self.trade_tree.column("prix", width=100, anchor="e")
        self.trade_tree.column("usd", width=100, anchor="e")
        sb = ttk.Scrollbar(hist_frame, orient="vertical", command=self.trade_tree.yview)
        self.trade_tree.configure(yscrollcommand=sb.set)
        self.trade_tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        # barre de statut en bas
        self.status_var = tk.StringVar(value="Portefeuille charge depuis " + PORTFOLIO_FILE)
        status = ttk.Label(self, textvariable=self.status_var, relief="sunken", anchor="w", padding=(8, 3))
        status.pack(fill="x", side="bottom")

    # --- actions ---

    def refresh_prices(self):
        self.status_var.set("Recuperation des prix...")
        self.update_idletasks()
        try:
            self.prices = fetch_prices()
        except Exception as e:
            self.status_var.set("Erreur recup prix : " + str(e))
            return
        for coin in self.price_labels:
            if coin in self.prices:
                p = self.prices[coin][VS_CURRENCY]
                self.price_labels[coin].config(text=f"{p:,.2f} USD")
        self.refresh_view()
        self.status_var.set("Prix mis a jour")

    def on_buy(self):
        if not self.prices:
            self.status_var.set("Clique Refresh d'abord")
            return
        coin = self.coin_var.get()
        try:
            usd = float(self.usd_var.get())
        except ValueError:
            messagebox.showerror("Erreur", "Montant USD invalide")
            return
        try:
            qty = buy(self.portfolio, coin, usd, self.prices)
        except ValueError as e:
            messagebox.showerror("Achat impossible", str(e))
            return
        save_portfolio(self.portfolio)
        self.usd_var.set("")
        self.refresh_view()
        self.status_var.set("Achete " + f"{qty:.8f}" + " " + coin + " pour " + f"{usd:,.2f}" + " USD")

    def on_sell(self):
        if not self.prices:
            self.status_var.set("Clique Refresh d'abord")
            return
        coin = self.coin_var.get()
        try:
            usd_wanted = float(self.usd_var.get())
        except ValueError:
            messagebox.showerror("Erreur", "Montant USD invalide")
            return
        # on convertit le montant USD en quantite du coin choisi
        price = self.prices[coin][VS_CURRENCY]
        qty = usd_wanted / price
        try:
            usd = sell(self.portfolio, coin, qty, self.prices)
        except ValueError as e:
            messagebox.showerror("Vente impossible", str(e))
            return
        save_portfolio(self.portfolio)
        self.usd_var.set("")
        self.refresh_view()
        self.status_var.set("Vendu " + f"{qty:.8f}" + " " + coin + " pour " + f"{usd:,.2f}" + " USD")

    def on_usd_change(self, *_):
        # conversion live : combien valent X USD dans chaque crypto
        txt = self.usd_var.get().strip()
        if not txt or not self.prices:
            for coin in self.conv_labels:
                self.conv_labels[coin].config(text="—")
            return
        try:
            usd = float(txt)
        except ValueError:
            for coin in self.conv_labels:
                self.conv_labels[coin].config(text="—")
            return
        for coin in COINS:
            if coin in self.prices:
                qty = usd / self.prices[coin][VS_CURRENCY]
                self.conv_labels[coin].config(text=f"{qty:.8f}")

    def on_sell_all(self):
        if not self.prices:
            self.status_var.set("Clique Refresh d'abord")
            return
        coin = self.coin_var.get()
        held = self.portfolio["positions"].get(coin, 0)
        if held <= 0:
            messagebox.showinfo("Rien a vendre", "Aucune position sur " + coin)
            return
        try:
            usd = sell(self.portfolio, coin, held, self.prices)
        except ValueError as e:
            messagebox.showerror("Vente impossible", str(e))
            return
        save_portfolio(self.portfolio)
        self.refresh_view()
        self.status_var.set("Tout vendu sur " + coin + " pour " + f"{usd:,.2f}" + " USD")

    def reset_portfolio(self):
        ok = messagebox.askyesno("Reset", "Remettre le portefeuille a zero ?")
        if not ok:
            return
        self.portfolio = default_portfolio()
        save_portfolio(self.portfolio)
        self.refresh_view()
        self.status_var.set("Portefeuille reset")

    def refresh_view(self):
        # cash + total
        cash = self.portfolio["cash"]
        self.cash_lbl.config(text="Cash : " + f"{cash:,.2f}" + " USD")

        # on vide le tableau des positions et on le remplit
        for row in self.pos_tree.get_children():
            self.pos_tree.delete(row)
        total_pos = 0
        for coin, qty in self.portfolio["positions"].items():
            if coin in self.prices:
                price = self.prices[coin][VS_CURRENCY]
            else:
                price = 0
            value = qty * price
            total_pos += value
            self.pos_tree.insert("", "end", values=(
                coin.capitalize(),
                f"{qty:.8f}",
                f"{price:,.2f}" if price else "—",
                f"{value:,.2f}" if price else "—",
            ))

        total = cash + total_pos
        self.equity_lbl.config(text="Total : " + f"{total:,.2f}" + " USD   (positions : " + f"{total_pos:,.2f}" + ")")

        # on vide l'historique et on le remplit (plus recent en haut)
        for row in self.trade_tree.get_children():
            self.trade_tree.delete(row)
        for t in reversed(self.portfolio["trades"]):
            self.trade_tree.insert("", "end", values=(
                t["timestamp"],
                t["side"],
                t["coin"],
                f"{t['quantity']:.8f}",
                f"{t['price']:,.2f}",
                f"{t['usd_amount']:,.2f}",
            ))


if __name__ == "__main__":
    app = TradingApp()
    app.mainloop()
