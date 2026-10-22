// Run from frontend: node scripts/check-admin.mjs. No browser or extra packages.
import assert from 'node:assert/strict';
import { createServer } from 'vite';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { readFile } from 'node:fs/promises';

const server = await createServer({ optimizeDeps: { noDiscovery: true, entries: [] }, server: { middlewareMode: true, ws: false, watch: null }, appType: 'custom' });
const clients = [];
const load = path => server.ssrLoadModule(`/src/${path}`);
const key = (name, params = {}) => [name, 'admin-list', { page: 1, search: '', ...params }];
const paginated = (results, count = results.length) => ({ results, count, next: count > 10 ? '/next/' : null, previous: null });
function client() { const qc = new QueryClient({ defaultOptions: { queries: { retry: false, retryOnMount: false, gcTime: Infinity } } }); clients.push(qc); return qc; }
function render(Component, seeds = [], errors = []) {
  const qc = client();
  for (const [queryKey, data] of seeds) qc.setQueryData(queryKey, data);
  for (const queryKey of errors) qc.getQueryCache().build(qc, { queryKey }).setState({ status: 'error', fetchStatus: 'idle', error: new Error('Unavailable'), data: undefined });
  const html = renderToStaticMarkup(React.createElement(QueryClientProvider, { client: qc }, React.createElement(MemoryRouter, null, React.createElement(Component))));
  return { html, qc };
}
try {
  const { RoutersManager } = await load('features/routers/RoutersManager.tsx');
  const router = { id: 1, name: 'Core', host: '10.0.0.1', port: 8728, is_active: true, status: 'disconnected', password: 'must-never-render', last_checked: null };
  let { html } = render(RoutersManager, [[key('routers'), paginated([router])]]);
  assert.ok(html.includes('Disconnected') || html.includes('disconnected'));
  assert.ok(html.includes('Enabled') && html.includes('Test connection'));
  assert.ok(!html.includes('must-never-render') && !html.includes('aria-label="Delete"'));

  const { PaymentsHistory } = await load('features/payments/PaymentsHistory.tsx');
  const ledger = [{ id: 1, customer_name: 'Alice', amount: '1500', payment_method: 'mpesa', transaction_id: 'MPESA-RECEIPT' }, { id: 2, customer_name: 'Bob', amount: '-200', payment_method: 'adjustment' }];
  ({ html } = render(PaymentsHistory, [[key('transactions'), paginated(ledger, 21)]]));
  for (const text of ['M-Pesa', 'MPESA-RECEIPT', 'Ledger adjustment', 'not received income', 'KES', 'Next', '21 records']) assert.ok(html.includes(text), text);
  assert.ok(!html.includes('৳') && !html.includes('NaN'));
  ({ html } = render(PaymentsHistory, [], [key('transactions')]));
  assert.ok(html.includes('Could not load this list') && !html.includes('No payments yet'));

  const { MonthlyBillsList } = await load('features/billing/MonthlyBillsList.tsx');
  ({ html } = render(MonthlyBillsList, [[key('monthly-bills'), paginated([{ id: 1, customer_name: 'Alice', total_amount: '1500', paid_amount: '500', remaining_amount: '1000', payment_status: 'partial' }])]]));
  for (const text of ['Allocated / paid', 'Outstanding', 'invoice allocations', 'KES']) assert.ok(html.includes(text), text);
  const { ZonesManager } = await load('features/zones/ZonesManager.tsx');
  ({ html } = render(ZonesManager, [[key('zones'), paginated([{ id: 1, name: 'North' }])]]));
  assert.ok(html.includes('North') && !html.includes('aria-label="Delete"'));

  const { LiveUsageView } = await load('features/bandwidth/LiveUsageView.tsx');
  ({ html } = render(LiveUsageView, [[['bandwidth-live', ''], { router_connected: false, router_count: 1, online_clients: 0, sessions: [] }], [['admin-options', 'routers'], [router]]]));
  assert.ok(html.includes('Unable to verify sessions') && html.includes('RADIUS accounting'));
  assert.ok(!html.includes('No sessions detected'));
  ({ html } = render(LiveUsageView, [[['admin-options', 'routers'], [router]]], [['bandwidth-live', '']]));
  assert.ok(html.includes('RouterOS live data unavailable'));

  const { SettingsPage } = await load('pages/SettingsPage.tsx');
  ({ html } = render(SettingsPage, [[['session'], { pk: 7, email: 'operator@example.test' }]]));
  assert.ok(html.includes('operator@example.test') && html.includes('Not supplied by the account API'));
  assert.ok(!/net\s*pulse/i.test(html) && !html.includes(">Administrator<"));
  const { UserMenu } = await load('shared/components/layout/UserMenu.tsx');
  const { platformKeys } = await load('features/platform/api.ts');
  ({ html } = render(UserMenu, [[['session'], {email:'operator@example.test',first_name:'Pat',last_name:'Morgan'}], [platformKeys.me, {is_platform_admin:true}]]));
  assert.ok(html.includes('Pat Morgan') && html.includes('Superadmin'));
  ({ html } = render(UserMenu, [[['session'], {email:'operator@example.test',first_name:'Pat'}]], [platformKeys.me]));
  assert.ok(html.includes('Pat') && html.includes('Role unavailable') && !html.includes('Superadmin'));
  ({ html } = render(UserMenu, [[['session'], {email:'operator@example.test',username:'operator',is_platform_admin:true,membership:{role:'owner',role_label:'Owner',organization:{id:1,name:'Example ISP'}}}]], [platformKeys.me]));
  assert.ok(html.includes('Superadmin · Owner') && html.includes('operator'));
  const { DASHBOARD_TONES } = await load('shared/constants/dashboardTones.ts');
  assert.equal(DASHBOARD_TONES.length,6);
  for (const tone of DASHBOARD_TONES) assert.ok(tone.includes('from-') && tone.includes('to-'));
  for (const shell of ['TopBar','PortalShell']) assert.ok((await readFile(`src/shared/components/layout/${shell}.tsx`,'utf8')).includes('<DarkThemeToggle'));
  const startup = await readFile('src/main.tsx','utf8');
  assert.ok(startup.includes('defaultMode: "light"') && !startup.includes('localStorage.setItem'));
  const { API } = await load('shared/api/endpoints.ts');
  assert.equal(API.scheduler, '/scheduler/tasks/');

  const { OnusManager } = await load('features/olt/OnusManager.tsx');
  ({ html } = render(OnusManager, [[key('onus'), [{ id: 1, serial_number: 'ONU-1', onu_index: '1', status: 'unknown', olt_name: 'OLT', rx_power: null }]], [['admin-options', 'olt-devices'], []]]));
  assert.ok(html.includes('ONU-1') && html.includes('pending safe tenant validation'));
  assert.ok(!html.includes('Add ONU') && !html.includes('aria-label="Delete"'));
  const { SchedulerTaskList } = await load('features/scheduler/SchedulerTaskList.tsx');
  ({ html } = render(SchedulerTaskList, [[['scheduler'], [{ task_id: 'billing', name: 'Billing schedule', status: 'off', next_run: null }]]]));
  assert.ok(html.includes('Billing schedule') && !html.includes('Run now'));
  const { SmsGateways } = await load('features/sms/SmsGateways.tsx');
  ({ html } = render(SmsGateways, [[key('sms-gateways'), [{ id: 1, label: 'Gateway', provider: 'africastalking', is_active: true, is_default: true, credentials: { api_key: 'provider-secret-never-render' } }]]]));
  assert.ok(!html.includes('provider-secret-never-render'));

  // Execute the query functions against a local adapter, preserving pagination
  // metadata and ensuring complete options do not stop after page one.
  const { AdminResourceList } = await load('features/admin/AdminResourceList.tsx');
  const { api } = await load('shared/api/client.ts');
  const { useAdminOptions } = await load('features/admin/useAdminOptions.ts');
  const { useAdminCrud } = await load('features/admin/useAdminCrud.ts');
  const qc = client(); let mutations;
  function Probe() {
    useAdminOptions('routers', API.routers); mutations = useAdminCrud('routers', API.routers);
    return React.createElement(AdminResourceList, { queryKey: 'transactions', url: API.billing.transactions, params: { payment_method: 'mpesa' }, columns: [], rowKey: r => r.id, emptyTitle: 'Empty', emptyDescription: '' });
  }
  renderToStaticMarkup(React.createElement(QueryClientProvider, { client: qc }, React.createElement(Probe)));
  const requests = [];
  api.defaults.adapter = async config => {
    requests.push(config);
    const data = config.url === API.routers && config.method === 'get' ? { results: [router], count: 2, next: config.params.page === 1 ? '/next/' : null } : paginated(ledger, 21);
    return { config, data, status: 200, statusText: 'OK', headers: {} };
  };
  const paymentQuery = qc.getQueryCache().find({ queryKey: key('transactions', { payment_method: 'mpesa' }) });
  await paymentQuery.fetch();
  assert.equal(paymentQuery.state.data.count, 21);
  assert.equal(requests[0].params.payment_method, 'mpesa');
  assert.equal(requests[0].params.page_size, 10);
  assert.equal(requests[0].params.search, undefined);
  await qc.getQueryCache().find({ queryKey: ['admin-options', 'routers'] }).fetch();
  assert.equal(qc.getQueryData(['admin-options', 'routers']).length, 2);
  for (const k of [['routers'], ['customer-options', 'routers'], ['bandwidth-live'], ['dashboard-summary'], ['unrelated']]) qc.setQueryData(k, {});
  await mutations.update.mutateAsync({ id: 1, body: { description: 'Updated' } });
  for (const k of [['routers'], ['customer-options', 'routers'], ['bandwidth-live'], ['dashboard-summary']]) assert.equal(qc.getQueryState(k).isInvalidated, true);
  assert.equal(qc.getQueryState(['unrelated']).isInvalidated, false);

  // Secret preservation on edit and safety controls are also checked at source
  // because Flowbite portals do not render open dialogs during SSR.
  const routerForm = await readFile('src/features/routers/RouterForm.tsx', 'utf8');
  assert.ok(!routerForm.includes('initial.password'));
  assert.ok(routerForm.includes('if (!initial || f.password) body.password = f.password'));
  const oltForm = await readFile('src/features/olt/OltDeviceForm.tsx', 'utf8');
  assert.ok(!oltForm.includes('initial.telnet_password') && !oltForm.includes('initial.snmp_community'));
  const gatewayForm = await readFile('src/features/sms/SmsGatewayForm.tsx', 'utf8');
  assert.ok(gatewayForm.includes('replaceCredentials ? {credentials: out} : {}'));
  console.log('PASS: remaining-admin render/query checks, pagination, KES, ledger semantics, secret preservation, safe actions, failure states and targeted invalidation.');
} finally {
  for (const qc of clients) qc.clear();
  await server.close();
}
process.exit(0);
