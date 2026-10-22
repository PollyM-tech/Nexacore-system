// Run from frontend: node scripts/check-currency.mjs.
import assert from 'node:assert/strict';
import { createServer } from 'vite';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
const server = await createServer({ optimizeDeps: { noDiscovery: true, entries: [] }, server: { middlewareMode: true, ws: false, watch: null }, appType: 'custom' });
try {
  const { formatKES, kes, money, compactKes, compact } = await server.ssrLoadModule('/src/shared/utils/format.ts');
  assert.equal(kes, formatKES);
  assert.equal(money, formatKES);
  assert.equal(compact, compactKes);
  for (const [input, expected] of [[0,'KES 0'],[1500,'KES 1,500'],['2000.00','KES 2,000'],['1250.50','KES 1,250.50'],[25450,'KES 25,450'],[-1200.25,'KES -1,200.25'],[1000000,'KES 1,000,000']]) assert.equal(formatKES(input), expected);
  for (const invalid of [undefined,null,'',' ',NaN,Infinity,'invalid',{},true]) {
    assert.equal(formatKES(invalid),'—'); assert.equal(compactKes(invalid),'—');
  }
  for (const [input, expected] of [[1200,'KES 1.2K'],[25000,'KES 25K'],[1500000,'KES 1.5M']]) assert.equal(compactKes(input),expected);
  const { ProfileCard } = await server.ssrLoadModule('/src/features/portal/ProfileCard.tsx');
  const { BillsList } = await server.ssrLoadModule('/src/features/portal/BillsList.tsx');
  const profile = renderToStaticMarkup(React.createElement(ProfileCard,{profile:{customer_name:'Customer',customer_id:'C1',customer_status:'active',balance:'25450.75'}}));
  assert.ok(profile.includes('KES 25,450.75'));
  const bills = renderToStaticMarkup(React.createElement(BillsList,{bills:[{id:1,total_amount:'2000',remaining_amount:'1250.50',payment_status:'partial'}]}));
  assert.ok(bills.includes('KES 2,000') && bills.includes('KES 1,250.50'));
  console.log('PASS: shared KES aliases, decimals, negative/zero/missing values, compact axes, portal balance and invoices.');
} finally { await server.close(); }

process.exit(0);
