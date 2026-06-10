from container import build_order_service

def main():
    service = build_order_service()

    user = {"id": 1, "email": "user@mail.com", "address": "Cairo"}
    items = [
        {"id": 1, "name": "Book", "price": 100, "qty": 2},
        {"id": 2, "name": "Pen", "price": 20, "qty": 3}
    ]
    card = "1234-5678-9999"

    order = service.create_order(user, items, card)

    print("ORDER CREATED:", order)


if __name__ == "__main__":
    main()
