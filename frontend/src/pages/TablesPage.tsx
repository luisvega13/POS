import {ArrowLeft,ArrowRightLeft,Ban,Clock3,Eye,Layers3,Minus,Plus,Printer,Search,Trash2,UtensilsCrossed,UsersRound} from 'lucide-react';
import {useEffect,useState} from 'react';
import {api} from '../api';
import {Modal} from '../components/Modal';
import {ValueModeToggle,type ValueMode} from '../components/ValueModeToggle';
import type {CartLine,DiningTable,DiningTableItem,PaymentMethod,Permissions,Product,TableCancellation,User,UserRole} from '../types';
const mxn=(value:number|string)=>new Intl.NumberFormat('es-MX',{style:'currency',currency:'MXN'}).format(Number(value));
const dateTime=(value:string)=>new Date(value).toLocaleString('es-MX',{day:'2-digit',month:'2-digit',year:'numeric',hour:'2-digit',minute:'2-digit'});
const tableName=(name:string)=>/^mesa\b/i.test(name)?name:`Mesa ${name}`;
type DetailLine={key:string;item_id:number|null;product_name:string;quantity:number;subtotal:number;added_at:string|null};
const calculated=(base:number,value:string,mode:ValueMode)=>Math.round((mode==='percent'?base*Number(value||0)/100:Number(value||0))*100)/100;
const cents=(value:number|string)=>Math.round((Number(value)||0)*100);
function detailLines(items:DiningTableItem[],grouped:boolean):DetailLine[]{if(!grouped)return items.map(item=>({key:String(item.id),item_id:item.id,product_name:item.product_name,quantity:item.quantity,subtotal:Number(item.subtotal),added_at:item.added_at}));const combined=new Map<string,DetailLine>();for(const item of items){const key=`${item.product_id}:${item.unit_price}`,current=combined.get(key);current?(current.quantity+=item.quantity,current.subtotal+=Number(item.subtotal)):combined.set(key,{key,item_id:null,product_name:item.product_name,quantity:item.quantity,subtotal:Number(item.subtotal),added_at:null})}return [...combined.values()]}
export function TablesPage({products,cashOpen,role,permissions,onReload,onNotice}:{products:Product[];cashOpen:boolean;role:UserRole;permissions:Permissions;onReload:()=>void;onNotice:(message:string,error?:boolean)=>void}){
 const [tables,setTables]=useState<DiningTable[]>([]),[selected,setSelected]=useState<DiningTable|null>(null),[lockedTable,setLockedTable]=useState<DiningTable|null>(null),[pendingOperation,setPendingOperation]=useState<'cancel'|'product_transfer'|'table_transfer'|null>(null),[authPassword,setAuthPassword]=useState(''),[authorizedPassword,setAuthorizedPassword]=useState(''),[draft,setDraft]=useState<Map<number,CartLine>>(new Map()),[creating,setCreating]=useState(false),[details,setDetails]=useState(false),[cancellations,setCancellations]=useState<TableCancellation[]>([]),[grouped,setGrouped]=useState(false),[transferring,setTransferring]=useState(false),[targetId,setTargetId]=useState(''),[transferQty,setTransferQty]=useState<Record<number,number>>({}),[cancelItem,setCancelItem]=useState<DiningTableItem|null>(null),[cancelQty,setCancelQty]=useState(1),[cancelReason,setCancelReason]=useState(''),[name,setName]=useState(''),[query,setQuery]=useState(''),[category,setCategory]=useState(''),[paying,setPaying]=useState(false),[method,setMethod]=useState<PaymentMethod>('cash'),[split,setSplit]=useState(false),[splitCash,setSplitCash]=useState(''),[splitCard,setSplitCard]=useState(''),[splitTransfer,setSplitTransfer]=useState(''),[received,setReceived]=useState(''),[tip,setTip]=useState(''),[tipMode,setTipMode]=useState<ValueMode>('amount'),[tipMethod,setTipMethod]=useState<PaymentMethod>('cash'),[discount,setDiscount]=useState(''),[discountMode,setDiscountMode]=useState<ValueMode>('amount'),[discountReason,setDiscountReason]=useState(''),[saving,setSaving]=useState(false),[guestCount,setGuestCount]=useState(1),[waiters,setWaiters]=useState<User[]>([]),[assigning,setAssigning]=useState(false),[waiterId,setWaiterId]=useState(''),[openingWaiterId,setOpeningWaiterId]=useState('');
 const load=async()=>{try{const data=await api.tables();setTables(data);if(selected)setSelected(data.find(table=>table.id===selected.id)??null)}catch(error){onNotice((error as Error).message,true)}};useEffect(()=>{void load();void api.waiters().then(setWaiters).catch(error=>onNotice((error as Error).message,true))},[]);
 const categories=[...new Set(products.map(product=>product.category))],filtered=products.filter(product=>(!category||product.category===category)&&product.name.toLowerCase().includes(query.toLowerCase())),draftLines=[...draft.values()],draftTotal=draftLines.reduce((sum,line)=>sum+Number(line.product.price)*line.quantity,0),tableTotal=Number(selected?.total||0),discountValue=calculated(tableTotal,discount,discountMode),discountedTotal=Math.max(0,tableTotal-discountValue),serviceCharge=permissions.include_tip_in_ticket?Math.round(discountedTotal*permissions.service_charge_percent)/100:0,tipValue=permissions.include_tip_in_ticket?serviceCharge:calculated(discountedTotal,tip,tipMode),splitCents=cents(splitCash)+cents(splitCard)+cents(splitTransfer),totalCents=cents(discountedTotal),splitSum=splitCents/100,splitBalance=(totalCents-splitCents)/100,cashPayment=split?cents(splitCash)/100:(method==='cash'?discountedTotal:0),cashDue=cashPayment+(tipValue>0&&tipMethod==='cash'?tipValue:0),discountBlocked=role==='cashier'&&permissions.cashier_discount_mode==='denied';
 const canPrint=role!=='waiter'||permissions.waiter_print_account,productTransferMode=role==='admin'?'allowed':permissions[`${role}_product_transfer_mode` as 'waiter_product_transfer_mode'|'cashier_product_transfer_mode'],tableTransferMode=role==='admin'?'allowed':permissions[`${role}_table_transfer_mode` as 'waiter_table_transfer_mode'|'cashier_table_transfer_mode'],cancelMode=role==='admin'?'allowed':permissions[`${role}_cancel_mode` as 'waiter_cancel_mode'|'cashier_cancel_mode'];
 async function create(){if(!name.trim()||(role!=='waiter'&&!openingWaiterId))return;setSaving(true);try{const table=await api.createTable(name,permissions.waiter_require_guest_count?guestCount:0,role==='waiter'?undefined:Number(openingWaiterId));setTables(old=>[...old,table]);setSelected(table);setName('');setGuestCount(1);setOpeningWaiterId('');setCreating(false);onNotice(`${table.name} abierta para ${table.assigned_waiter_name}`)}catch(error){onNotice((error as Error).message,true)}finally{setSaving(false)}}
 function setQty(product:Product,delta:number){setDraft(current=>{const next=new Map(current),quantity=(next.get(product.id)?.quantity??0)+delta;quantity>0?next.set(product.id,{product,quantity}):next.delete(product.id);return next})}
 async function addToTable(){if(!selected||!draftLines.length)return;setSaving(true);try{const saved=await api.addTableItems(selected.id,draftLines.map(line=>({product_id:line.product.id,quantity:line.quantity})));setSelected(saved);setTables(old=>old.map(table=>table.id===saved.id?saved:table));setDraft(new Map());onNotice('Productos agregados a la mesa')}catch(error){onNotice((error as Error).message,true)}finally{setSaving(false)}}
 async function printAccount(){if(!selected)return;setSaving(true);try{onNotice((await api.printTableAccount(selected.id)).message);setSelected(null);setDraft(new Map());await load()}catch(error){onNotice((error as Error).message,true)}finally{setSaving(false)}}
 async function openDetails(){if(!selected)return;setGrouped(false);setCancellations(await api.tableCancellations(selected.id));setDetails(true)}
 function operationPassword(operation:'cancel'|'product_transfer'|'table_transfer'){if(authorizedPassword)return authorizedPassword;if(role==='admin')return '';const mode=permissions[`${role}_${operation}_mode` as keyof Permissions];if(mode==='password')return null;return ''}
 function openAuthorizedOperation(operation:'cancel'|'product_transfer'|'table_transfer',password=''){setAuthorizedPassword(password);if(operation==='cancel'){setCancelItem(selected?.items[0]??null);setCancelQty(1);setCancelReason('')}else if(operation==='product_transfer')setTransferring(true);else{setWaiterId(String(selected?.assigned_waiter_id??''));setAssigning(true)}}
 function requestOperation(operation:'cancel'|'product_transfer'|'table_transfer'){const mode=role==='admin'?'allowed':permissions[`${role}_${operation}_mode` as keyof Permissions];if(mode==='password'){setAuthPassword('');setPendingOperation(operation)}else openAuthorizedOperation(operation)}
 async function confirmOperationPassword(){if(!pendingOperation)return;setSaving(true);try{await api.authorizeOperation(pendingOperation,authPassword);const operation=pendingOperation;setPendingOperation(null);openAuthorizedOperation(operation,authPassword)}catch(error){onNotice((error as Error).message,true)}finally{setSaving(false)}}
 async function cancelProduct(){if(!selected||!cancelItem)return;const operation_password=operationPassword('cancel');if(operation_password===null)return;setSaving(true);try{const saved=await api.cancelTableItem(selected.id,cancelItem.id,{quantity:cancelQty,reason:cancelReason,operation_password});setSelected(saved);setTables(old=>old.map(table=>table.id===saved.id?saved:table));setCancellations(await api.tableCancellations(selected.id));setCancelItem(null);setCancelReason('');onNotice('Producto cancelado y registrado')}catch(error){onNotice((error as Error).message,true)}finally{setSaving(false)}}
 async function transfer(){if(!selected||!targetId)return;const operation_password=operationPassword('product_transfer');if(operation_password===null)return;const items=Object.entries(transferQty).filter(([,quantity])=>quantity>0).map(([item_id,quantity])=>({item_id:Number(item_id),quantity}));setSaving(true);try{const result=await api.transferTableItems(selected.id,{target_table_id:Number(targetId),items,operation_password});setSelected(result.source);setTransferring(false);setTransferQty({});setTargetId('');await load();onNotice('Productos traspasados correctamente')}catch(error){onNotice((error as Error).message,true)}finally{setSaving(false)}}
 async function assignWaiter(){if(!selected||!waiterId)return;const operation_password=operationPassword('table_transfer');if(operation_password===null)return;setSaving(true);try{const saved=await api.assignTableWaiter(selected.id,Number(waiterId),operation_password);setAssigning(false);setWaiterId('');if(role==='waiter'){setSelected(null);await load()}else{setSelected(saved);setTables(old=>old.map(table=>table.id===saved.id?saved:table))}onNotice(`Mesa asignada a ${saved.assigned_waiter_name}`)}catch(error){onNotice((error as Error).message,true)}finally{setSaving(false)}}
 async function cancelTable(){if(!selected||!window.confirm(`¿Cerrar ${selected.name} sin cobrar?`))return;try{const result=await api.cancelTable(selected.id);setSelected(null);setDraft(new Map());await load();onNotice(result.message)}catch(error){onNotice((error as Error).message,true)}}
 async function checkout(){if(!selected)return;if(draftLines.length)return onNotice('Primero agrega los productos pendientes a la mesa',true);if(split&&splitCents!==totalCents)return onNotice('La suma de los pagos debe coincidir con el total de la cuenta',true);if(discountMode==='percent'&&Number(discount)>100)return onNotice('El porcentaje de descuento no puede superar 100%',true);if(discountValue>tableTotal)return onNotice('El descuento no puede superar el consumo',true);if(discountValue>0&&!discountReason.trim())return onNotice('Indica el motivo del descuento',true);let discount_password:string|undefined;if(discountValue>0&&role==='cashier'&&permissions.cashier_discount_mode==='password'){discount_password=window.prompt('Ingresa la contraseña operativa para autorizar el descuento')||undefined;if(!discount_password)return}if(cashDue>0&&cents(received)<cents(cashDue))return onNotice('El efectivo recibido es menor al total en efectivo',true);const payments=split?([['cash',splitCash],['card',splitCard],['transfer',splitTransfer]] as [PaymentMethod,string][]).filter(([,value])=>cents(value)>0).map(([paymentMethod,value])=>({method:paymentMethod,amount:cents(value)/100})):[];setSaving(true);try{const result=await api.checkoutTable(selected.id,{payment_method:method,payments,amount_received:cashDue>0?received:null,tip_amount:tipValue,tip_method:tipMethod,discount_amount:discountValue,discount_reason:discountReason,discount_password,print_ticket:permissions.print_on_checkout});setPaying(false);setSelected(null);setReceived('');setTip('');setDiscount('');setDiscountReason('');setSplit(false);setSplitCash('');setSplitCard('');setSplitTransfer('');await load();onReload();onNotice(result.message,result.print_success===false)}catch(error){onNotice((error as Error).message,true)}finally{setSaving(false)}}
 function leaveTable(){if(draftLines.length&&!window.confirm('Hay productos sin agregar. ¿Salir y descartarlos?'))return;setDraft(new Map());setSelected(null)}
 if(selected)return <div className="table-service">
<div className="table-service-head">
<div className="table-context">
<button className="table-back" onClick={leaveTable}>
<ArrowLeft size={17}/> Mesas</button>
<span className="table-context-divider"/>
<div className="table-identity">
<h2>{tableName(selected.name)}</h2>
<span>
<i/> Abierta{selected.guest_count>0?` · ${selected.guest_count} personas`:``}{selected.assigned_waiter_name?` · ${selected.assigned_waiter_name}`:``}</span>
</div>
</div>
<div className="table-head-actions">{waiters.length>0&&tableTransferMode!=='denied'&&<button className="table-detail-button" onClick={()=>requestOperation('table_transfer')}>
<UsersRound size={15}/> {selected.assigned_waiter_id?'Traspasar mesa':'Asignar mesero'}</button>}{canPrint&&<button className="table-detail-button" disabled={!selected.items.length||saving} onClick={()=>void printAccount()}>
<Printer size={15}/> Cuenta</button>}{cancelMode!=='denied'&&<button className="table-detail-button" disabled={!selected.items.length} onClick={()=>requestOperation('cancel')}><Ban size={15}/> Cancelar producto</button>}{productTransferMode!=='denied'&&<button className="table-detail-button" disabled={!selected.items.length||tables.length<2} onClick={()=>requestOperation('product_transfer')}>
<ArrowRightLeft size={15}/> Traspasar productos</button>}<button className="table-detail-button" onClick={()=>void openDetails()}>
<Eye size={15}/> Detalle</button>{role!=='waiter'&&<button className="table-close-button" onClick={()=>void cancelTable()}>Cerrar</button>}</div>
</div>
<div className="pos-grid">
<section className="catalog panel">
<div className="search">
<Search size={18}/>
<input value={query} onChange={event=>setQuery(event.target.value)} placeholder="Buscar producto…"/>
</div>
<div className="chips">
<button className={!category?'active':''} onClick={()=>setCategory('')}>Todos</button>{categories.map(item=>
<button key={item} className={category===item?'active':''} onClick={()=>setCategory(item)}>{item}</button>)}</div>
<div className="product-grid">{filtered.map(product=>
<button className="product-card" key={product.id} onClick={()=>setQty(product,1)}>
<small>{product.category}</small>
<b>{product.name}</b>
<strong>{mxn(product.price)}</strong>
</button>)}</div>
</section>
<aside className="cart panel">
<header>
<div>
<small>POR AÑADIR</small>
<h2>Consumo actual</h2>
</div>
<button className="text-button" onClick={()=>setDraft(new Map())}>Limpiar</button>
</header>
<div className="cart-lines">{draftLines.map(line=>
<article key={line.product.id}>
<div>
<b>{line.product.name}</b>
<small>{mxn(line.product.price)} c/u</small>
</div>
<strong>{mxn(Number(line.product.price)*line.quantity)}</strong>
<footer>
<button onClick={()=>setQty(line.product,-1)}>
<Minus size={15}/>
</button>
<span>{line.quantity}</span>
<button onClick={()=>setQty(line.product,1)}>
<Plus size={15}/>
</button>
<button className="remove" onClick={()=>setQty(line.product,-line.quantity)}>
<Trash2 size={15}/> Quitar</button>
</footer>
</article>)}{!draftLines.length&&<div className="empty">
<UtensilsCrossed/>
<p>Selecciona los productos que deseas añadir</p>
</div>}</div>
<div className="cart-total">
<p>
<span>Productos por añadir</span>
<b>{mxn(draftTotal)}</b>
</p>
<button className="primary full" disabled={!draftLines.length||saving} onClick={()=>void addToTable()}>{saving?'Agregando…':'Añadir a la mesa'}</button>
<p className="saved-total">
<span>Total guardado en mesa</span>
<b>{mxn(selected.total)}</b>
</p>{role!=='waiter'&&<button className="secondary full" disabled={!selected.items.length||saving} onClick={()=>cashOpen?setPaying(true):onNotice('Debes abrir caja antes de cobrar',true)}>Cobrar mesa</button>}</div>
</aside>
</div>
 {details&&<Modal title={`Detalle de ${selected.name}`} onClose={()=>setDetails(false)}>
<div className="table-detail-summary">
<span>Total acumulado</span>
<strong>{mxn(selected.total)}</strong>
</div>
<div className="table-detail-section-head">
<div>
<small>PRODUCTOS AGREGADOS</small>
<span>{grouped?'Vista resumida':'Ordenados por incorporación'}</span>
</div>
</div>
<div className="table-detail-actions">
<button className="detail-group-button" onClick={()=>setGrouped(value=>!value)}>
<Layers3 size={14}/>{grouped?'Ver historial':'Agrupar'}</button>
</div>
<div className="table-detail-list">{detailLines(selected.items,grouped).map(item=>
<div className="table-detail-row" key={item.key}>
<span className="detail-quantity">{item.quantity}</span>
<article>
<div>
<b>{item.product_name}</b>{item.added_at&&<small>{dateTime(item.added_at)}</small>}</div>
<strong>{mxn(item.subtotal)}</strong></article>
</div>)}{!selected.items.length&&<div className="empty">Aún no se han agregado productos.</div>}</div>{cancellations.length>0&&<div className="cancellation-history">
<small>CANCELACIONES</small>{cancellations.map(item=>
<article key={item.id}>
<div>
<b>{item.quantity} {item.product_name}</b>
<span>{item.reason}</span>
</div>
<div>
<strong>-{mxn(item.amount)}</strong>
<small>{item.cancelled_by} · {dateTime(item.cancelled_at)}</small>
</div>
</article>)}</div>}</Modal>}
 {cancelItem&&<Modal title="Cancelar producto" onClose={()=>setCancelItem(null)}>
<label className="field">Producto<select value={cancelItem.id} onChange={event=>{const item=selected.items.find(row=>row.id===Number(event.target.value));if(item){setCancelItem(item);setCancelQty(1)}}}>{selected.items.map(item=><option key={item.id} value={item.id}>{item.product_name} · {item.quantity}</option>)}</select></label>
<div className="operation-product">
<b>{cancelItem.product_name}</b>
<span>{cancelItem.quantity} disponibles</span>
</div>
<label className="field">Cantidad<input type="number" min="1" max={cancelItem.quantity} value={cancelQty} onChange={event=>setCancelQty(Number(event.target.value))}/>
</label>
<label className="field">Motivo<select required value={cancelReason} onChange={event=>setCancelReason(event.target.value)}>
<option value="">Seleccionar motivo…</option>
<option value="Cambio de opinión del cliente">Cambio de opinión del cliente</option>
<option value="Error en la captura">Error en la captura</option>
<option value="Producto agotado">Producto agotado</option>
<option value="Retraso en la preparación">Retraso en la preparación</option>
</select>
</label>
<button className="danger full" disabled={!cancelReason||saving} onClick={()=>void cancelProduct()}>Confirmar cancelación</button>
</Modal>}
 {transferring&&<Modal title="Traspasar productos" onClose={()=>setTransferring(false)}>
<label className="field">Mesa destino<select value={targetId} onChange={event=>setTargetId(event.target.value)}>
<option value="">Seleccionar mesa…</option>{tables.filter(table=>table.id!==selected.id).map(table=>
<option key={table.id} value={table.id}>{tableName(table.name)}</option>)}</select>
</label>
<div className="transfer-list">{selected.items.map(item=>
<label key={item.id}>
<span>
<b>{item.product_name}</b>
<small>Disponible: {item.quantity}</small>
</span>
<input type="number" min="0" max={item.quantity} value={transferQty[item.id]??0} onChange={event=>setTransferQty(current=>({...current,[item.id]:Number(event.target.value)}))}/>
</label>)}</div>
<button className="primary full" disabled={!targetId||!Object.values(transferQty).some(value=>value>0)||saving} onClick={()=>void transfer()}>Confirmar traspaso</button>
</Modal>}
 {assigning&&<Modal title="Asignar mesa a mesero" onClose={()=>setAssigning(false)}>
<div className="transfer-waiter-form" style={{display:'grid',gap:20}}>
<label className="field">Mesero responsable<select value={waiterId} onChange={event=>setWaiterId(event.target.value)}>
<option value="">Seleccionar mesero…</option>{waiters.map(waiter=>
<option key={waiter.id} value={waiter.id}>{waiter.display_name}</option>)}</select>
</label>
<button className="primary full" disabled={!waiterId||saving} onClick={()=>void assignWaiter()}>{saving?'Guardando…':'Confirmar traspaso de mesa'}</button>
</div>
</Modal>}{paying&&<Modal title={`Cobrar ${selected.name}`} onClose={()=>setPaying(false)}>
<div className="payment-total">
<span>Total a cobrar</span>
<strong>{mxn(discountedTotal+tipValue)}</strong>
</div>
{!split&&<div className="payment-tabs">{([['cash','Efectivo'],['card','Tarjeta'],['transfer','Transferencia']] as [PaymentMethod,string][]).map(([id,label])=>
<button key={id} className={method===id?'active':''} onClick={()=>setMethod(id)}>{label}</button>)}</div>
}<div className="split-payment-toggle"><button type="button" onClick={()=>setSplit(value=>!value)}>{split?'Usar un solo método':'Dividir pago'}</button></div>{split&&<><div className="split-payment-grid"><label className="field">Efectivo<input type="number" min="0" step="0.01" value={splitCash} onChange={event=>setSplitCash(event.target.value)}/></label><label className="field">Tarjeta<input type="number" min="0" step="0.01" value={splitCard} onChange={event=>setSplitCard(event.target.value)}/></label><label className="field">Transferencia<input type="number" min="0" step="0.01" value={splitTransfer} onChange={event=>setSplitTransfer(event.target.value)}/></label></div><p className="split-balance">Asignado: <b>{mxn(splitSum)}</b> · Restante: <b>{mxn(splitBalance)}</b></p></>}
<div className="payment-adjustments">
<label className={`field adjustment-field ${discountBlocked?'is-disabled':''}`}>
<span className="field-heading">
<span>Descuento</span>
<ValueModeToggle mode={discountMode} onChange={setDiscountMode} label="Descuento" disabled={discountBlocked}/>
</span>
<span className="amount-control">
<i>{discountMode==='amount'?'$':'%'}</i>
<input disabled={discountBlocked} type="number" min="0" max={discountMode==='percent'?100:tableTotal} step="0.01" value={discount} onChange={event=>setDiscount(event.target.value)} placeholder="0.00"/>
</span>
<small>Aplicado: {mxn(discountValue)}</small>
</label>
<label className="field adjustment-field">
<span className="field-heading">
<span>Propina</span>{!permissions.include_tip_in_ticket&&<ValueModeToggle mode={tipMode} onChange={setTipMode} label="Propina"/>}</span>{permissions.include_tip_in_ticket?<div className="service-charge-summary compact">
<span>Servicio {permissions.service_charge_percent}%</span>
<b>{mxn(serviceCharge)}</b>
</div>:<>
<span className="amount-control">
<i>{tipMode==='amount'?'$':'%'}</i>
<input inputMode="decimal" type="number" min="0" step="0.01" value={tip} onChange={event=>setTip(event.target.value)} placeholder="0.00"/>
</span>
<small>Calculada: {mxn(tipValue)}</small>
</>}</label>
<label className="field">Motivo del descuento<input disabled={discountBlocked} value={discountReason} onChange={event=>setDiscountReason(event.target.value)} placeholder={discountBlocked?'Sin permiso para aplicar descuentos':'Ej. Promoción o cortesía'}/>
</label>
<label className="field">Método de propina<select value={tipMethod} onChange={event=>setTipMethod(event.target.value as PaymentMethod)}>
<option value="cash">Efectivo</option>
<option value="card">Tarjeta</option>
<option value="transfer">Transferencia</option>
</select>
</label>
</div>{cashDue>0&&<label className="field received-field">Cantidad recibida<input inputMode="decimal" value={received} onChange={event=>setReceived(event.target.value)} placeholder="0.00"/>
<span>Cambio: <b>{mxn(Math.max(0,Number(received||0)-cashDue))}</b>
</span>
</label>}<button className="primary full" disabled={saving} onClick={()=>void checkout()}>{saving?'Registrando…':permissions.print_on_checkout?'Confirmar cobro e imprimir':'Confirmar cobro'}</button>
</Modal>}{pendingOperation&&<Modal title="Autorizar operación" onClose={()=>setPendingOperation(null)}><p className="muted-copy">Ingresa la contraseña operativa antes de continuar.</p><label className="field">Contraseña<input autoFocus type="password" value={authPassword} onChange={event=>setAuthPassword(event.target.value)} onKeyDown={event=>event.key==='Enter'&&void confirmOperationPassword()}/></label><button className="primary full" disabled={!authPassword||saving} onClick={()=>void confirmOperationPassword()}>{saving?'Validando…':'Confirmar contraseña'}</button></Modal>}</div>;
 return <>
<div className="section-title">
<div>
<h2>Mesas abiertas</h2>
<p>Conserva varios consumos y cobra cuando el cliente lo solicite.</p>
</div>
<button className="primary" onClick={()=>setCreating(true)}>
<Plus size={17}/> Abrir mesa</button>
</div>
<section className="tables-grid">{tables.map(table=>
<button className={`table-card panel ${table.account_printed_at?'is-locked':''}`} key={table.id} onClick={()=>{if(table.account_printed_at)setLockedTable(table);else{setSelected(table);setDraft(new Map())}}}>
<span className="table-icon">
<UtensilsCrossed size={20}/>
</span>
<div>
<small>{table.account_printed_at?'CUENTA IMPRESA':'EN SERVICIO'}</small>
<h3>{table.name}</h3>
<p>
<Clock3 size={14}/>{new Date(table.opened_at).toLocaleTimeString('es-MX',{hour:'2-digit',minute:'2-digit'})} · {table.items.reduce((sum,item)=>sum+item.quantity,0)} productos{table.guest_count>0?` · ${table.guest_count} personas`:``}{table.assigned_waiter_name?` · ${table.assigned_waiter_name}`:``}</p>
</div>
<strong>{mxn(table.total)}</strong>
</button>)}{!tables.length&&<div className="empty-state panel">
<UtensilsCrossed size={38}/>
<h3>No hay mesas abiertas</h3>
<p className="muted-copy">Abre una mesa para comenzar a registrar su consumo.</p>
</div>}</section>{lockedTable&&<Modal title={`${tableName(lockedTable.name)} · Cuenta impresa`} onClose={()=>setLockedTable(null)}><p className="muted-copy">La mesa está bloqueada para evitar cambios después de presentar la cuenta.</p><div className="locked-table-actions">{(role==='admin'||permissions[`${role}_reprint_account` as 'waiter_reprint_account'|'cashier_reprint_account'])&&<button className="secondary full" onClick={async()=>{try{onNotice((await api.printTableAccount(lockedTable.id)).message)}catch(error){onNotice((error as Error).message,true)}}}><Printer size={16}/> Reimprimir cuenta</button>}{(role==='admin'||permissions[`${role}_reopen_printed_table` as 'waiter_reopen_printed_table'|'cashier_reopen_printed_table'])&&<button className="primary full" onClick={async()=>{try{await api.reopenTableAccount(lockedTable.id);setLockedTable(null);await load();onNotice('Mesa reabierta correctamente')}catch(error){onNotice((error as Error).message,true)}}}>Reabrir mesa</button>}</div></Modal>}{creating&&<Modal title="Abrir una mesa" onClose={()=>setCreating(false)}>
<label className="field">Nombre o número de mesa<input autoFocus value={name} onChange={event=>setName(event.target.value)} onKeyDown={event=>event.key==='Enter'&&void create()} placeholder="Ej. Mesa 4, Terraza 2…"/>
</label>{role!=='waiter'&&<label className="field">Mesero responsable<select value={openingWaiterId} onChange={event=>setOpeningWaiterId(event.target.value)}>
<option value="">Seleccionar mesero…</option>{waiters.map(waiter=>
<option key={waiter.id} value={waiter.id}>{waiter.display_name}</option>)}</select>
</label>}{permissions.waiter_require_guest_count&&<label className="field">Número de personas<input type="number" min="1" max="100" value={guestCount} onChange={event=>setGuestCount(Number(event.target.value))}/>
</label>}<button className="primary full" disabled={!name.trim()||saving||(role!=='waiter'&&!openingWaiterId)||(permissions.waiter_require_guest_count&&guestCount<1)} onClick={()=>void create()}>{saving?'Abriendo…':'Abrir mesa'}</button>
</Modal>}</>;
}


