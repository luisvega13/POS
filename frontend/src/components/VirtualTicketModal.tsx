import {Code2} from 'lucide-react';
import {Modal} from './Modal';

export function VirtualTicketModal({ticket,onClose}:{ticket:string;onClose:()=>void}){
 return <Modal title="Ticket virtual" onClose={onClose}><div className="virtual-ticket-note"><Code2 size={17}/><span>Modo desarrollador activo. Este ticket no fue enviado a la impresora.</span></div><pre className="virtual-ticket-paper">{ticket}</pre><button className="primary full" onClick={onClose}>Cerrar vista previa</button></Modal>;
}
