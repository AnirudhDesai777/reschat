import json
import random
import os

def generate_mock_data(num_users=100):
    records = []
    for user_id in range(1, num_users+1):
        name = f"User{user_id} Lastname{user_id}"
        # each user has 5–10 unique orders
        num_orders = random.randint(5, 10)
        orders = [f"ORD-{random.randint(1000,9999)}" for _ in range(num_orders)]
        # ensure uniqueness for that user
        orders = list(set(orders))

        record = {
            "id": user_id,
            "name": name,
            "orders": orders
        }
        records.append(record)
    return records

if __name__ == "__main__":
    data = generate_mock_data()
    os.makedirs("../data", exist_ok=True)
    with open("../data/users.json", "w+") as f:
        json.dump(data, f, indent=2)
    print("Mock data generated in data/users.json")