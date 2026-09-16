from datetime import datetime
from decimal import Decimal,InvalidOperation,ROUND_HALF_UP
from sqlalchemy import func,select
from sqlalchemy.orm import Session,selectinload
from app.models import BusinessConfig,CashCharge,CashSession,Category,DiningTable,DiningTableItem,PermissionConfig,Product,Sale,SaleItem,TableItemCancellation,TableItemTransfer,User

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
    tip=money(s.tip_amount or 0); data={"id":s.id,"folio":s.folio,"subtotal":str(s.subtotal),"total":str(s.total),"discount_amount":str(s.discount_amount or 0),"discount_reason":s.discount_reason or "","tip_amount":str(tip),"tip_method":s.tip_method,"service_charge_percent":s.service_charge_percent or 0,"grand_total":str(money(s.total+tip)),"guest_count":s.guest_count or 0,"payment_method":s.payment_method,"amount_received":str(s.amount_received) if s.amount_received is not None else None,"change_amount":str(s.change_amount) if s.change_amount is not None else None,"created_at":s.created_at.isoformat(),"cash_session_id":s.cash_session_id}
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
        tip_rows=db.execute(select(Sale.tip_method,func.coalesce(func.sum(Sale.tip_amount),0)).where(Sale.cash_session_id==session.id,Sale.tip_amount>0).group_by(Sale.tip_method)).all()
        tips={"cash":Decimal("0"),"card":Decimal("0"),"transfer":Decimal("0")}
        for method,total in tip_rows:
            if method in tips:tips[method]=money(total)
        sold=sum(totals.values(),Decimal("0"));total_tips=sum(tips.values(),Decimal("0"));charges=money(db.scalar(select(func.coalesce(func.sum(CashCharge.amount),0)).where(CashCharge.cash_session_id==session.id)) or 0)
        cancelled=int(db.scalar(select(func.count(DiningTable.id)).where(DiningTable.cash_session_id==session.id,DiningTable.status=="cancelled")) or 0)
        discounted=int(db.scalar(select(func.count(Sale.id)).where(Sale.cash_session_id==session.id,Sale.discount_amount>0)) or 0)
        total_discounts=money(db.scalar(select(func.coalesce(func.sum(Sale.discount_amount),0)).where(Sale.cash_session_id==session.id)) or 0)
        guests=int(db.scalar(select(func.coalesce(func.sum(Sale.guest_count),0)).where(Sale.cash_session_id==session.id)) or 0)
        average=money(sold/operations) if operations else Decimal("0");grand=money(sold+total_tips);paid_tips=money(tips["card"]+tips["transfer"]);total_collected=money(session.opening_amount+totals["cash"]);expected=money(total_collected-paid_tips-charges)
        declared_cash=money(session.declared_cash) if session.declared_cash is not None else None;declared_card=money(session.declared_card) if session.declared_card is not None else None;declared_transfer=money(session.declared_transfer) if session.declared_transfer is not None else None
        variance=(declared_cash-expected).quantize(CENT,rounding=ROUND_HALF_UP) if declared_cash is not None else None
        net_total=(total_collected-paid_tips-charges).quantize(CENT,rounding=ROUND_HALF_UP)
        return {"id":session.id,"opened_at":session.opened_at.isoformat(),"closed_at":session.closed_at.isoformat() if session.closed_at else None,"opening_amount":str(session.opening_amount),"operations":operations,"cash":str(totals["cash"]),"card":str(totals["card"]),"transfer":str(totals["transfer"]),"tip_cash":str(tips["cash"]),"tip_card":str(tips["card"]),"tip_transfer":str(tips["transfer"]),"total_tips":str(money(total_tips)),"paid_tips":str(paid_tips),"total_sold":str(money(sold)),"grand_total":str(grand),"total_collected":str(total_collected),"charges":str(charges),"net_total":str(net_total),"expected_cash":str(expected),"cancelled_accounts":cancelled,"discounted_accounts":discounted,"total_discounts":str(total_discounts),"average_consumption":str(average),"guests":guests,"declared_cash":str(declared_cash) if declared_cash is not None else None,"declared_card":str(declared_card) if declared_card is not None else None,"declared_transfer":str(declared_transfer) if declared_transfer is not None else None,"declared_total":str(money((declared_cash or 0)+(declared_card or 0)+(declared_transfer or 0))) if declared_cash is not None else None,"cash_variance":str(variance) if variance is not None else None,"reopened_count":session.reopened_count or 0,"last_reopened_at":session.last_reopened_at.isoformat() if session.last_reopened_at else None,"last_reopened_by":session.last_reopened_by or "","last_reopen_reason":session.last_reopen_reason or ""}
    @classmethod
    def history(cls,db,page=1,page_size=10):
        total=int(db.scalar(select(func.count(CashSession.id)).where(CashSession.closed_at.is_not(None))) or 0)
        sessions=db.scalars(select(CashSession).where(CashSession.closed_at.is_not(None)).order_by(CashSession.closed_at.desc()).offset((page-1)*page_size).limit(page_size))
        return {"items":[cls.summary(db,session) for session in sessions],"total":total,"page":page,"page_size":page_size}
    @classmethod
    def get(cls,db,session_id):
        session=db.get(CashSession,session_id)
        if not session:raise PosError("Corte de caja no encontrado")
        return session
    @classmethod
    def reopen(cls,db,session_id,user,reason):
        if cls.current(db):raise PosError("Cierra la caja actual antes de reabrir otro corte")
        session=cls.get(db,session_id)
        if session.closed_at is None:raise PosError("El corte ya está abierto")
        value=reason.strip()
        if len(value)<3:raise PosError("Indica el motivo de la reapertura")
        session.closed_at=None;session.declared_cash=None;session.declared_card=None;session.declared_transfer=None
        session.reopened_count=(session.reopened_count or 0)+1;session.last_reopened_at=datetime.now();session.last_reopened_by=user.display_name;session.last_reopen_reason=value
        db.commit();db.refresh(session);return cls.summary(db,session)
    @classmethod
    def close(cls,db,declared_cash=0,declared_card=0,declared_transfer=0):
        session=cls.current(db)
        if not session: raise PosError("No hay una caja abierta")
        session.declared_cash=money(declared_cash);session.declared_card=money(declared_card);session.declared_transfer=money(declared_transfer);session.closed_at=datetime.now();db.commit();return cls.summary(db,session)
    @classmethod
    def add_charge(cls,db,amount,concept,user):
        session=cls.current(db)
        if not session:raise PosError("No hay una caja abierta")
        value=concept.strip()
        if not value:raise PosError("El concepto del cargo es obligatorio")
        charge_amount=money(amount)
        available=Decimal(cls.summary(db,session)["expected_cash"])
        if charge_amount>available:raise PosError("El cargo supera el efectivo disponible")
        charge=CashCharge(cash_session_id=session.id,amount=charge_amount,concept=value,created_by_id=user.id,created_by_name=user.display_name);db.add(charge);db.commit();db.refresh(charge)
        return {"id":charge.id,"amount":str(charge.amount),"concept":charge.concept,"created_by":charge.created_by_name,"created_at":charge.created_at.isoformat()}

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
        subtotal=sum((money(products[pid].price)*qty for pid,qty in quantities.items()),Decimal("0")).quantize(CENT)
        discount=money(getattr(payload,"discount_amount",0) or 0)
        if discount>subtotal:raise PosError("El descuento no puede superar el consumo")
        total=money(subtotal-discount);discount_reason=(getattr(payload,"discount_reason","") or "").strip()
        if discount>0 and not discount_reason:raise PosError("Indica el motivo del descuento")
        method=payload.payment_method.lower()
        if method not in PAYMENTS: raise PosError("Método de pago no válido")
        permissions=db.get(PermissionConfig,1)
        tip=money(total*Decimal(permissions.service_charge_percent)/Decimal(100)) if permissions and permissions.include_tip_in_ticket else money(getattr(payload,"tip_amount",0) or 0)
        tip_method=(getattr(payload,"tip_method",None) or method).lower() if tip>0 else None
        if tip_method and tip_method not in PAYMENTS: raise PosError("Método de propina no válido")
        received=money(payload.amount_received) if payload.amount_received is not None else None
        cash_due=(total if method=="cash" else Decimal("0"))+(tip if tip_method=="cash" else Decimal("0"))
        if cash_due>0:
            if received is None or received < cash_due: raise PosError("El efectivo recibido es menor al total en efectivo")
            change=money(received-cash_due)
        else: received=None; change=None
        try:
            last=db.scalar(select(Sale.folio).order_by(Sale.id.desc()).limit(1)); folio=f"{int(last or '0')+1:06d}"
            sale=Sale(folio=folio,cash_session_id=cash.id,subtotal=subtotal,total=total,discount_amount=discount,discount_reason=discount_reason,payment_method=method,amount_received=received,change_amount=change,tip_amount=tip,tip_method=tip_method,service_charge_percent=permissions.service_charge_percent if permissions and permissions.include_tip_in_ticket else 0,guest_count=getattr(payload,"guest_count",0) or 0)
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
    def paginated(db,page=1,page_size=10,date_from=None,date_to=None):
        filters=[]
        if date_from:filters.append(Sale.created_at>=date_from)
        if date_to:filters.append(Sale.created_at<date_to)
        total=db.scalar(select(func.count(Sale.id)).where(*filters)) or 0
        query=select(Sale).where(*filters).order_by(Sale.id.desc()).offset((page-1)*page_size).limit(page_size)
        return {"items":[sale_dict(row) for row in db.scalars(query)],"total":int(total),"page":page,"page_size":page_size}
    @staticmethod
    def product_report(db,date_from=None,date_to=None,category=None):
        category_value=func.coalesce(Product.category,"General")
        q=select(SaleItem.product_id,SaleItem.product_name,category_value,func.sum(SaleItem.quantity),func.sum(SaleItem.subtotal),func.count(func.distinct(SaleItem.sale_id))).join(Sale,Sale.id==SaleItem.sale_id).outerjoin(Product,Product.id==SaleItem.product_id)
        if date_from: q=q.where(Sale.created_at>=date_from)
        if date_to: q=q.where(Sale.created_at<date_to)
        if category:q=q.where(Product.category==category)
        rows=db.execute(q.group_by(SaleItem.product_id,SaleItem.product_name,category_value).order_by(func.sum(SaleItem.quantity).desc(),SaleItem.product_name)).all()
        products=[{"product_id":pid,"product_name":name,"category":product_category,"quantity":int(qty),"revenue":str(money(revenue)),"sales_count":int(count)} for pid,name,product_category,qty,revenue,count in rows]
        visitors_q=select(func.coalesce(func.sum(Sale.guest_count),0))
        if date_from: visitors_q=visitors_q.where(Sale.created_at>=date_from)
        if date_to: visitors_q=visitors_q.where(Sale.created_at<date_to)
        return {"total_units":sum(x["quantity"] for x in products),"distinct_products":len(products),"total_revenue":str(money(sum((Decimal(x["revenue"]) for x in products),Decimal("0")))),"total_visitors":int(db.scalar(visitors_q) or 0),"products":products}

