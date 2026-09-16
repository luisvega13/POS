import {useCallback,useEffect,useState} from 'react';
import {Navigate,Route,Routes} from 'react-router-dom';
import {api} from './api';
import {Layout} from './components/Layout';
import {Notice,type NoticeState} from './components/Notice';
import {VirtualTicketModal} from './components/VirtualTicketModal';
import {CashPage} from './pages/CashPage';
import {AuditPage} from './pages/AuditPage';
import {LoginPage} from './pages/LoginPage';
import {PosPage} from './pages/PosPage';
import {ProductsPage} from './pages/ProductsPage';
import {SalesPage} from './pages/SalesPage';
import {SettingsPage} from './pages/SettingsPage';
import {TablesPage} from './pages/TablesPage';
import {UsersPage} from './pages/UsersPage';
import type {AuthStatus,BusinessConfig,Category,Permissions,Product,User,UserRole} from './types';

const defaultPermissions:Permissions={cashier_table_access:true,waiter_print_account:true,waiter_transfer_mode:'allowed',cashier_transfer_mode:'allowed',waiter_cancel_mode:'allowed',cashier_cancel_mode:'allowed',include_tip_in_ticket:true,service_charge_percent:10,include_suggested_tip:false,suggested_tip_percent:10,print_on_checkout:true,waiter_require_guest_count:false,developer_mode:false};

export default function App(){
 const [auth,setAuth]=useState<AuthStatus|null>(null),[permissions,setPermissions]=useState<Permissions>(defaultPermissions),[products,setProducts]=useState<Product[]>([]),[categories,setCategories]=useState<Category[]>([]),[business,setBusiness]=useState('MI NEGOCIO'),[cashOpen,setCashOpen]=useState(false),[notice,setNotice]=useState<NoticeState|null>(null),[virtualTicket,setVirtualTicket]=useState(''),[loading,setLoading]=useState(true);
 const notify=useCallback((message:string,error=false)=>{setNotice({message,error});window.setTimeout(()=>setNotice(null),6000)},[]);
 const refresh=useCallback(async()=>{try{const [active,all,cats,cash,config]=await Promise.all([api.products(),api.products(true),api.categories(),api.cash(),api.config()]);setProducts(active);setCategories(cats);setCashOpen(cash.open);setBusiness(config.business_name);return all}catch(e){notify((e as Error).message,true);return []}finally{setLoading(false)}},[notify]);
 useEffect(()=>{api.authStatus().then(setAuth).catch(()=>setAuth({setup_required:false,authenticated:false,user:null}))},[]);
 useEffect(()=>{const show=(event:Event)=>setVirtualTicket((event as CustomEvent<string>).detail);window.addEventListener('virtual-ticket',show);return()=>window.removeEventListener('virtual-ticket',show)},[]);
 useEffect(()=>{if(auth?.authenticated){void refresh();void api.permissions().then(setPermissions)}},[auth?.authenticated,refresh]);
 if(!auth)return <div className="loading"><span/><p>Preparando sistema…</p></div>;
 if(!auth.authenticated||!auth.user)return <LoginPage setup={auth.setup_required} onAuthenticated={(user:User)=>setAuth({setup_required:false,authenticated:true,user})}/>;
 const user=auth.user,home=user.role==='waiter'?'/mesas':'/pos',loader=<div className="loading"><span/><p>Preparando punto de venta…</p></div>;
 const allowed=(roles:UserRole[],element:React.ReactNode)=>roles.includes(user.role)?element:<Navigate to={home} replace/>;
 async function logout(){await api.logout();setAuth({setup_required:false,authenticated:false,user:null});setProducts([]);setCategories([])}
 return <Layout business={business} cashOpen={cashOpen} user={user} permissions={permissions} onLogout={()=>void logout()}><Notice notice={notice} onClose={()=>setNotice(null)}/>{virtualTicket&&<VirtualTicketModal ticket={virtualTicket} onClose={()=>setVirtualTicket('')}/>}<Routes>
  <Route path="/" element={<Navigate to={home} replace/>}/>
  <Route path="/pos" element={allowed(['admin','cashier'],loading?loader:<PosPage products={products} cashOpen={cashOpen} permissions={permissions} onReload={()=>void refresh()} onNotice={notify}/>)}/>
  <Route path="/mesas" element={user.role==='cashier'&&!permissions.cashier_table_access?<Navigate to="/pos" replace/>:loading?loader:<TablesPage products={products} cashOpen={cashOpen} role={user.role} permissions={permissions} onReload={()=>void refresh()} onNotice={notify}/>}/>
  <Route path="/productos" element={allowed(['admin'],loading?loader:<ProductContainer categories={categories} refresh={refresh} notify={notify}/>)}/>
  <Route path="/categorias" element={<Navigate to="/productos" replace/>}/>
  <Route path="/ventas" element={allowed(['admin','cashier'],loading?loader:<SalesPage onNotice={notify}/>)}/>
  <Route path="/caja" element={allowed(['admin','cashier'],loading?loader:<CashPage role={user.role} onStatus={setCashOpen} onNotice={notify}/>)}/>
  <Route path="/auditoria" element={allowed(['admin'],<AuditPage onNotice={notify}/>)}/>
  <Route path="/usuarios" element={allowed(['admin'],<UsersPage permissions={permissions} onPermissions={setPermissions} onNotice={notify}/>)}/>
  <Route path="/configuracion" element={allowed(['admin'],loading?loader:<SettingsPage permissions={permissions} onPermissions={setPermissions} onSaved={(config:BusinessConfig)=>setBusiness(config.business_name)} onNotice={notify}/>)}/>
  <Route path="*" element={<Navigate to={home} replace/>}/>
 </Routes></Layout>;
}

function ProductContainer({categories,refresh,notify}:{categories:Category[];refresh:()=>Promise<Product[]>;notify:(message:string,error?:boolean)=>void}){
 const [all,setAll]=useState<Product[]>([]);const load=useCallback(async()=>setAll(await refresh()),[refresh]);useEffect(()=>{void load()},[load]);
 return <ProductsPage products={all} categories={categories} onRefresh={load} onNotice={notify}/>;
}
