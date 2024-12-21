import decimal
import urllib.parse
import pandas as pd
import numpy as np
import pyodbc

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
from sklearn.metrics.pairwise import cosine_similarity
from sqlalchemy import create_engine

from recommenderModel.recommenderModels import RecommenderService, ColdStartRecommender, BundleRecommender
from recommenderModel.otherModels import RecommendationRequest, RecommendationResponse, RecommendationRequestType2, ProductResponse

app = FastAPI(title="Product Recommender API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],  
    allow_headers=["*"],  
)
# Create connection string for SQLAlchemy
PARAMS = urllib.parse.quote_plus(
    "Driver={ODBC Driver 18 for SQL Server};"
    "Server=tcp:lthshop.database.windows.net,1433;"
    "Database=lthshop;"
    "Uid=lthshop;"  
    "Pwd=Ecommercewebsite2024;" 
    "Encrypt=yes;"
    "TrustServerCertificate=no;"
    "Connection Timeout=30"
)

ENGINE = create_engine(f"mssql+pyodbc:///?odbc_connect={PARAMS}")

def get_db_data(query: str, params=None):
    try:
        # Convert params list to tuple if provided
        params = tuple(params) if params else None
        # Replace @p1 style params with ? for SQLAlchemy
        query = query.replace('@p1', '?')
        df = pd.read_sql(query, ENGINE, params=params)
        return df
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching data: {str(e)}")

# Update table names to match database
cart_items_query = "SELECT * FROM CartItems"
orders_query = "SELECT * FROM Orders"
order_items_query = "SELECT * FROM OrderItems"

# Read CSV option
# cart_items = pd.read_csv("dataset/cart_data.csv")
# orders = pd.read_csv("dataset/orders.csv")
# order_items = pd.read_csv("dataset/order_items.csv")

# Read MSSQL option
cart_items = get_db_data(cart_items_query)
orders = get_db_data(orders_query)
order_items = get_db_data(order_items_query)

recommender_service = RecommenderService(cart_items, orders, order_items)
cold_start = ColdStartRecommender(orders, order_items)
bundle_recommender = BundleRecommender(orders, order_items)

def getProductByProductSizeId(id: int):
    try:
        # Query product details using ProductSizeId
        product_query = """
            SELECT p.* 
            FROM Products p
            JOIN ProductSizes ps ON p.ProductId = ps.ProductId
            WHERE ps.ProductSizeId = ?
        """
        df = get_db_data(product_query, params=[id])
        
        if df.empty:
            raise HTTPException(
                status_code=404, 
                detail=f"Product with size ID {id} not found"
            )
        
        # Convert decimal types to float for JSON serialization
        product_data = df.to_dict('records')[0]
        for key, value in product_data.items():
            if isinstance(value, decimal.Decimal):
                product_data[key] = float(value)
                
        return product_data
        
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error fetching product: {str(e)}"
        )
    
@app.post("/recommendations/")
async def get_recommendations(request: RecommendationRequest):
    results = []
    try:
        if request and request.customer_id:
            # Use existing collaborative recommendations
            recommendations = recommender_service.get_recommendations(
                request.customer_id,
                request.num_recommendations
            )
            for i in recommendations:
                results.append(ProductResponse(**getProductByProductSizeId(i)))
        elif request.customer_id is None:  
            # Use cold start recommendations
            recommendations = cold_start.get_cold_start_recommendations(request.num_recommendations)
            for i in recommendations:
                results.append(ProductResponse(**getProductByProductSizeId(i)))
        
        return {
            "customer_id": request.customer_id if request else None,
            "recommendations": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/bundle-recommendations")
async def get_bundle_recommendations(request: RecommendationRequestType2):
    results = []
    try:
        recommendations = bundle_recommender.get_bundle_recommendations(request.product_id, request.num_recommendations)
        for i in recommendations:
            results.append(ProductResponse(**getProductByProductSizeId(i)))
        return {
            "product_id": request.product_id,
            "bundle_recommendations": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

###############################
# To run: uvicorn main:app --reload
###############################