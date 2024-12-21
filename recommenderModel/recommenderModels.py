from datetime import timedelta, datetime
from sklearn.metrics.pairwise import cosine_similarity
from typing import List
import pandas as pd
import numpy as np
from collections import defaultdict
from typing import List, Dict

class RecommenderService:
    def __init__(self, cart_items, orders, order_items):
        self.cart_data = cart_items
        self.orders = orders
        self.order_items = order_items
        self.prepare_data()

    def prepare_data(self):
        order_interactions = self.order_items.merge(
            self.orders[['OrderID', 'CustomerID']],
            on='OrderID'
        )
        self.all_interactions = pd.concat([
            self.cart_data[['CustomerID', 'ProductSizeID', 'Quantity']],
            order_interactions[['CustomerID', 'ProductSizeID', 'Quantity']]
        ])
        self.user_item_matrix = self.all_interactions.pivot_table(
            index='CustomerID',
            columns='ProductSizeID',
            values='Quantity',
            aggfunc='sum',
            fill_value=0
        )
        self.popularity_scores = self.all_interactions.groupby('ProductSizeID')['Quantity'].sum()

    def get_recommendations(self, customer_id: int, n_recommendations: int = 4) -> List[int]:
        recommendations = self._get_collaborative_recommendations(customer_id, n_recommendations)
        if len(recommendations) < n_recommendations:
            popular_items = self._get_popular_items(
                n=n_recommendations - len(recommendations),
                exclude_items=recommendations
            )
            recommendations.extend(popular_items)
        return recommendations[:n_recommendations]

    def _get_collaborative_recommendations(self, customer_id: int, n: int) -> List[int]:
        if customer_id not in self.user_item_matrix.index:
            return []
        item_similarity = cosine_similarity(self.user_item_matrix.T)
        user_profile = self.user_item_matrix.loc[customer_id]
        scores = np.dot(item_similarity, user_profile)
        recommendations = pd.Series(scores, index=self.user_item_matrix.columns)
        return recommendations.nlargest(n).index.tolist()

    def _get_popular_items(self, n: int, exclude_items: List[int]) -> List[int]:
        return self.popularity_scores[~self.popularity_scores.index.isin(exclude_items)].nlargest(n).index.tolist()

class ColdStartRecommender:
    def __init__(self, orders, order_items):
        self.orders = orders
        self.order_items = order_items
        self.cached_recommendations = {}
        self.last_cache_time = None
        self.cache_duration = timedelta(minutes=30)
        self.prepare_data()

    def prepare_data(self):
        # Convert and index DateTime
        self.orders['DateTime'] = pd.to_datetime(self.orders['DateTime'])
        
        # Pre-merge data once
        self.full_data = self.order_items.merge(
            self.orders[['OrderID', 'DateTime', 'Status']],
            on='OrderID'
        )
        
        # Pre-filter successful orders
        self.full_data = self.full_data[
            self.full_data['Status'].isin([3, 4])
        ]
        
        # Pre-calculate popularity scores
        self.popularity_scores = self.full_data.groupby('ProductSizeID')['Quantity'].sum()
        
        # Sort DateTime for faster filtering
        self.full_data = self.full_data.sort_values('DateTime')

    def get_trending_items(self, days=100, n=4):
        # Get recent orders
        recent_date = datetime.now() - timedelta(days=days)
        recent_orders = self.full_data[
            self.full_data['DateTime'] >= recent_date
        ]

        # Calculate trending scores
        trending_scores = recent_orders.groupby('ProductSizeID')['Quantity'].sum()
        return trending_scores.nlargest(n).index.tolist()

    def get_seasonal_items(self, n=4):
        # Get current month
        current_month = datetime.now().month

        # Filter orders from same month in previous years
        seasonal_orders = self.full_data[
            self.full_data['DateTime'].dt.month == current_month
        ]

        seasonal_scores = seasonal_orders.groupby('ProductSizeID')['Quantity'].sum()
        return seasonal_scores.nlargest(n).index.tolist()

    def get_popularity_items(self, n=4):
        popularity_scores = self.full_data.groupby('ProductSizeID')['Quantity'].sum()
        return popularity_scores.nlargest(n).index.tolist()

    def get_cold_start_recommendations(self, n_recommendations=4):
        # Debug data availability
        print(f"Total orders: {len(self.full_data)}")
        
        # Get base recommendations with larger numbers
        trending = self.get_trending_items(n=n_recommendations*2)
        print(f"Trending items: {trending}")
        
        seasonal = self.get_seasonal_items(n=n_recommendations*2)
        print(f"Seasonal items: {seasonal}")
        
        # Ensure we get enough popular items
        popular = self.get_popularity_items(n=n_recommendations*2)
        print(f"Popular items: {popular}")
        
        # Combine all sources
        all_recommendations = []
        
        # Add items from each source
        for items in [trending, seasonal, popular]:
            for item in items:
                if item not in all_recommendations:
                    all_recommendations.append(item)
        
        # Fallback to most popular if not enough items
        if len(all_recommendations) < n_recommendations:
            print("Not enough items, adding from popularity scores")
            popularity_backup = list(self.popularity_scores.nlargest(n_recommendations*3).index)
            for item in popularity_backup:
                if item not in all_recommendations:
                    all_recommendations.append(item)
                    if len(all_recommendations) >= n_recommendations:
                        break
        
        print(f"Final recommendations: {all_recommendations[:n_recommendations]}")
        return all_recommendations[:n_recommendations]

class BundleRecommender:
    def __init__(self, orders, order_items):
        self.orders = orders
        self.order_items = order_items
        self.prepare_data()

    def prepare_data(self):
        # Merge orders with items
        self.order_products = self.order_items.merge(
            self.orders[['OrderID', 'Status']],
            on='OrderID'
        )

        # Filter successful orders
        self.order_products = self.order_products[
            self.order_products['Status'].isin([3, 4])
        ]

        # Create product pairs
        self.product_pairs = self._create_product_pairs()

    def _create_product_pairs(self) -> Dict:
        pairs = defaultdict(lambda: defaultdict(int))
        product_freq = defaultdict(int)

        # Group by order
        order_groups = self.order_products.groupby('OrderID')['ProductSizeID'].agg(list)

        # Count co-occurrences
        for products in order_groups:
            for p1 in products:
                product_freq[p1] += 1
                for p2 in products:
                    if p1 != p2:
                        pairs[p1][p2] += 1

        # Calculate confidence scores
        confidence_scores = defaultdict(dict)
        for p1 in pairs:
            for p2 in pairs[p1]:
                confidence = pairs[p1][p2] / product_freq[p1]
                confidence_scores[p1][p2] = confidence

        return confidence_scores

    def get_bundle_recommendations(self, product_id: int, n_recommendations: int = 4) -> List[int]:
        if product_id not in self.product_pairs:
            return []

        # Sort products by confidence score
        recommendations = sorted(
            self.product_pairs[product_id].items(),
            key=lambda x: x[1],
            reverse=True
        )

        return [prod_id for prod_id, _ in recommendations[:n_recommendations]]