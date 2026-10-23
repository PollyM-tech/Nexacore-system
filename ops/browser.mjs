// Executed inside the isolated Playwright container; credentials come from its test env.
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {writeFile} from 'node:fs/promises';
const require=createRequire('/tools/package.json');
const {chromium}=require('playwright');
const browser=await chromium.launch({headless:true});
const password=process.env.LINTECH_BROWSER_PASSWORD;
const base=process.env.LINTECH_BROWSER_BASE || 'http://frontend';
const checks=[];
async function test(name,fn){await fn();checks.push(name);console.log(`PASS: ${name}`);}
async function visible(page,selector){await selector.waitFor({state:'visible',timeout:20000});}
async function login(page,email,target='/admin',credential=password) {
  await page.goto(base+'/admin/login');
  await page.getByLabel('Email',{exact:true}).fill(email);
  await page.getByLabel('Password',{exact:true}).fill(credential);
  await page.getByRole('button',{name:'Sign in',exact:true}).click();
  await page.waitForURL(base+target,{timeout:20000});
}
async function noOverflow(page){assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth+2),'Page overflows viewport');}
const context=await browser.newContext({ignoreHTTPSErrors:true,viewport:{width:1440,height:1000}});
const page=await context.newPage();
const errors=[];page.on('pageerror',error=>errors.push(error.message));
try {
 await test('public branding, starting prices and login-only navigation',async()=>{
  await page.goto(base);await visible(page,page.getByRole('heading',{level:1}));
  const text=await page.locator('body').innerText();assert.ok(!/net\s*pulse|৳|\bUSD\b|\bKSh\b/i.test(text));
  await visible(page,page.getByRole('link',{name:'Admin Login',exact:true}).first());await visible(page,page.getByRole('link',{name:'Customer Login',exact:true}).first());
  for(const amount of ['1,500','2,000','3,000'])await visible(page,page.getByLabel(`From KES ${amount} / month`));
  assert.equal(await page.getByRole('link',{name:/sign up|create account/i}).count(),0);await noOverflow(page);
 });
 await test('real staff cookie login, CSRF bootstrap, identity and tenant isolation',async()=>{
  await login(page,'owner@example.test');await visible(page,page.getByText('Pilot Owner',{exact:true}));
  if(base.startsWith('https:')) {const cookies=await context.cookies();assert.ok(cookies.find(c=>c.name==='auth-jwt')?.secure);assert.ok(cookies.find(c=>c.name==='csrftoken')?.secure);const redirect=await page.request.get('http://frontend/admin/login',{maxRedirects:0});assert.ok([301,302,307,308].includes(redirect.status()));}
  await visible(page,page.getByText('Owner',{exact:true}).first());
  await visible(page,page.getByText('KES 1,250',{exact:true}).first());
  const summary=await page.request.get(base+'/api/reports/dashboard/');assert.equal(summary.status(),200);const data=await summary.json();assert.equal(data.customers.total,1);assert.equal(data.revenue.received.today,1250);
  assert.equal((await page.request.get(base+'/api/customers/PRIVATE1/')).status(),404);
  assert.equal((await page.request.post(base+'/api/auth/registration/',{data:{}})).status(),403);
 });
 await test('desktop admin routes and dark-mode persistence',async()=>{
  await page.getByRole('button',{name:'Toggle dark mode'}).click();assert.equal(await page.evaluate(()=>document.documentElement.classList.contains('dark')),true);
  await page.reload();await visible(page,page.getByRole('heading',{name:'Network overview',exact:true}));assert.equal(await page.evaluate(()=>document.documentElement.classList.contains('dark')),true);
  for(const route of ['/admin/customers','/admin/customers/ACCEPT1','/admin/packages','/admin/payments','/admin/billing','/admin/routers','/admin/tickets','/admin/settings']) {
   await page.goto(base+route);await visible(page,page.getByRole('heading',{level:1}).first());await noOverflow(page);
   assert.ok(!(await page.locator('body').innerText()).includes('Other Tenant Secret Name'));
  }
 });
 await test('NAS enrollment and hotspot plan/voucher workflows keep secrets out of normal reads',async()=>{
  await page.goto(base+'/admin/radius-nas');await page.getByRole('button',{name:'Add NAS device',exact:true}).click();
  await page.getByLabel('Device name',{exact:true}).fill('Acceptance Hotspot NAS');await page.getByLabel('Unique NAS / VPN IPv4 address',{exact:true}).fill('10.64.0.10');
  await page.getByLabel('RADIUS shared secret (32–128 characters)',{exact:false}).first().fill(password);
  await page.getByLabel('Create a RADIUS-only PPPoE router entry (no router API credentials)',{exact:true}).check();
  const created=page.waitForResponse(r=>r.url().endsWith('/radius/nas/')&&r.request().method()==='POST');await page.getByRole('button',{name:'Save NAS',exact:true}).click();const nasResponse=await created;assert.equal(nasResponse.status(),201);const nas=await nasResponse.json();assert.ok(!('shared_secret' in nas));assert.ok(nas.router);
  assert.equal((await page.request.get(base+'/api/internal/radius/client/10.64.0.10/')).status(),404);
  await page.goto(base+'/admin/hotspot');await page.getByRole('button',{name:'Create Hotspot plan',exact:true}).click();
  await page.getByLabel('Plan name',{exact:true}).fill('Acceptance Hotspot');await page.getByLabel('Price (whole KES)',{exact:true}).fill('50');
  const planCreated=page.waitForResponse(r=>r.url().endsWith('/hotspot/plans/')&&r.request().method()==='POST');await page.getByRole('button',{name:'Save plan',exact:true}).click();assert.equal((await planCreated).status(),201);
  await page.getByRole('button',{name:'Vouchers',exact:true}).click();await page.getByLabel('Active plan',{exact:true}).selectOption({label:'Acceptance Hotspot · KES 50'});await page.getByLabel('Voucher count (1–200)',{exact:true}).fill('2');
  await page.getByLabel('Batch label',{exact:true}).fill('Acceptance voucher batch');const batchCreated=page.waitForResponse(r=>r.url().endsWith('/hotspot/batches/')&&r.request().method()==='POST');await page.getByRole('button',{name:'Generate batch',exact:true}).click();assert.equal((await batchCreated).status(),201);
  await visible(page,page.getByText('Acceptance voucher batch',{exact:true}).first());
  const exported=page.waitForResponse(r=>r.url().endsWith('/export/')&&r.request().method()==='POST');await page.getByRole('button',{name:'Export / Print codes',exact:true}).first().click();const exportResponse=await exported;assert.equal(exportResponse.status(),200);assert.equal(exportResponse.headers()['cache-control'],'no-store');const codes=(await exportResponse.json()).vouchers.map(v=>v.code);
  await visible(page,page.getByRole('region',{name:'Voucher code sheet'}));const download=page.waitForEvent('download');await page.getByRole('button',{name:'Download CSV',exact:true}).click();assert.equal((await download).suggestedFilename(),'lintech-hotspot-vouchers.csv');
  await page.getByRole('button',{name:'Close and clear codes',exact:true}).click();const clearedText=await page.locator('body').innerText();assert.ok(codes.every(code=>!clearedText.includes(code)),'Codes leaked');
  page.once('dialog',dialog=>dialog.accept());const sale=page.waitForResponse(r=>r.url().endsWith('/sale/')&&r.request().method()==='POST');await page.getByRole('button',{name:'Record cash sale',exact:true}).first().click();assert.equal((await sale).status(),201);
  page.once('dialog',dialog=>dialog.accept());const revoked=page.waitForResponse(r=>r.url().endsWith('/revoke/')&&r.request().method()==='POST');await page.getByRole('button',{name:'Revoke',exact:true}).first().click();assert.equal((await revoked).status(),200);
  await page.setViewportSize({width:390,height:844});await noOverflow(page);await page.goto(base+'/hotspot/'+nas.public_id);await visible(page,page.getByText('Online purchase is not available yet. Obtain a voucher directly from your ISP.',{exact:true}));assert.equal(await page.getByRole('button',{name:'Request M-Pesa payment',exact:true}).isDisabled(),true);await noOverflow(page);
  await page.setViewportSize({width:1440,height:1000});
 });
 await test('mobile navigation and forms do not clip',async()=>{
  await page.setViewportSize({width:390,height:844});await page.goto(base+'/admin');await visible(page,page.getByRole('button',{name:'Open menu'}));await page.getByRole('button',{name:'Open menu'}).click();await visible(page,page.getByRole('link',{name:'Packages',exact:true}));await page.getByRole('link',{name:'Packages',exact:true}).click();await page.waitForURL(base+'/admin/packages');await noOverflow(page);
 });
 await test('ordinary ISP owner cannot enter the platform workspace',async()=>{
  await page.goto(base+'/superadmin');await visible(page,page.getByText(/Access denied/).first());
 });
 const platformContext=await browser.newContext({ignoreHTTPSErrors:true,viewport:{width:1440,height:1000}});const platformPage=await platformContext.newPage();platformPage.on('pageerror',error=>errors.push(error.message));
 await test('superadmin dashboard and organization account provisioning',async()=>{
  await login(platformPage,'platform@example.test');await platformPage.goto(base+'/superadmin');await visible(platformPage,platformPage.getByRole('heading',{name:'Platform dashboard',exact:true}));
  await platformPage.goto(base+'/superadmin/organizations/1');await visible(platformPage,platformPage.getByRole('button',{name:'Create staff account'}));await platformPage.getByRole('button',{name:'Create staff account'}).click();
  await platformPage.getByLabel('Username',{exact:true}).fill('acceptance-new-staff');await platformPage.getByLabel('Email',{exact:true}).fill('new-staff@example.test');await platformPage.getByLabel('ISP role',{exact:true}).selectOption('support');
  await platformPage.getByLabel('Initial password',{exact:false}).first().fill(password);await platformPage.getByLabel('Confirm password',{exact:false}).first().fill(password);
  const response=platformPage.waitForResponse(r=>r.url().endsWith('/organizations/1/users/')&&r.request().method()==='POST');await platformPage.getByRole('button',{name:'Create account',exact:true}).click();assert.equal((await response).status(),201);
  await visible(platformPage,platformPage.getByText('acceptance-new-staff',{exact:false}).first());
 });
 const portalContext=await browser.newContext({ignoreHTTPSErrors:true,viewport:{width:390,height:844}});const portal=await portalContext.newPage();portal.on('pageerror',error=>errors.push(error.message));
 await test('customer PPPoE login with organization code and KES balances',async()=>{
  await portal.goto(base+'/portal/login');await portal.getByLabel('ISP organization code').fill('acceptance');await portal.getByLabel('PPPoE username').fill('pilot-subscriber');await portal.getByLabel('Password',{exact:true}).fill(password);await portal.getByRole('button',{name:'Sign in',exact:true}).click();await portal.waitForURL(base+'/portal',{timeout:20000});await visible(portal,portal.getByText('KES -250',{exact:true}).first());await noOverflow(portal);
  await portal.getByRole('button',{name:'Toggle dark mode'}).click();assert.equal(await portal.evaluate(()=>document.documentElement.classList.contains('dark')),true);await portal.reload();assert.equal(await portal.evaluate(()=>document.documentElement.classList.contains('dark')),true);
 });
 await test('customer ticket reaches ISP support and support reply reaches customer',async()=>{
  await portal.goto(base+'/portal/tickets');await portal.getByLabel('Subject').fill('Acceptance connection issue');await portal.getByLabel('Describe the issue').fill('Disposable test ticket to verify customer and support workflow.');await portal.getByRole('button',{name:'Submit ticket'}).click();await visible(portal,portal.getByRole('button',{name:/Acceptance connection issue/}));
  await page.setViewportSize({width:1440,height:1000});await page.goto(base+'/admin/tickets');await visible(page,page.getByText('Acceptance connection issue',{exact:true}));await page.getByRole('button',{name:'View thread'}).first().click();await page.getByLabel('Ticket status').selectOption('in_progress');await page.getByLabel('Support reply').fill('Acceptance support response: connection investigation started.');await page.getByRole('button',{name:'Reply',exact:true}).click();await visible(page,page.getByText('Acceptance support response: connection investigation started.',{exact:true}));
  await portal.getByRole('button',{name:/Acceptance connection issue/}).click();await visible(portal,portal.getByText('Acceptance support response: connection investigation started.',{exact:false}).first());await noOverflow(portal);
  await page.getByRole('button',{name:'Close',exact:true}).click();
 });
 await test('new staff account can replace its initial password and old access is revoked',async()=>{
  const staffContext=await browser.newContext({ignoreHTTPSErrors:true,viewport:{width:1280,height:900}});const staff=await staffContext.newPage();staff.on('pageerror',error=>errors.push(error.message));
  await login(staff,'new-staff@example.test');await staff.goto(base+'/admin/settings');
  await staff.getByLabel('Current account password',{exact:false}).first().fill(password);
  await staff.getByLabel('New account password',{exact:false}).first().fill(password+'-changed');
  await staff.getByLabel('Confirm new account password',{exact:false}).first().fill(password+'-changed');
  const changed=staff.waitForResponse(r=>r.url().endsWith('/auth/password/change/')&&r.request().method()==='POST');await staff.getByRole('button',{name:'Change account password',exact:true}).click();assert.equal((await changed).status(),200);
  assert.equal((await staff.request.get(base+'/api/auth/user/')).status(),401);
  await login(staff,'new-staff@example.test','/admin',password+'-changed');await visible(staff,staff.getByText('Support',{exact:true}).first());await staffContext.close();
 });
 await test('staff and customer sign-out invalidate their UI sessions',async()=>{
  await page.getByRole('button',{name:/Pilot Owner/}).click();await page.getByText('Sign out',{exact:true}).click();await page.waitForURL(base+'/admin/login');
  await portal.getByRole('button',{name:'Sign out',exact:true}).click();await portal.waitForURL(base+'/portal/login');
 });
 assert.deepEqual(errors,[],'Browser JavaScript exceptions');
 await writeFile('/results/browser.json',JSON.stringify({status:'passed',checks,viewports:['1440x1000','390x844'],browser:'Chromium',https_test:'ephemeral internal CA; public certificate still requires an owned domain',checked_at:new Date().toISOString()},null,2));
} catch(error) {
 await page.screenshot({path:'/results/browser-failure.png',fullPage:true}).catch(()=>{});
 // No page dumps or request logs: they can include credentials.
 throw new Error(String(error.message).replaceAll(password, "[redacted test credential]"));
} finally {await browser.close();}
