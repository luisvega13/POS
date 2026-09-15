from datetime import datetime
from decimal import Decimal,InvalidOperation,ROUND_HALF_UP
from sqlalchemy import func,select
from sqlalchemy.orm import Session,selectinload
from app.models import BusinessConfig,CashSession,Category,Product,Sale,SaleItem

CENT=Decimal("0.01")
PAYMENTS={"cash","card","transfer"}
class PosError(ValueError): pass
def money(value):
    try: result=Decimal(str(value)).quantize(CENT,rounding=ROUND_HALF_UP)
    except (InvalidOperation,ValueError): raise PosError("Importe no válido")
    if result < 0: raise PosError("El importe no puede ser negativo")
    return result
def product_dict(p): return {"id":p.id,"name":p.name,"price":str(p.price),"category":p.category,"active":p.active,"created_at":p.created_at.isoformat(),"updated_at":p.updated_at.isoformat()}
def sale_dict(s,details=False):
    data={"id":s.id,"folio":s.folio,"subtotal":str(s.subtotal),"total":str(s.total),"payment_method":s.payment_method,"amount_received":str(s.amount_received) if s.amount_received is not None else None,"change_amount":str(s.change_amount) if s.change_amount is not None else None,"created_at":s.created_at.isoformat(),"cash_session_id":s.cash_session_id}
    if details: data["items"]=[{"id":i.id,"product_id":i.product_id,"product_name":i.product_name,"unit_price":str(i.unit_price),"quantity":i.quantity,"subtotal":str(i.subtotal)} for i in s.items]
    return data

def category_dict(c): return {"id":c.id,"name":c.name,"active":c.active,"created_at":c.created_at.isoformat(),"updated_at":c.updated_at.isoformat()}
class CategoryService:
    @staticmethod
    def ensure(db):
        names={name for name in db.scalars(select(Product.category).distinct()) if name}
        names.add("General"); existing={name.casefold() for name in db.scalars(select(Category.name))}
        for name in sorted(names):
            if name.casefold() not in existing: db.add(Category(name=name))
        db.commit()
    @staticmethod
    def list(db,active_only=True):
        q=select(Category)
        if active_only: q=q.where(Category.active.is_(True))
        return [category_dict(c) for c in db.scalars(q.order_by(Category.name))]
    @staticmethod
    def create(db,name):
        value=name.strip()
        if not value: raise PosError("El nombre de la categoría es obligatorio")
        if db.scalar(select(Category).where(func.lower(Category.name)==value.casefold())): raise PosError("La categoría ya existe")
        c=Category(name=value); db.add(c); db.commit(); db.refresh(c); return category_dict(c)
    @staticmethod
    def update(db,cid,name):
        c=db.get(Category,cid)
        if not c: raise PosError("Categoría no encontrada")
        value=name.strip()
        if not value: raise PosError("El nombre de la categoría es obligatorio")
        duplicate=db.scalar(select(Category).where(func.lower(Category.name)==value.casefold(),Category.id!=cid))
        if duplicate: raise PosError("La categoría ya existe")
        old=c.name; c.name=value; c.updated_at=datetime.now()
        db.query(Product).filter(Product.category==old).update({Product.category:value},synchronize_session=False)
        db.commit(); db.refresh(c); return category_dict(c)
    @staticmethod
    def delete(db,cid):
        c=db.get(Category,cid)
        if not c: raise PosError("Categoría no encontrada")
        count=db.scalar(select(func.count(Product.id)).where(Product.category==c.name))
        if count: raise PosError(f"No se puede eliminar: contiene {count} producto(s)")
        db.delete(c); db.commit()
    @staticmethod
    def require(db,name):
        value=name.strip() or "General"
        if not db.scalar(select(Category).where(Category.name==value,Category.active.is_(True))): raise PosError("La categoría seleccionada no existe")
        return value

class ProductService:
    @staticmethod
    def list(db,search="",category=None,active_only=True):
        q=select(Product)
        if active_only: q=q.where(Product.active.is_(True))
        if search: q=q.where(Product.name.ilike(f"%{search.strip()}%"))
        if category: q=q.where(Product.category==category)
        return [product_dict(x) for x in db.scalars(q.order_by(Product.category,Product.name))]
    @staticmethod
    def create(db,data):
        name=data.name.strip()
        if not name: raise PosError("El nombre es obligatorio")
        p=Product(name=name,price=money(data.price),category=CategoryService.require(db,data.category),active=data.active)
        db.add(p); db.commit(); db.refresh(p); return product_dict(p)
    @staticmethod
    def update(db,pid,data):
        p=db.get(Product,pid)
        if not p: raise PosError("Producto no encontrado")
        values=data.model_dump(exclude_unset=True) if hasattr(data,"model_dump") else data.dict(exclude_unset=True)
        if "name" in values:
            values["name"]=values["name"].strip()
            if not values["name"]: raise PosError("El nombre es obligatorio")
        if "price" in values: values["price"]=money(values["price"])
        if "category" in values: values["category"]=CategoryService.require(db,values["category"])
        for key,value in values.items(): setattr(p,key,value)
        p.updated_at=datetime.now(); db.commit(); db.refresh(p); return product_dict(p)

