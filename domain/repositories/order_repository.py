from dataclasses import dataclass

@dataclass
class Order:
    user_id: int
    items: list
    total: float
