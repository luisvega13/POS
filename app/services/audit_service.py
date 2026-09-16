import json
from datetime import date,datetime,time,timedelta
from sqlalchemy import func,select
from app.models import AuditEvent

def record_audit(db,user,action,entity_type,entity_id="",details=None):
    event=AuditEvent(user_id=getattr(user,"id",None),user_name=getattr(user,"display_name","Sistema"),user_role=getattr(user,"role","system"),action=action,entity_type=entity_type,entity_id=str(entity_id or ""),details=json.dumps(details or {},ensure_ascii=False,default=str))
    db.add(event);db.commit();db.refresh(event);return event

def audit_dict(event):
    try:details=json.loads(event.details or "{}")
    except json.JSONDecodeError:details={"value":event.details}
    return {"id":event.id,"user_id":event.user_id,"user_name":event.user_name,"user_role":event.user_role,"action":event.action,"entity_type":event.entity_type,"entity_id":event.entity_id,"details":details,"created_at":event.created_at.isoformat()}

def list_audits(db,page=1,page_size=20,day:date|None=None,action=""):
    filters=[]
    if day:
        start=datetime.combine(day,time.min);filters.extend((AuditEvent.created_at>=start,AuditEvent.created_at<start+timedelta(days=1)))
    if action:filters.append(AuditEvent.action==action)
    total=int(db.scalar(select(func.count(AuditEvent.id)).where(*filters)) or 0)
    rows=db.scalars(select(AuditEvent).where(*filters).order_by(AuditEvent.id.desc()).offset((page-1)*page_size).limit(page_size))
    return {"items":[audit_dict(row) for row in rows],"total":total,"page":page,"page_size":page_size}
