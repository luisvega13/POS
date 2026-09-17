export type ValueMode='amount'|'percent';
export function ValueModeToggle({mode,onChange,label,disabled=false}:{mode:ValueMode;onChange:(mode:ValueMode)=>void;label:string;disabled?:boolean}){
 const next=mode==='amount'?'percent':'amount';
 return <button type="button" disabled={disabled} className="value-mode-toggle" role="switch" aria-checked={mode==='percent'} aria-label={`${label}: ${mode==='amount'?'monto fijo':'porcentaje'}`} title={`Cambiar a ${next==='amount'?'monto fijo':'porcentaje'}`} onClick={()=>onChange(next)}><span className={mode==='amount'?'active':''}>$</span><span className={mode==='percent'?'active':''}>%</span></button>;
}
