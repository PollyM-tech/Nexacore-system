// Run from frontend: node scripts/check-landing.mjs. No browser/dependencies required.
import assert from 'node:assert/strict';
import {createServer} from 'vite';
import React from 'react';
import {MemoryRouter} from 'react-router-dom';
import {QueryClient, QueryClientProvider} from '@tanstack/react-query';
import {renderToStaticMarkup} from 'react-dom/server';
import {readFile} from 'node:fs/promises';
const server=await createServer({optimizeDeps:{noDiscovery:true,entries:[]},server:{middlewareMode:true,ws:false,watch:null},appType:'custom'});
try {
 const {AuthLayout}=await server.ssrLoadModule('/src/shared/components/layout/AuthLayout.tsx');
 const loginHtml=renderToStaticMarkup(React.createElement(AuthLayout,null,React.createElement('div',null,'Sign in')));
 assert.ok(loginHtml.includes('Lintech ISP Management') && loginHtml.includes('alt="Lintech"'));
 assert.ok(!/net\s*pulse|netulse|ISP Control Center/i.test(loginHtml));
 const {PortalLoginPage}=await server.ssrLoadModule('/src/pages/PortalLoginPage.tsx');
 const savedStorage=globalThis.localStorage;
 Object.defineProperty(globalThis,'localStorage',{configurable:true,value:{getItem:()=>null}});
 const portalClient=new QueryClient();
 try {
  const portalHtml=renderToStaticMarkup(React.createElement(QueryClientProvider,{client:portalClient},React.createElement(MemoryRouter,null,React.createElement(PortalLoginPage))));
  assert.ok(portalHtml.includes('Lintech ISP Management') && portalHtml.includes('alt="Lintech"'));
  assert.ok(portalHtml.includes('Customer Portal') && portalHtml.includes('PPPoE username'));
  assert.ok(!/net\s*pulse|netulse|ISP Control Center/i.test(portalHtml));
 } finally {portalClient.clear();Object.defineProperty(globalThis,'localStorage',{configurable:true,value:savedStorage});}
 const {LandingPage}=await server.ssrLoadModule('/src/pages/LandingPage.tsx');
 // Deliberately no query provider: public pricing must not fetch tenant packages.
 const html=renderToStaticMarkup(React.createElement(LandingPage));
 const text=html.replace(/<[^>]*>/g,' ').replace(/\s+/g,' ');
 for(const amount of ['1,500','2,000','3,000'])assert.ok(html.includes(`aria-label="From KES ${amount} / month"`));
 for(const title of ['Hotspot Only','PPPoE Only','Full Stack','Transparent pricing','Plans visible at a glance.','Enterprise'])assert.ok(text.includes(title),title);
 assert.equal((html.match(/<article\b/g)||[]).length,3);
 assert.ok(!/WISPMAN|Net\s*Pulse|per[- ]active|per[- ]user|per subscriber|\b(?:100|200|300|500)\s+(?:users|subscribers|customers)\b/i.test(text));
 assert.ok(text.includes('Final pricing depends on the number of active subscribers'));
 assert.ok(!text.includes('Hotspot functionality is still being completed'));
 assert.ok(!text.includes('Hotspot operations are being completed separately'));
 assert.ok(html.includes('bg-ink-900 text-white'));
 for(const id of ['features','pricing','workflow','contact'])assert.ok(html.includes(`id="${id}"`),id);
 const anchors=[...html.matchAll(/<a\b[^>]*href="([^"]*)"[^>]*>([\s\S]*?)<\/a>/g)].map(m=>({href:m[1],text:m[2].replace(/<[^>]*>/g,' ').trim()}));
 const quotes=anchors.filter(a=>a.text.startsWith('Request Quote') && !a.text.includes('WhatsApp'));
 assert.equal(quotes.length,4);assert.ok(quotes.every(a=>a.href==='#contact'));
 assert.ok(anchors.some(a=>a.text==='Talk to Us'&&a.href==='#contact'));
 assert.ok(anchors.some(a=>a.text==='View Pricing'&&a.href==='#pricing'));
 assert.ok(anchors.some(a=>a.text==='Admin Login'&&a.href==='/admin/login'));
 assert.ok(anchors.some(a=>a.text==='Customer Login'&&a.href==='/portal/login'));
 assert.ok(!anchors.some(a=>/sign up|create account/i.test(a.text)));
 for(const title of ['Features','Pricing','Workflow','Contact','Staff Login'])assert.ok(anchors.some(a=>a.text===title),title);
 assert.ok(anchors.some(a=>a.href==='tel:+254714660729'));
 assert.ok(anchors.some(a=>a.href.startsWith('https://wa.me/254714660729?')));
 assert.ok(html.includes('alt="Lintech"')&&html.includes('logo.png'));
 assert.ok(!/static[- ]ip service/i.test(text));
 const pricing=await readFile('src/features/landing/LandingPricing.tsx','utf8');
 assert.ok(!/usePackages|axios|useQuery|\/api\//.test(pricing));
 const styles=await readFile('src/index.css','utf8');
 assert.ok(styles.includes('prefers-reduced-motion: no-preference')&&styles.includes('scroll-behavior: smooth'));
 console.log('PASS: three starting-price cards, no public calculations, compact pricing and requested notice removal, contact/hero/nav links, official logo and API-independent pricing.');
} finally {await server.close();}process.exit(0);
