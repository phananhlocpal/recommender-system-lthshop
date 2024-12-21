import pyodbc

def test_azure_sql_connection():
    CONNECTION_STRING = "DRIVER={ODBC Driver 18 for SQL Server};Server=tcp:lthshop.database.windows.net,1433;Database=lthshop;Uid=lthshop;Pwd=Ecommercewebsite2024;Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"
       
    try:
        print("Attempting to connect to Azure SQL...")
        conn = pyodbc.connect(CONNECTION_STRING)
        
        cursor = conn.cursor()
        cursor.execute("SELECT @@VERSION")
        row = cursor.fetchone()
        
        print("✅ Connection successful!")
        print(f"Server version: {row[0]}")
        
        cursor.close()
        conn.close()
        
    except pyodbc.Error as err:
        print("❌ Connection failed!")
        print(f"Error: {err}")
        print("Error details:", err.args[1] if len(err.args) > 1 else "No additional details")

if __name__ == "__main__":
    test_azure_sql_connection()