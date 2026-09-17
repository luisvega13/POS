import {ChevronLeft,ChevronRight,Eye,Printer,RefreshCw,Search} from 'lucide-react';
import {useEffect,useMemo,useState} from 'react';
import {api} from '../api';
import type {Category,ProductReport,Sale} from '../types';
import {Modal} from '../components/Modal';

const PAGE_SIZE=10;
const mxn=(value:string)=>new Intl.NumberFormat('es-MX',{style:'currency',currency:'MXN'}).format(Number(value));
const payment={cash:'Efectivo',card:'Tarjeta',transfer:'Transferencia',mixed:'Pago dividido'};

function Pagination({page,total,onPage}:{page:number;total:number;onPage:(page:number)=>void}){
 const pages=Math.max(1,Math.ceil(total/PAGE_SIZE)),start=total?(page-1)*PAGE_SIZE+1:0,end=Math.min(page*PAGE_SIZE,total);
 return <div className="pagination">
<span>{start} - {end} de {total}</span>
<div>
<button aria-label="Página anterior" disabled={page<=1} onClick={()=>onPage(page-1)}>
<ChevronLeft size={17}/>
</button>
<b>{page} / {pages}</b>
<button aria-label="Página siguiente" disabled={page>=pages} onClick={()=>onPage(page+1)}>
<ChevronRight size={17}/>
</button>
</div>
</div>;
}

