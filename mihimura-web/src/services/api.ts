import { platformApi } from './platformApi';
export type DashboardPayload = any;
export async function fetchDashboard(){try{const payload=await platformApi.dashboard();return {...payload,_connection:'backend'}}catch{return import('../data/mockApi').then(m=>({generatedAt:new Date().toISOString(),source:'demo',_connection:'demo',summary:{cropHealth:64,cropHealthChange:2.4,atRiskArea:625,newlyAtRiskArea:18,waterDeficit:18,irrigationNeed:36400,activeThreats:17,criticalThreats:2,yieldProtected:14.8},provinces:m.provinceData,priorityActions:[],changes:[],agentActivity:[]}))}}
export async function askMihimura(question:string,province='Eastern'){return platformApi.ask(question,{province,lat:7.291,lon:81.674,scope:'national-overview'})}
