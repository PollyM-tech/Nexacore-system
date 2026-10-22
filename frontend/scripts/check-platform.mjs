// Run from frontend: node scripts/check-platform.mjs. No browser automation.
import assert from 'node:assert/strict';
import {createServer} from 'vite';
import React from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import {MemoryRouter,Routes,Route} from 'react-router-dom';
import {QueryClient,QueryClientProvider} from '@tanstack/react-query';
import {readFile} from 'node:fs/promises';
const server=await createServer({optimizeDeps:{noDiscovery:true,entries:[]},server:{middlewareMode:true,ws:false,watch:null},appType:'custom'});
const clients=[];
const load=p=>server.ssrLoadModule('/src/'+p);
function client(){const c=new QueryClient({defaultOptions:{queries:{retry:false,retryOnMount:false,gcTime:Infinity,staleTime:Infinity}}});clients.push(c);return c;}
function render(Component,seeds=[],errors=[]){const qc=client();for(const [key,value]of seeds)qc.setQueryData(key,value);for(const [key,status]of errors)qc.getQueryCache().build(qc,{queryKey:key}).setState({status:'error',fetchStatus:'idle',error:{response:{status}}});const html=renderToStaticMarkup(React.createElement(QueryClientProvider,{client:qc},React.createElement(MemoryRouter,null,React.createElement(Component))));return {qc,html};}
const page=(rows,count=rows.length)=>({results:rows,count,next:count>10?'/next/':null,previous:null});
try{
 const {platformKeys:k,PLATFORM}=await load('features/platform/api.ts');
 const {PlatformProtectedRoute}=await load('features/platform/PlatformProtectedRoute.tsx');
 function Guard(){return React.createElement(Routes,null,React.createElement(Route,{element:React.createElement(PlatformProtectedRoute)},React.createElement(Route,{path:'/',element:React.createElement('p',null,'Authorized platform content')})));}
 let {html}=render(Guard,[],[[k.me,403]]);assert.ok(html.includes('Access denied')&&!html.includes('Authorized platform content'));
 ({html}=render(Guard,[[k.me,{is_platform_admin:true,user:{id:1,email:'root@example.test',username:'root'}}]]));assert.ok(html.includes('Authorized platform content'));
 ({html}=render(Guard,[[k.me,{is_platform_admin:false,user:{id:2}}]]));assert.ok(html.includes('Access denied')&&!html.includes('Authorized platform content'));
 ({html}=render(Guard,[],[[k.me,500]]));assert.ok(html.includes('Unable to load or save platform data')&&!html.includes('Authorized platform content'));
 const {PlatformDashboard}=await load('features/platform/PlatformDashboard.tsx');
 ({html}=render(PlatformDashboard,[[k.summary,{organizations:{total:12,active:10},users:{total:50},customers:{total:900,active:800},routers:{total:30,active:25},packages:{total:40,active:38}}]]));
 for(const v of ['Total ISPs','Enabled routers','900','800','25'])assert.ok(html.includes(v),v);
 ({html}=render(PlatformDashboard,[],[[k.summary,403]]));assert.ok(html.includes('Access denied')&&!html.includes('Total ISPs'));
 const {OrganizationsManager}=await load('features/platform/Organizations.tsx');
 const org={id:3,name:'ISP Three',slug:'isp-three',status:'active',is_active:true,member_count:18,customer_count:123,router_count:7,package_count:4,created_at:null};
 ({html}=render(OrganizationsManager,[[[...k.organizations,{page:1,page_size:10}],page([org],21)]]));
 for(const v of ['ISP Three','123','18','7','21 records'])assert.ok(html.includes(v),v);
 assert.ok(!html.includes('Delete organization')&&!html.includes('Remove organization'));
 const {PlatformUsers}=await load('features/platform/PlatformUsers.tsx');
 ({html}=render(PlatformUsers,[[[...k.users,{page:1,page_size:10}],page([{id:5,username:'owner',email:'owner@example.test',first_name:'ISP',last_name:'Owner',is_active:true,is_superuser:false,membership_count:2,password:'never-render-user-hash'}])]]));
 assert.ok(html.includes('owner@example.test')&&!html.includes('never-render-user-hash')&&!html.includes('Edit user')&&!html.includes('Delete user'));
 const {AuditMetadata,safeMetadataRows}=await load('features/platform/PlatformAudit.tsx');
 const metadata={safe:'<img src=x onerror=alert(1)>',password:'never-render',api_key:'never-render',nested:[{consumer_secret:'never-render',count:4}],record:{attribute:'Cleartext-Password',value:'never-render'}};
 assert.ok(!JSON.stringify(safeMetadataRows(metadata)).includes('never-render'));
 ({html}=render(()=>React.createElement(AuditMetadata,{value:metadata})));
 assert.ok(html.includes('&lt;img')&&!html.includes('<img')&&!html.includes('Cleartext-Password')&&!html.includes('consumer_secret'));
 assert.ok(safeMetadataRows(Object.fromEntries(Array.from({length:1000},(_,i)=>['field'+i,'x'.repeat(1000)]))).length<=20);
 ({html}=render(Guard,[],[[k.me,401]]));assert.ok(!html.includes("Authorized platform content"));
 const {PlatformError}=await load('features/platform/PlatformFeedback.tsx');
 ({html}=render(()=>React.createElement(PlatformError,{error:{response:{status:400,data:{role:['The last active owner cannot be removed.']}}}})));
 assert.ok(html.includes('last active owner cannot be removed'));

 const {usePlatformList}=await load('features/platform/PlatformList.tsx');
 const {useMembershipMutation,useOrganizationMutation}=await load('features/platform/queries.ts');
 const {api}=await load('shared/api/client.ts');
 const qc=client();let members,organizations;
 function Probe(){usePlatformList(k.audit,PLATFORM.audit,{organization:'3',user:'5',action:'platform.membership_updated',page:2,page_size:10});members=useMembershipMutation('3');organizations=useOrganizationMutation();return null;}
 renderToStaticMarkup(React.createElement(QueryClientProvider,{client:qc},React.createElement(MemoryRouter,null,React.createElement(Probe))));
 const requests=[];api.defaults.adapter=async config=>{requests.push(config);return {config,data:config.method==='get'?page([],40):org,status:200,statusText:'OK',headers:{}};};
 const params={organization:'3',user:'5',action:'platform.membership_updated',page:2,page_size:10};
 await qc.getQueryCache().find({queryKey:[...k.audit,params]}).fetch();assert.deepEqual(requests[0].params,params);assert.equal(requests[0].url,PLATFORM.audit);
 for(const key of [k.members('3'),k.organization('3'),k.organizations,k.users,k.summary,k.audit,['customers']])qc.setQueryData(key,{});
 await members.mutateAsync({id:10,body:{role:'admin',is_active:true}});
 assert.equal(requests[1].url,'/platform/organizations/3/members/10/');
 for(const key of [k.members('3'),k.organization('3'),k.organizations,k.users,k.summary,k.audit])assert.equal(qc.getQueryState(key).isInvalidated,true);
 assert.equal(qc.getQueryState(['customers']).isInvalidated,false);
 await organizations.mutateAsync({id:3,body:{status:'suspended'}});assert.equal(requests[2].method,'patch');assert.ok(!JSON.parse(requests[2].data).organization_id);
 const login=await readFile('src/features/auth/useLogin.ts','utf8');assert.ok(login.includes('removeQueries({ queryKey: ["platform"] })'));
 const pagination=await readFile('src/shared/components/data/TablePagination.tsx','utf8');assert.ok([...pagination.matchAll(/<button\b[^>]*>/g)].every(m=>m[0].includes('type="button"')));
 console.log('PASS: platform authorization, counts, read-only users, safe audit metadata, validation errors, pagination/filters and isolated mutation invalidation.');
}finally{for(const qc of clients)qc.clear();await server.close();}process.exit(0);