def dining_table_dict(table):
    items=[{"id":item.id,"product_id":item.product_id,"product_name":item.product_name,"unit_price":str(item.unit_price),"quantity":item.quantity,"subtotal":str(money(item.unit_price*item.quantity)),"added_at":item.added_at.isoformat()} for item in table.items]
    return {"id":table.id,"name":table.name,"status":table.status,"guest_count":table.guest_count or 0,"assigned_waiter_id":table.assigned_waiter_id,"assigned_waiter_name":table.assigned_waiter_name or "","opened_at":table.opened_at.isoformat(),"updated_at":table.updated_at.isoformat(),"closed_at":table.closed_at.isoformat() if table.closed_at else None,"total":str(money(sum((Decimal(item["subtotal"]) for item in items),Decimal("0")))),"items":items}

class DiningTableService:
    @staticmethod
    def list(db,user=None):
        query=select(DiningTable).options(selectinload(DiningTable.items)).where(DiningTable.status=="open").order_by(DiningTable.opened_at)
        if user and user.role=="waiter": query=query.where(DiningTable.assigned_waiter_id==user.id)
        return [dining_table_dict(table) for table in db.scalars(query)]
    @staticmethod
    def get(db,table_id,user=None):
        table=db.scalar(select(DiningTable).options(selectinload(DiningTable.items)).where(DiningTable.id==table_id,DiningTable.status=="open"))
        if not table: raise PosError("Mesa abierta no encontrada")
        if user and user.role=="waiter" and table.assigned_waiter_id!=user.id: raise PosError("No tienes acceso a esta mesa")
        return table
    @staticmethod
    def create(db,name,guest_count=0,user=None,waiter_id=None):
        value=name.strip()
        if not value: raise PosError("El nombre de la mesa es obligatorio")
        duplicate=db.scalar(select(DiningTable).where(func.lower(DiningTable.name)==value.casefold(),DiningTable.status=="open"))
        if duplicate: raise PosError("Ya existe una mesa abierta con ese nombre")
        waiter=user if user and user.role=="waiter" else db.get(User,waiter_id) if waiter_id else None
        if (user is not None or waiter_id is not None) and (not waiter or not waiter.active or waiter.role!="waiter"): raise PosError("Selecciona un mesero activo")
        cash=CashService.current(db)
        table=DiningTable(name=value,guest_count=guest_count,assigned_waiter_id=waiter.id if waiter else None,assigned_waiter_name=waiter.display_name if waiter else "",cash_session_id=cash.id if cash else None); db.add(table); db.commit(); db.refresh(table)
        return dining_table_dict(DiningTableService.get(db,table.id))
    @staticmethod
    def assign_waiter(db,table_id,waiter_id):
        table=DiningTableService.get(db,table_id)
        waiter=db.get(User,waiter_id)
        if not waiter or not waiter.active or waiter.role!="waiter": raise PosError("Mesero activo no encontrado")
        table.assigned_waiter_id=waiter.id;table.assigned_waiter_name=waiter.display_name;table.updated_at=datetime.now();db.commit()
        return dining_table_dict(DiningTableService.get(db,table.id))
    @staticmethod
    def save_items(db,table_id,items):
        table=DiningTableService.get(db,table_id); quantities={}
        for item in items:
            if item.quantity < 1: raise PosError("Las cantidades deben ser mayores que cero")
            quantities[item.product_id]=quantities.get(item.product_id,0)+item.quantity
        products={p.id:p for p in db.scalars(select(Product).where(Product.id.in_(quantities),Product.active.is_(True)))} if quantities else {}
        if len(products)!=len(quantities): raise PosError("Uno o más productos no están disponibles")
        table.items.clear()
        for product_id,quantity in quantities.items():
            product=products[product_id]; table.items.append(DiningTableItem(product_id=product.id,product_name=product.name,unit_price=money(product.price),quantity=quantity))
        table.updated_at=datetime.now(); db.commit()
        return dining_table_dict(DiningTableService.get(db,table.id))
    @staticmethod
    def add_items(db,table_id,items):
        table=DiningTableService.get(db,table_id); quantities={}
        for item in items:
            if item.quantity < 1: raise PosError("Las cantidades deben ser mayores que cero")
            quantities[item.product_id]=quantities.get(item.product_id,0)+item.quantity
        if not quantities: raise PosError("No hay productos por agregar")
        products={p.id:p for p in db.scalars(select(Product).where(Product.id.in_(quantities),Product.active.is_(True)))}
        if len(products)!=len(quantities): raise PosError("Uno o más productos no están disponibles")
        added_at=datetime.now()
        for product_id,quantity in quantities.items():
            product=products[product_id]; table.items.append(DiningTableItem(product_id=product.id,product_name=product.name,unit_price=money(product.price),quantity=quantity,added_at=added_at))
        table.updated_at=added_at; db.commit()
        return dining_table_dict(DiningTableService.get(db,table.id))
    @staticmethod
    def cancel_item(db,table_id,item_id,quantity,reason,user):
        table=DiningTableService.get(db,table_id); item=next((row for row in table.items if row.id==item_id),None)
        if not item: raise PosError("Producto de la mesa no encontrado")
        if quantity<1 or quantity>item.quantity: raise PosError("Cantidad a cancelar no válida")
        value=reason.strip()
        if not value: raise PosError("El motivo de cancelación es obligatorio")
        db.add(TableItemCancellation(table_id=table.id,product_id=item.product_id,product_name=item.product_name,unit_price=item.unit_price,quantity=quantity,reason=value,cancelled_by_id=user.id,cancelled_by_name=user.display_name))
        if quantity==item.quantity: db.delete(item)
        else:item.quantity-=quantity
        table.updated_at=datetime.now();db.commit();return dining_table_dict(DiningTableService.get(db,table.id))
    @staticmethod
    def cancellations(db,table_id):
        DiningTableService.get(db,table_id)
        rows=db.scalars(select(TableItemCancellation).where(TableItemCancellation.table_id==table_id).order_by(TableItemCancellation.cancelled_at.desc()))
        return [{"id":row.id,"product_name":row.product_name,"quantity":row.quantity,"amount":str(money(row.unit_price*row.quantity)),"reason":row.reason,"cancelled_by":row.cancelled_by_name,"cancelled_at":row.cancelled_at.isoformat()} for row in rows]
    @staticmethod
    def transfer_items(db,source_id,target_id,items,user):
        if source_id==target_id: raise PosError("La mesa destino debe ser diferente")
        source=DiningTableService.get(db,source_id); target=DiningTableService.get(db,target_id); requested={item.item_id:item.quantity for item in items if item.quantity>0}
        if not requested: raise PosError("Selecciona productos para traspasar")
        source_items={item.id:item for item in source.items}
        for item_id,quantity in requested.items():
            item=source_items.get(item_id)
            if not item or quantity>item.quantity: raise PosError("Cantidad de traspaso no válida")
        moved_at=datetime.now()
        for item_id,quantity in requested.items():
            item=source_items[item_id];target.items.append(DiningTableItem(product_id=item.product_id,product_name=item.product_name,unit_price=item.unit_price,quantity=quantity,added_at=moved_at))
            db.add(TableItemTransfer(source_table_id=source.id,target_table_id=target.id,product_name=item.product_name,quantity=quantity,transferred_by_id=user.id,transferred_by_name=user.display_name,transferred_at=moved_at))
            if quantity==item.quantity:db.delete(item)
            else:item.quantity-=quantity
        source.updated_at=moved_at;target.updated_at=moved_at;db.commit()
        return {"source":dining_table_dict(DiningTableService.get(db,source.id)),"target":dining_table_dict(DiningTableService.get(db,target.id))}
    @staticmethod
    def cancel(db,table_id):
        table=DiningTableService.get(db,table_id); table.status="cancelled"; table.closed_at=datetime.now(); table.updated_at=datetime.now(); db.commit()

def config_dict(c): return {"business_name":c.business_name,"address":c.address,"phone":c.phone,"ticket_message":c.ticket_message,"printer_name":c.printer_name,"encoding":c.encoding,"character_table":c.character_table}
def get_business_config(db):
    c=db.get(BusinessConfig,1)
    if not c: c=BusinessConfig(id=1); db.add(c); db.commit(); db.refresh(c)
    return c
