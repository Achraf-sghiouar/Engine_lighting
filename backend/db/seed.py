import asyncio
import uuid
import random
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from db.database import DATABASE_URL, Base
from models.domain import Product, Project, ProjectLine, DecisionTrace

engine = create_async_engine(DATABASE_URL, echo=True)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

def generate_mock_products():
    brands = ["Acuity Brands", "Signify", "Eaton", "Lithonia", "Juno", "Cooper Lighting"]
    families = ["Downlight Series A", "Panel B", "HighBay X", "Outdoor Y", "Accent Z"]
    categories = ["downlight", "panel", "highbay", "outdoor", "accent"]
    mountings = ["recessed", "surface", "suspended", "wall"]
    voltages = ["120V", "277V", "120-277V", "MVOLT", "347V", "220-240V"] # EMEA uses 220-240V
    dimmings = ["0-10V", "DALI", "Phase", "None"]
    
    products = []
    
    for i in range(50):
        category = random.choice(categories)
        mounting = random.choice(mountings)
        if category == "downlight":
            mounting = "recessed"
            
        cct = random.choice([2700, 3000, 3500, 4000, 5000])
        lumens = random.choice([1000, 1500, 2000, 3000, 4000, 5000, 10000])
        cri = random.choice([80, 90, 95])
        
        voltage = random.choice(voltages)
        tier = random.choices([1, 2, 3], weights=[0.2, 0.5, 0.3])[0] # Tier 1 is premium, 2 standard, 3 value
        status = random.choices(["active", "superseded", "discontinued"], weights=[0.8, 0.1, 0.1])[0]
        
        certs = ["UL"]
        if random.random() > 0.3:
            certs.append("DLC")
        if random.random() > 0.8:
            certs.append("JA8")
        if voltage == "220-240V":
            certs = ["CE"] # EMEA product
            
        p = Product(
            id=uuid.uuid4(),
            sku=f"MOCK-SKU-{i+1:03d}-{random.randint(1000,9999)}",
            manufacturer=random.choice(brands),
            brand=random.choice(brands),
            family=random.choice(families),
            category_product_family=category,
            category_mounting_type=mounting,
            lumens=lumens,
            cct=cct,
            cri=cri,
            beam_angle=random.choice([15.0, 30.0, 45.0, 60.0, 90.0, None]),
            voltage_range=voltage,
            dimming_protocol=random.choice(dimmings),
            thd=random.choice([10.0, 15.0, 20.0]),
            power_factor=random.choice([0.9, 0.95, 0.99]),
            efficacy=random.uniform(90.0, 150.0),
            cutout_in=random.choice([4.0, 6.0, 8.0]) if category == "downlight" else None,
            ip_rating=random.choice([20, 44, 65]),
            ik_rating=random.choice([2, 5, 8, 10]) if category in ["outdoor", "highbay"] else None,
            finish=random.choice(["white", "black", "silver", None]),
            trim=random.choice(["round", "square", "flangeless", None]),
            certifications=certs,
            controls_protocols=[],
            lifecycle_status=status,
            tier=tier,
            margin=random.uniform(0.10, 0.50),
            supplier_stock=random.randint(0, 500),
            lead_time_days=random.randint(1, 45)
        )
        products.append(p)
    return products


async def init_db():
    async with engine.begin() as conn:
        # Create extension if not exists inside the session (though usually done by a superuser)
        # We will assume init.sql handles the extension, so we just create tables here.
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
        
    async with AsyncSessionLocal() as session:
        products = generate_mock_products()
        session.add_all(products)
        await session.commit()
        print(f"Seeded {len(products)} products.")

if __name__ == "__main__":
    asyncio.run(init_db())