class CashService:
    @staticmethod
    def current(db): return db.scalar(select(CashSession).where(CashSession.closed_at.is_(None)).order_by(CashSession.id.desc()))
    @classmethod
    def open(cls,db,amount):
        if cls.current(db): raise PosError("Ya existe una caja abierta")
        session=CashSession(opening_amount=money(amount)); db.add(session); db.commit(); db.refresh(session); return session
    @classmethod
    def summary(cls,db,session=None):
        session=session or cls.current(db)
        if not session: raise PosError("No hay una caja abierta")
        rows=db.execute(select(Sale.payment_method,func.coalesce(func.sum(Sale.total),0),func.count(Sale.id)).where(Sale.cash_session_id==session.id).group_by(Sale.payment_method)).all()
        totals={"cash":Decimal("0"),"card":Decimal("0"),"transfer":Decimal("0")}; operations=0
        for method,total,count in rows: totals[method]=money(total); operations+=count
        sold=sum(totals.values(),Decimal("0")); expected=money(session.opening_amount+totals["cash"])
        return {"id":session.id,"opened_at":session.opened_at.isoformat(),"closed_at":session.closed_at.isoformat() if session.closed_at else None,"opening_amount":str(session.opening_amount),"operations":operations,"cash":str(totals["cash"]),"card":str(totals["card"]),"transfer":str(totals["transfer"]),"total_sold":str(money(sold)),"expected_cash":str(expected)}
    @classmethod
    def close(cls,db):
        session=cls.current(db)
        if not session: raise PosError("No hay una caja abierta")
        summary=cls.summary(db,session); session.closed_at=datetime.now(); db.commit(); summary["closed_at"]=session.closed_at.isoformat(); return summary

class SaleService:
    @staticmethod
    def create(db: Session,payload):
        cash=CashService.current(db)
        if not cash: raise PosError("Debe abrir caja antes de vender")
        if not payload.items: raise PosError("La venta no contiene productos")
        quantities={}
        for item in payload.items:
            if item.quantity < 1: raise PosError("Las cantidades deben ser mayores que cero")
            quantities[item.product_id]=quantities.get(item.product_id,0)+item.quantity
        products={p.id:p for p in db.scalars(select(Product).where(Product.id.in_(quantities),Product.active.is_(True)))}
        if len(products)!=len(quantities): raise PosError("Uno o más productos no están disponibles")
        total=sum((money(products[pid].price)*qty for pid,qty in quantities.items()),Decimal("0")).quantize(CENT)
        method=payload.payment_method.lower()
        if method not in PAYMENTS: raise PosError("Método de pago no válido")
        received=money(payload.amount_received) if payload.amount_received is not None else None
        if method=="cash":
            if received is None or received < total: raise PosError("El efectivo recibido es menor al total")
            change=money(received-total)
        else: received=None; change=None
        try:
            last=db.scalar(select(Sale.folio).order_by(Sale.id.desc()).limit(1)); folio=f"{int(last or '0')+1:06d}"
            sale=Sale(folio=folio,cash_session_id=cash.id,subtotal=total,total=total,payment_method=method,amount_received=received,change_amount=change)
            db.add(sale); db.flush()
            for pid,qty in quantities.items():
                p=products[pid]; subtotal=(money(p.price)*qty).quantize(CENT)
                db.add(SaleItem(sale_id=sale.id,product_id=p.id,product_name=p.name,unit_price=money(p.price),quantity=qty,subtotal=subtotal))
            db.commit()
        except Exception:
            db.rollback(); raise
        return SaleService.get(db,sale.id)
    @staticmethod
    def get(db,sid):
        sale=db.scalar(select(Sale).options(selectinload(Sale.items)).where(Sale.id==sid))
        if not sale: raise PosError("Venta no encontrada")
        return sale
    @staticmethod
    def list(db,limit=200): return [sale_dict(x) for x in db.scalars(select(Sale).order_by(Sale.id.desc()).limit(limit))]
    @staticmethod
    def product_report(db,date_from=None,date_to=None):
        q=select(SaleItem.product_id,SaleItem.product_name,func.sum(SaleItem.quantity),func.sum(SaleItem.subtotal),func.count(func.distinct(SaleItem.sale_id))).join(Sale,Sale.id==SaleItem.sale_id)
        if date_from: q=q.where(Sale.created_at>=date_from)
        if date_to: q=q.where(Sale.created_at<date_to)
        rows=db.execute(q.group_by(SaleItem.product_id,SaleItem.product_name).order_by(func.sum(SaleItem.quantity).desc(),SaleItem.product_name)).all()
        products=[{"product_id":pid,"product_name":name,"quantity":int(qty),"revenue":str(money(revenue)),"sales_count":int(count)} for pid,name,qty,revenue,count in rows]
        return {"total_units":sum(x["quantity"] for x in products),"distinct_products":len(products),"total_revenue":str(money(sum((Decimal(x["revenue"]) for x in products),Decimal("0")))),"products":products}

def config_dict(c): return {"business_name":c.business_name,"address":c.address,"phone":c.phone,"ticket_message":c.ticket_message,"printer_name":c.printer_name,"encoding":c.encoding,"character_table":c.character_table}
def get_business_config(db):
    c=db.get(BusinessConfig,1)
    if not c: c=BusinessConfig(id=1); db.add(c); db.commit(); db.refresh(c)
    return c
