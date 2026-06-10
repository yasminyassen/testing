import sqlite3

from repositories.sql_order_repository import SQLOrderRepository
from services.order_service import OrderService
from services.payment_service import PaymentService
from services.inventory_service import InventoryService
from services.shipping_service import ShippingService
from services.email_service import EmailService


def build_order_service():
    db = sqlite3.connect("app.db")

    repo = SQLOrderRepository(db)

    return OrderService(
        repo=repo,
        payment=PaymentService(),
        inventory=InventoryService(),
        shipping=ShippingService(),
        email=EmailService()
    )
