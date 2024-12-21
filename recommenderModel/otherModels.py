from typing import List, Optional
from pydantic import BaseModel, Field

class RecommendationRequest(BaseModel):
    customer_id: Optional[int] = None
    num_recommendations: int = 4

class RecommendationRequestType2(BaseModel):
    product_id: int
    num_recommendations: int = 4

class RecommendationResponse(BaseModel):
    customer_id: Optional[int] = None
    recommendations: List[int]

class ProductResponse(BaseModel):
    productId: int = Field(..., alias="ProductID")
    name: str = Field(..., alias="Name") 
    brand: str = Field(..., alias="Brand")
    description: str = Field(..., alias="Description")
    imageUrl: str = Field(..., alias="ImageURL")
    categoryId: int = Field(..., alias="CategoryID")
    nameAlias: str = Field(..., alias="NameAlias")

    class Config:
        allow_population_by_field_name = True