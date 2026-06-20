import asyncio
import json
from sqlalchemy import select
from db.database import AsyncSessionLocal
from models.domain import Product
from db.cache import redis_client

async def sync_erp_data_to_redis():
    """
    Simulates fetching real-time stock and prices from an ERP and
    caching them in Redis.
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Product.sku, Product.supplier_stock, Product.margin))
        products = result.all()
        
        pipeline = redis_client.pipeline()
        for sku, stock, margin in products:
            data = {
                "stock": stock,
                "margin": margin
            }
            # Cache indefinitely for MVP, or use expiry in prod
            pipeline.set(f"product_erp:{sku}", json.dumps(data))
            
        await pipeline.execute()
        print(f"Synced {len(products)} products to Redis Cache.")

if __name__ == "__main__":
    asyncio.run(sync_erp_data_to_redis())
