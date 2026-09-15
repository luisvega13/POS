from decimal import Decimal
from sqlalchemy import select
from app.database import SessionLocal,init_db
from app.models import Product
from app.services.pos_service import CategoryService

PRODUCTS=[("Coca Cola","25.00","Bebidas"),("Agua","20.00","Bebidas"),("Hamburguesa","80.00","Comida"),("Papas","40.00","Comida")]
def main():
    init_db()
    with SessionLocal() as db:
        CategoryService.ensure(db)
        for category in ("Bebidas","Comida"):
            try: CategoryService.create(db,category)
            except ValueError: pass
        existing={x.casefold() for x in db.scalars(select(Product.name))}; added=0
        for name,price,category in PRODUCTS:
            if name.casefold() not in existing:
                db.add(Product(name=name,price=Decimal(price),category=category)); added+=1
        db.commit(); print(f"Productos agregados: {added}")
if __name__=="__main__": main()
