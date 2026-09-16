import {Boxes,ChartNoAxesColumn,ClipboardList,History,LayoutGrid,LogOut,Settings,Store,UsersRound,UtensilsCrossed} from 'lucide-react';
import type {ReactNode} from 'react';
import {NavLink,useLocation} from 'react-router-dom';
import type {Permissions,User,UserRole} from '../types';

const items=[
 {path:'/pos',label:'Punto de venta',icon:LayoutGrid,roles:['admin','cashier']},
 {path:'/mesas',label:'Mesas',icon:UtensilsCrossed,roles:['admin','cashier','waiter']},
 {path:'/productos',label:'Productos',icon:Boxes,roles:['admin']},
 {path:'/ventas',label:'Ventas y reportes',icon:History,roles:['admin','cashier']},
 {path:'/caja',label:'Corte de caja',icon:ChartNoAxesColumn,roles:['admin','cashier']},
 {path:'/auditoria',label:'Auditoría',icon:ClipboardList,roles:['admin']},
 {path:'/usuarios',label:'Usuarios',icon:UsersRound,roles:['admin']},
 {path:'/configuracion',label:'Configuración',icon:Settings,roles:['admin']}
] as const;
const roleNames:Record<UserRole,string>={admin:'Administrador',cashier:'Caja',waiter:'Mesero'};
export function Layout({business,cashOpen,user,permissions,onLogout,children}:{business:string;cashOpen:boolean;user:User;permissions:Permissions;onLogout:()=>void;children:ReactNode}){
 const location=useLocation(),available=items.filter(item=>(item.roles as readonly UserRole[]).includes(user.role)&&!(item.path==='/mesas'&&user.role==='cashier'&&!permissions.cashier_table_access)),title=items.find(item=>location.pathname===item.path)?.label??available[0]?.label;
 return <div className="app-shell"><aside className="sidebar"><div className="brand"><span><Store size={18}/></span><strong>{business}</strong></div><nav>{available.map(({path,label,icon:Icon})=><NavLink key={path} to={path} className={({isActive})=>isActive?'active':''}><Icon size={19}/><span>{label}</span></NavLink>)}</nav><div className="sidebar-account"><div><b>{user.display_name}</b><small>{roleNames[user.role]}</small></div><button onClick={onLogout} aria-label="Cerrar sesión" title="Cerrar sesión"><LogOut size={17}/></button></div><div className={`cash-state ${cashOpen?'open':''}`}><i/>{cashOpen?'Caja abierta':'Caja cerrada'}</div></aside><main><header className="topbar"><div><small>OPERACIÓN</small><h1>{title}</h1></div><time>{new Date().toLocaleDateString('es-MX',{weekday:'long',day:'numeric',month:'long'})}</time></header>{children}</main></div>;
}
