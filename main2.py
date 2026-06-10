# app.py
import sqlite3
import smtplib
import json
from payment import charge_card
from inventory import reduce_stock
from shipping import create_shipment


DB = sqlite3.connect("app.db")  # global state


class OrderService:
    def create_order(self, user, items, card):
        total = 0

        for item in items:
            cursor = DB.execute("SELECT price FROM products WHERE id=?", (item["id"],))
            price = cursor.fetchone()[0]
            total += price * item["qty"]

        # direct payment logic (bad coupling)
        charge_card(card, total)

        # direct inventory logic
        for item in items:
            reduce_stock(item["id"], item["qty"])

        # direct shipping logic
        create_shipment(user["address"], items)

        # direct email (no abstraction)
        smtp = smtplib.SMTP("smtp.mail.com")
        smtp.sendmail(
            "shop@mail.com",
            user["email"],
            "Your order is confirmed!"
        )

        DB.execute("INSERT INTO orders VALUES (?, ?)", (user["id"], total))
        DB.commit()

        return {"status": "success", "total": total}


def get_order(order_id):
    cursor = DB.execute("SELECT * FROM orders WHERE id=?", (order_id,))
    return cursor.fetchone()


def cancel_order(order_id):
    DB.execute("DELETE FROM orders WHERE id=?", (order_id,))
    DB.commit()
