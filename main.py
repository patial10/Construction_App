from fastapi import FastAPI, HTTPException, Depends, status
from pydantic import BaseModel
from typing import List, Optional
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
from dotenv import load_dotenv
import os

load_dotenv()


app = FastAPI()

# MongoDB Client Setup
MONGO_URI = os.getenv("MONGO_UR")  # Get Mongo URI from environment
client = AsyncIOMotorClient(MONGO_URI)
db = client["webapp_db"]
customers_collection = db["customers"]

# Pydantic models for data validation

class Order(BaseModel):
    category: str  # e.g., "bricks", "sand", "concrete"
    quantity: int
    price: float

class Customer(BaseModel):
    name: str
    email: str
    phone: str
    address: str
    orders: Optional[List[Order]] = []

class CustomerInDB(Customer):
    id: str

# Helper to convert ObjectId to string
def customer_helper(customer) -> dict:
    return {
        "id": str(customer["_id"]),
        "name": customer["name"],
        "email": customer["email"],
        "phone": customer["phone"],
        "address": customer["address"],
        "orders": customer["orders"]
    }

# Route to Add a New Customer
@app.post("/customers/", response_model=CustomerInDB)
async def add_customer(customer: Customer):
    new_customer = {
        "name": customer.name,
        "email": customer.email,
        "phone": customer.phone,
        "address": customer.address,
        "orders": customer.orders if customer.orders else []
    }
    result = await customers_collection.insert_one(new_customer)
    new_customer["_id"] = result.inserted_id
    return customer_helper(new_customer)

# Route to Book an Order for a Customer
@app.post("/customers/{customer_id}/order")
async def book_order(customer_id: str, order: Order):
    customer = await customers_collection.find_one({"_id": ObjectId(customer_id)})
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")

    new_order = order.dict()
    customer["orders"].append(new_order)
    
    # Update customer with the new order
    await customers_collection.update_one(
        {"_id": ObjectId(customer_id)},
        {"$set": {"orders": customer["orders"]}}
    )
    return {"message": "Order booked successfully", "order": new_order}

# Route to View All Customers
@app.get("/customers/", response_model=List[CustomerInDB])
async def get_customers():
    customers = await customers_collection.find().to_list(100)
    return [customer_helper(cust) for cust in customers]

# Route to Edit Customer Order (for admin)
@app.put("/customers/{customer_id}/order/{order_index}")
async def edit_order(customer_id: str, order_index: int, order: Order):
    customer = await customers_collection.find_one({"_id": ObjectId(customer_id)})
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    
    if order_index >= len(customer["orders"]):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    # Modify the order at the given index
    customer["orders"][order_index] = order.dict()

    # Update the customer in the database
    await customers_collection.update_one(
        {"_id": ObjectId(customer_id)},
        {"$set": {"orders": customer["orders"]}}
    )
    return {"message": "Order updated successfully", "order": order.dict()}

# Route to Delete a Customer's Order
@app.delete("/customers/{customer_id}/order/{order_index}")
async def delete_order(customer_id: str, order_index: int):
    customer = await customers_collection.find_one({"_id": ObjectId(customer_id)})
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    
    if order_index >= len(customer["orders"]):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    # Remove the order from the list
    del customer["orders"][order_index]

    # Update the customer in the database
    await customers_collection.update_one(
        {"_id": ObjectId(customer_id)},
        {"$set": {"orders": customer["orders"]}}
    )
    return {"message": "Order deleted successfully"}

# Route to Update Amount or Price for a Customer's Order
@app.patch("/customers/{customer_id}/order/{order_index}")
async def update_order_amount(customer_id: str, order_index: int, new_price: float, new_quantity: int):
    customer = await customers_collection.find_one({"_id": ObjectId(customer_id)})
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    
    if order_index >= len(customer["orders"]):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    # Update the specific order
    customer["orders"][order_index]["quantity"] = new_quantity
    customer["orders"][order_index]["price"] = new_price

    # Update in the database
    await customers_collection.update_one(
        {"_id": ObjectId(customer_id)},
        {"$set": {"orders": customer["orders"]}}
    )
    return {"message": "Order updated successfully", "order": customer["orders"][order_index]}
