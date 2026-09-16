import {CheckCircle2,TriangleAlert,X} from 'lucide-react';
export interface NoticeState{message:string;error?:boolean}
export function Notice({notice,onClose}:{notice:NoticeState|null;onClose:()=>void}){if(!notice)return null;const Icon=notice.error?TriangleAlert:CheckCircle2;return <div className={`notice ${notice.error?'error':''}`}><Icon size={18}/><span>{notice.message}</span><button onClick={onClose}><X size={16}/></button></div>}
