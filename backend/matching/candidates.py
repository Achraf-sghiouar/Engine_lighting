from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.domain import Product
from models.schemas import PRO

async def get_candidates(db: AsyncSession, pro: PRO):
    """
    Candidate Generation (MVP)
    Fetches up to 50 candidates that could potentially match.
    In a real system, this would use pgvector or cross-references.
    For MVP, we fetch all products and rely on hard filters, 
    or just filter by category if specified.
    """
    query = select(Product)
    if pro.category:
        # Simple ILIKE search for category or family
        query = query.where(Product.category_product_family.ilike(f"%{pro.category}%"))
    
    result = await db.execute(query)
    candidates = result.scalars().all()
    
    # If no category match, fetch everything to let filters do the job
    if not candidates:
        result = await db.execute(select(Product))
        candidates = result.scalars().all()
        
    return candidates
