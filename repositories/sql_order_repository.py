class OrderRepository:
    def save(self, order):
        raise NotImplementedError

    def get(self, order_id):
        raise NotImplementedError
