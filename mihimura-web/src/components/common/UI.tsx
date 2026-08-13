import type { ReactNode } from 'react';
import { CheckCircle2, Info, TriangleAlert } from 'lucide-react';

export function Button({children,onClick,variant='primary',type='button',disabled=false,className=''}:{children:ReactNode,onClick?:()=>void,variant?:'primary'|'secondary'|'ghost'|'danger',type?:'button'|'submit',disabled?:boolean,className?:string}){
 return <button type={type} disabled={disabled} className={`ui-btn ${variant} ${className}`} onClick={onClick}>{children}</button>
}
export function Card({title,subtitle,action,children,className=''}:{title?:string,subtitle?:string,action?:ReactNode,children:ReactNode,className?:string}){
 return <section className={`ui-card ${className}`}><header className="ui-card-header"><div>{title&&<h3>{title}</h3>}{subtitle&&<p>{subtitle}</p>}</div>{action}</header>{children}</section>
}
export function Status({children,tone='green'}:{children:ReactNode,tone?:'green'|'amber'|'orange'|'red'|'blue'|'purple'|'gray'}){return <span className={`ui-status ${tone}`}>{children}</span>}
export function Metric({label,value,note,icon:Icon,tone='green'}:{label:string,value:string|number,note?:string,icon:any,tone?:string}){return <div className={`ui-metric tone-${tone}`}><span className="ui-metric-icon"><Icon size={19}/></span><div><small>{label}</small><strong>{value}</strong>{note&&<em>{note}</em>}</div></div>}
export function Empty({title,detail}:{title:string,detail?:string}){return <div className="empty-box"><Info/><b>{title}</b>{detail&&<p>{detail}</p>}</div>}
export function Notice({tone='info',title,children}:{tone?:'info'|'warning'|'success'|'danger',title:string,children:ReactNode}){const Icon=tone==='success'?CheckCircle2:tone==='info'?Info:TriangleAlert;return <div className={`notice ${tone}`}><Icon/><div><b>{title}</b><p>{children}</p></div></div>}
