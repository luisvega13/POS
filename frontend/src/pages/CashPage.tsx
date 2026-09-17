import {Banknote,ChevronLeft,ChevronRight,DoorOpen,Eye,MinusCircle,Printer,RefreshCw,RotateCcw} from 'lucide-react';
import {FormEvent,useEffect,useState} from 'react';
import {api} from '../api';
import type {CashSummary,PaginatedCash,UserRole} from '../types';
import {Modal} from '../components/Modal';
const mxn=(value:string|number|undefined)=>{const amount=Number(value);return new Intl.NumberFormat('es-MX',{style:'currency',currency:'MXN'}).format(Number.isFinite(amount)?amount:0)};
const initialHistory:PaginatedCash={items:[],total:0,page:1,page_size:10};

export function CashPage({role,onStatus,onNotice}:{role:UserRole;onStatus:(value:boolean)=>void;onNotice:(message:string,error?:boolean)=>void}){
 const [summary,setSummary]=useState<CashSummary|null>(null),[history,setHistory]=useState(initialHistory),[historyPage,setHistoryPage]=useState(1),[selected,setSelected]=useState<CashSummary|null>(null);
 const [opening,setOpening]=useState(false),[amount,setAmount]=useState('0.00'),[charging,setCharging]=useState(false),[chargeAmount,setChargeAmount]=useState(''),[chargeConcept,setChargeConcept]=useState('');
 const [closing,setClosing]=useState(false),[declaredCash,setDeclaredCash]=useState(''),[declaredCard,setDeclaredCard]=useState(''),[declaredTransfer,setDeclaredTransfer]=useState(''),[reopening,setReopening]=useState<CashSummary|null>(null),[reopenReason,setReopenReason]=useState(''),[saving,setSaving]=useState(false);
 const load=async()=>{try{const [current,past]=await Promise.all([api.cash(),api.cashHistory(historyPage)]);setSummary(current.session);setHistory(past);onStatus(current.open)}catch(error){onNotice((error as Error).message,true)}};
 useEffect(()=>{void load()},[historyPage]);
 async function open(event:FormEvent){event.preventDefault();try{await api.openCash(amount);setOpening(false);onNotice('Caja abierta correctamente');void load()}catch(error){onNotice((error as Error).message,true)}}
 async function addCharge(event:FormEvent){event.preventDefault();setSaving(true);try{const result=await api.addCashCharge({amount:chargeAmount,concept:chargeConcept});setSummary(result.summary);setCharging(false);setChargeAmount('');setChargeConcept('');onNotice(result.message)}catch(error){onNotice((error as Error).message,true)}finally{setSaving(false)}}
 function prepareClose(){if(!summary)return;setDeclaredCash(summary.expected_cash);setDeclaredCard(String(Number(summary.card)+Number(summary.tip_card)));setDeclaredTransfer(String(Number(summary.transfer)+Number(summary.tip_transfer)));setClosing(true)}
 async function close(event:FormEvent){event.preventDefault();setSaving(true);try{const result=await api.closeCash({declared_cash:declaredCash,declared_card:declaredCard,declared_transfer:declaredTransfer});setClosing(false);setSummary(null);onStatus(false);onNotice(result.message,result.print_success===false);void load()}catch(error){onNotice((error as Error).message,true)}finally{setSaving(false)}}
 async function printCurrent(){try{onNotice((await api.printCash()).message)}catch(error){onNotice((error as Error).message,true)}}
 async function printPast(id:number){try{onNotice((await api.printHistoricalCash(id)).message)}catch(error){onNotice((error as Error).message,true)}}
 async function reopen(event:FormEvent){event.preventDefault();if(!reopening)return;setSaving(true);try{const result=await api.reopenCash(reopening.id,reopenReason);setReopening(null);setSelected(null);setReopenReason('');setSummary(result.session);onStatus(true);onNotice(result.message);void load()}catch(error){onNotice((error as Error).message,true)}finally{setSaving(false)}}
 return <>
  {summary?<>
<div className="section-title">
<div>
<h2>Sesión actual</h2>
<p>Abierta {new Date(summary.opened_at).toLocaleString('es-MX')}</p>
</div>
<button className="secondary" onClick={load}>
<RefreshCw size={16}/> Actualizar</button>
</div>
<section className="panel cash-actions">
<div>
<Banknote/>
<div>
<h3>Resumen de caja</h3>
<p>El efectivo esperado considera fondo inicial y ventas en efectivo, menos cargos y propinas de tarjeta o transferencia pagadas desde caja.</p>
</div>
</div>
<aside>
<button className="secondary" onClick={()=>setCharging(true)}>
<MinusCircle size={16}/> Registrar cargo</button>
<button className="secondary" onClick={printCurrent}>
<Printer size={16}/> Imprimir corte</button>
<button className="danger" onClick={prepareClose}>Cerrar caja</button>
</aside>
</section>
</>:<section className="panel empty-state">
<DoorOpen size={36}/>
<h2>No hay una caja abierta</h2>
<p>Puedes abrir una caja nueva o reabrir un corte anterior.</p>
<button className="primary" onClick={()=>setOpening(true)}>Abrir caja</button>
</section>}
  <div className="section-title">
<div>
<h2>Historial de cortes</h2>
<p>Consulta, imprime o reabre sesiones cerradas.</p>
</div>
</div>
<section className="panel data-panel">
<div className="table-wrap">
<table>
<thead>
<tr>
<th>Corte</th>
<th>Apertura</th>
<th>Cierre</th>
<th>Operaciones</th>
<th>Total ventas</th>
<th>Diferencia</th>
<th>Acciones</th>
</tr>
</thead>
<tbody>{history.items.map(item=>
<tr key={item.id}>
<td><b>#{item.id}</b></td>
<td>{new Date(item.opened_at).toLocaleString('es-MX')}</td>
<td>{item.closed_at?new Date(item.closed_at).toLocaleString('es-MX'):'—'}</td>
<td>{item.operations}</td>
<td>{mxn(item.total_sold)}</td>
<td>{mxn(item.cash_variance||0)}</td>
<td>
<div className="actions">
<button onClick={()=>setSelected(item)}>
<Eye size={14}/> Detalle</button>
<button onClick={()=>void printPast(item.id)}>
<Printer size={14}/> Imprimir</button>{role==='admin'&&<button disabled={Boolean(summary)} onClick={()=>setReopening(item)}>
<RotateCcw size={14}/> Reabrir</button>}</div>
</td>
</tr>)}{!history.items.length&&<tr>
<td colSpan={7}>Todavía no hay cortes cerrados.</td>
</tr>}</tbody>
</table>
</div>{history.total>history.page_size&&<footer className="pagination"><span>{(historyPage-1)*10+1} - {Math.min(historyPage*10,history.total)} de {history.total}</span><div><button aria-label="Página anterior" disabled={historyPage===1} onClick={()=>setHistoryPage(value=>value-1)}><ChevronLeft size={17}/></button><b>{historyPage} / {Math.ceil(history.total/history.page_size)}</b><button aria-label="Página siguiente" disabled={historyPage*10>=history.total} onClick={()=>setHistoryPage(value=>value+1)}><ChevronRight size={17}/></button></div></footer>}</section>
  {opening&&<Modal title="Abrir caja" onClose={()=>setOpening(false)}>
<form className="form" onSubmit={open}>
<label className="field">Fondo inicial<input autoFocus type="number" min="0" step="0.01" value={amount} onChange={event=>setAmount(event.target.value)}/>
</label>
<button className="primary full">Abrir caja</button>
</form>
</Modal>}
  {charging&&summary&&<Modal title="Registrar cargo" onClose={()=>setCharging(false)}>
<form className="form" onSubmit={addCharge}>
<label className="field">Importe<input autoFocus required type="number" min="0.01" step="0.01" value={chargeAmount} onChange={event=>setChargeAmount(event.target.value)} placeholder="0.00"/>
</label>
<label className="field">Concepto<input required minLength={2} value={chargeConcept} onChange={event=>setChargeConcept(event.target.value)} placeholder="Ej. Retiro para pagar refresco"/>
</label>
<button className="primary full" disabled={saving}>{saving?'Registrando…':'Registrar cargo'}</button>
</form>
</Modal>}
  {closing&&summary&&<Modal title="Declaración del cajero" onClose={()=>setClosing(false)}>
<form className="form" onSubmit={close}>
<p>Registra lo contado antes de cerrar. Al confirmar se generará el corte final.</p>
<label className="field">Efectivo<input autoFocus required type="number" min="0" step="0.01" value={declaredCash} onChange={event=>setDeclaredCash(event.target.value)}/>
<span>Esperado: <b>{mxn(summary.expected_cash)}</b>
</span>
</label>
<label className="field">Tarjeta<input required type="number" min="0" step="0.01" value={declaredCard} onChange={event=>setDeclaredCard(event.target.value)}/>
</label>
<label className="field">Transferencia<input required type="number" min="0" step="0.01" value={declaredTransfer} onChange={event=>setDeclaredTransfer(event.target.value)}/>
</label>
<div className="payment-total">
<span>Total declarado</span>
<strong>{mxn(Number(declaredCash||0)+Number(declaredCard||0)+Number(declaredTransfer||0))}</strong>
</div>
<button className="danger full" disabled={saving}>{saving?'Cerrando…':'Cerrar caja e imprimir corte'}</button>
</form>
</Modal>}
  {selected&&<Modal title={`Detalle del corte #${selected.id}`} onClose={()=>setSelected(null)}>
<div className="metrics cash-metrics">{([['Fondo inicial',selected.opening_amount],['Operaciones',selected.operations],['Total ventas',selected.total_sold],['Efectivo total',selected.total_collected],['Total propinas',selected.total_tips],['Propinas pagadas',selected.paid_tips],['Cuentas con descuento',selected.discounted_accounts],['Total descontado',selected.total_discounts],['Cargos',selected.charges],['Efectivo esperado',selected.expected_cash],['Efectivo declarado',selected.declared_cash||'0'],['Sobrante o faltante',selected.cash_variance||'0']] as [string,string|number][]).map(([label,value])=>
<article key={label}>
<small>{label}</small>
<strong>{label==='Operaciones'||label==='Cuentas con descuento'?value:mxn(value)}</strong>
</article>)}</div>{selected.reopened_count>0&&<p>Reabierto {selected.reopened_count} vez/veces. Último motivo: {selected.last_reopen_reason}</p>}<button className="secondary full" onClick={()=>void printPast(selected.id)}>
<Printer size={16}/> Imprimir este corte</button>
</Modal>}
  {reopening&&<Modal title={`Reabrir corte #${reopening.id}`} onClose={()=>setReopening(null)}>
<form className="form" onSubmit={reopen}>
<p>La caja volverá a quedar activa y su declaración anterior se eliminará. La operación quedará en auditoría.</p>
<label className="field">Motivo de reapertura<textarea autoFocus required minLength={3} value={reopenReason} onChange={event=>setReopenReason(event.target.value)} placeholder="Ej. Corregir una operación omitida"/>
</label>
<button className="danger full" disabled={saving||reopenReason.trim().length<3}>{saving?'Reabriendo…':'Confirmar reapertura'}</button>
</form>
</Modal>}
 </>;
}