export function SalesPage({onNotice}:{onNotice:(message:string,error?:boolean)=>void}){
 const [sales,setSales]=useState<Sale[]>([]),[salesTotal,setSalesTotal]=useState(0),[salesPage,setSalesPage]=useState(1),[saleDay,setSaleDay]=useState(''),[detail,setDetail]=useState<Sale|null>(null),[report,setReport]=useState<ProductReport|null>(null),[reportPage,setReportPage]=useState(1),[from,setFrom]=useState(''),[to,setTo]=useState(''),[category,setCategory]=useState(''),[productId,setProductId]=useState(''),[productQuery,setProductQuery]=useState(''),[categories,setCategories]=useState<Category[]>([]),[query,setQuery]=useState('');
 async function loadSales(page=salesPage,day=saleDay){try{const result=await api.sales(page,day);setSales(result.items);setSalesTotal(result.total);setSalesPage(result.page)}catch(error){onNotice((error as Error).message,true)}}
 async function loadReport(){try{setReport(await api.report(from,to,category));setReportPage(1)}catch(error){onNotice((error as Error).message,true)}}
 useEffect(()=>{void loadSales(1,'');void loadReport();void api.categories().then(setCategories).catch(error=>onNotice((error as Error).message,true))},[]);
 const visible=sales.filter(sale=>sale.folio.includes(query));
 const filteredReportProducts=useMemo(()=>report?.products.filter(product=>(!productId||String(product.product_id)===productId)&&product.product_name.toLowerCase().includes(productQuery.toLowerCase()))??[],[report,productId,productQuery]);
 const reportProducts=useMemo(()=>filteredReportProducts.slice((reportPage-1)*PAGE_SIZE,reportPage*PAGE_SIZE),[filteredReportProducts,reportPage]);
 async function open(id:number){try{setDetail(await api.sale(id))}catch(error){onNotice((error as Error).message,true)}}
 async function print(id:number){try{onNotice((await api.reprint(id)).message)}catch(error){onNotice((error as Error).message,true)}}
 function applySaleDay(){setSalesPage(1);void loadSales(1,saleDay)}
 return <>
  <div className="section-title">
<div>
<h2>Historial de ventas</h2>
<p>Consulta operaciones y reimprime sin duplicar ventas.</p>
</div>
<button className="secondary" onClick={()=>{void loadSales();void loadReport()}}>
<RefreshCw size={16}/> Actualizar</button>
</div>
  <section className="panel data-panel">
   <div className="filters sales-filters">
<div className="search">
<Search size={17}/>
<input value={query} onChange={event=>setQuery(event.target.value)} placeholder="Buscar folio en esta página…"/>
</div>
<label className="compact-filter">Día<input type="date" value={saleDay} onChange={event=>setSaleDay(event.target.value)}/>
</label>
<button className="secondary" onClick={applySaleDay}>Filtrar</button>{saleDay&&<button className="text-button" onClick={()=>{setSaleDay('');setSalesPage(1);void loadSales(1,'')}}>Limpiar fecha</button>}</div>
   <div className="table-wrap">
<table>
<thead>
<tr>
<th>Folio</th>
<th>Fecha</th>
<th>Hora</th>
<th>Método</th>
<th>Total</th>
<th/>
</tr>
</thead>
<tbody>{visible.map(sale=>{const date=new Date(sale.created_at);return <tr key={sale.id}>
<td>
<b>{sale.folio}</b>
</td>
<td>{date.toLocaleDateString('es-MX')}</td>
<td>{date.toLocaleTimeString('es-MX',{hour:'2-digit',minute:'2-digit'})}</td>
<td>{payment[sale.payment_method]}</td>
<td>
<b>{mxn(sale.grand_total)}</b>
</td>
<td className="actions">
<button onClick={()=>void open(sale.id)}>
<Eye size={15}/> Ver</button>
</td>
</tr>})}</tbody>
</table>{!visible.length&&<div className="empty">No hay ventas para este filtro.</div>}</div>
   <Pagination page={salesPage} total={salesTotal} onPage={page=>void loadSales(page,saleDay)}/>
  </section>
  <div className="section-title report-title">
<div>
<h2>Productos vendidos</h2>
<p>Unidades, operaciones e ingresos por producto.</p>
</div>
</div>
  <div className="report-filters panel">
<label>Desde<input type="date" value={from} onChange={event=>setFrom(event.target.value)}/>
</label>
<label>Hasta<input type="date" value={to} onChange={event=>setTo(event.target.value)}/>
</label>
<label>Categoría<select value={category} onChange={event=>{setCategory(event.target.value);setProductId('')}}>
<option value="">Todas</option>{categories.map(item=>
<option key={item.id} value={item.name}>{item.name}</option>)}</select>
</label><label>Producto<select value={productId} onChange={event=>{setProductId(event.target.value);setReportPage(1)}}><option value="">Todos los productos</option>{report?.products.map(product=><option key={product.product_id??product.product_name} value={product.product_id??''}>{product.product_name}</option>)}</select></label><div className="search report-product-search"><Search size={17}/><input value={productQuery} onChange={event=>{setProductQuery(event.target.value);setReportPage(1)}} placeholder="Buscar producto…"/></div>
<button className="secondary" onClick={()=>void loadReport()}>Consultar</button>
</div>
  {report&&<>
<div className="metrics">
<article>
<small>Unidades vendidas</small>
<strong>{report.total_units}</strong>
</article>
<article>
<small>Productos diferentes</small>
<strong>{report.distinct_products}</strong>
</article>
<article>
<small>Importe vendido</small>
<strong>{mxn(report.total_revenue)}</strong>
</article>
<article>
<small>Personas atendidas</small>
<strong>{report.total_visitors}</strong>
</article>
</div>
<section className="panel data-panel">
<div className="table-wrap">
<table>
<thead>
<tr>
<th>Producto</th>
<th>Categoría</th>
<th>Unidades</th>
<th>Operaciones</th>
<th>Importe</th>
</tr>
</thead>
<tbody>{reportProducts.map(product=>
<tr key={`${product.product_id}-${product.product_name}`}>
<td>
<b>{product.product_name}</b>
</td>
<td>{product.category}</td>
<td>{product.quantity}</td>
<td>{product.sales_count}</td>
<td>
<b>{mxn(product.revenue)}</b>
</td>
</tr>)}</tbody>
</table>{!reportProducts.length&&<div className="empty">Sin ventas en el periodo.</div>}</div>
<Pagination page={reportPage} total={filteredReportProducts.length} onPage={setReportPage}/>
</section>
</>}
  {detail&&<Modal title={`Venta ${detail.folio}`} onClose={()=>setDetail(null)}>
<p className="muted-copy">{new Date(detail.created_at).toLocaleString('es-MX')} · {payment[detail.payment_method]}</p>
{detail.payments&&detail.payments.length>1&&<div className="detail-lines">{detail.payments.map(item=><p key={item.method}><span>{payment[item.method]}</span><b>{mxn(item.amount)}</b></p>)}</div>}<div className="detail-lines">{detail.items?.map(item=>
<p key={item.id}>
<span>{item.product_name} × {item.quantity}</span>
<b>{mxn(item.subtotal)}</b>
</p>)}</div>{Number(detail.tip_amount)>0&&<div className="detail-lines">
<p>
<span>Consumo</span>
<b>{mxn(detail.total)}</b>
</p>
<p>
<span>Cargo de servicio</span>
<b>{mxn(detail.tip_amount)}</b>
</p>
</div>}<div className="detail-total">
<span>Total pagado</span>
<strong>{mxn(detail.grand_total)}</strong>
</div>
<button className="primary full" onClick={()=>void print(detail.id)}>
<Printer size={17}/> Reimprimir ticket</button>
</Modal>}
 </>;
}
