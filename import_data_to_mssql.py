import pandas as pd
import pyodbc
import numpy as np

CONNECTION_STRING = "DRIVER={ODBC Driver 18 for SQL Server};Server=tcp:lthshop.database.windows.net,1433;Database=lthshop;Uid=lthshop;Pwd=Ecommercewebsite2024;Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"

def convert_types(value):
    if isinstance(value, (np.int64, np.int32)):
        return int(value)
    if isinstance(value, (np.float64, np.float32)):
        return float(value)
    return value

try:
    # Read CSV files
    cart_data = pd.read_csv('cart_data.csv')
    orders = pd.read_csv('orders.csv')
    order_items = pd.read_csv('order_items.csv')

    # Connect to Azure SQL
    conn = pyodbc.connect(CONNECTION_STRING)
    cursor = conn.cursor()

    # Enable IDENTITY_INSERT and insert cart_data
    cursor.execute("SET IDENTITY_INSERT CartItems ON")
    for index, row in cart_data.iterrows():
        cursor.execute(
            "INSERT INTO CartItems (CartItemID, CustomerID, ProductSizeID, Quantity) VALUES (?, ?, ?, ?)",
            *map(convert_types, [row.CartItemID, row.CustomerID, row.ProductSizeID, row.Quantity])
        )
    cursor.execute("SET IDENTITY_INSERT CartItems OFF")

    # Enable IDENTITY_INSERT and insert orders
    cursor.execute("SET IDENTITY_INSERT Orders ON")
    for index, row in orders.iterrows():
        cursor.execute(
            """INSERT INTO Orders (OrderID, DateTime, CustomerID, PaymentType, Status, 
            TransactionID, TotalPrice) VALUES (?, ?, ?, ?, ?, ?, ?)""",
            *map(convert_types, [row.OrderID, row.DateTime, row.CustomerID, row.PaymentType, 
            row.Status, row.TransactionID, row.TotalPrice])
        )
    cursor.execute("SET IDENTITY_INSERT Orders OFF")

    # Enable IDENTITY_INSERT and insert order_items
    cursor.execute("SET IDENTITY_INSERT OrderItems ON")
    for index, row in order_items.iterrows():
        cursor.execute(
            "INSERT INTO OrderItems (OrderItemID, OrderID, ProductSizeID, Quantity) VALUES (?, ?, ?, ?)",
            *map(convert_types, [row.OrderItemID, row.OrderID, row.ProductSizeID, row.Quantity])
        )
    cursor.execute("SET IDENTITY_INSERT OrderItems OFF")

    conn.commit()
    print("Data imported successfully!")

except Exception as e:
    conn.rollback()
    print(f"Error occurred: {str(e)}")

finally:
    if 'cursor' in locals():
        cursor.close()
    if 'conn' in locals():
        conn.close()