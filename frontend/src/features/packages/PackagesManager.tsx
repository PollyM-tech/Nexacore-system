import { Button, Select, TextInput } from "flowbite-react";
import { useEffect, useState } from "react";
import { packageColumns, knownCount } from "./packageColumns";
import { PackageForm } from "./PackageForm";
import { usePackages, usePackageMutations } from "./usePackages";
import { DataTable, type Column } from "@/shared/components/data/DataTable";
import { TablePagination } from "@/shared/components/data/TablePagination";
import { ListPageSection } from "@/shared/components/data/ListPageSection";
import { ErrorAlert } from "@/shared/components/feedback/ErrorAlert";
import { FormModal } from "@/shared/components/ui/FormModal";
import { apiError } from "@/shared/utils/apiError";
import type { Package } from "@/shared/types/api";

type Action = { kind: "delete" | "status"; package: Package };
export function PackagesManager() {
  const [search, setSearch] = useState("");
  const [debounced, setDebounced] = useState("");
  const [filter, setFilter] = useState("");
  const [page, setPage] = useState(1);
  const [form, setForm] = useState<Package | "new" | null>(null);
  const [action, setAction] = useState<Action | null>(null);
  useEffect(() => { const timer = setTimeout(() => { setDebounced(search.trim()); setPage(1); }, 300); return () => clearTimeout(timer); }, [search]);
  const query = usePackages(debounced, filter, page);
  useEffect(() => {
    if (query.data) {
      const lastPage = Math.max(1, Math.ceil(query.data.count / 10));
      if (page > lastPage) setPage(lastPage);
    }
  }, [query.data, page]);
  const { save, remove, status } = usePackageMutations();
  const pending = save.isPending || remove.isPending || status.isPending;
  const closeForm = () => { if (!save.isPending) setForm(null); };
  const start = (p: Package | "new") => { save.reset(); setForm(p); };
  const ask = (next: Action) => { remove.reset(); status.reset(); setAction(next); };
  const confirm = (e: React.FormEvent) => {
    e.preventDefault();
    if (!action) return;
    const p = action.package;
    if (action.kind === "delete") {
      if (!knownCount(p.customer_count) || p.customer_count > 0) return;
      remove.mutate(p.id, { onSuccess: () => { setAction(null); if (query.data?.results.length === 1 && page > 1) setPage(page - 1); } });
    } else status.mutate({ id: p.id, active: !p.is_active }, { onSuccess: () => setAction(null) });
  };
  const button = "rounded-lg border border-slate-200 px-2.5 py-1.5 text-xs font-medium focus-visible:outline-2 focus-visible:outline-brand-500 disabled:opacity-40 dark:border-slate-700";
  const columns: Column<Package>[] = [...packageColumns, { key: "actions", header: "Actions", render: (p) => {
    const canDelete = knownCount(p.customer_count) && p.customer_count === 0;
    return <div className="flex flex-wrap gap-2 min-w-52">
      <button className={button} disabled={pending} aria-label={`Edit ${p.name}`} onClick={() => start(p)}>Edit</button>
      <button className={button} disabled={pending} aria-label={`${p.is_active ? "Deactivate" : "Activate"} ${p.name}`} onClick={() => ask({ kind: "status", package: p })}>{p.is_active ? "Deactivate" : "Activate"}</button>
      <span title={canDelete ? undefined : "Assigned packages cannot be deleted. Deactivate instead. Usage must be available."}>
        <button className={`${button} text-rose-600`} disabled={pending || !canDelete} aria-label={`Delete ${p.name}`} onClick={() => ask({ kind: "delete", package: p })}>Delete</button>
      </span>
      {!canDelete && <span className="w-full text-xs text-slate-500">{knownCount(p.customer_count) ? "In use · deactivate instead of deleting." : "Usage unavailable · deletion disabled."}</span>}
    </div>;
  } }];
  return <div className="space-y-4">
    <div className="flex flex-wrap items-end gap-3">
      <div className="min-w-0 flex-1"><label htmlFor="package-search" className="mb-1 block text-sm">Search packages</label><TextInput id="package-search" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Name, speed or description" /></div>
      <div><label htmlFor="package-filter" className="mb-1 block text-sm">Status</label><Select id="package-filter" value={filter} onChange={(e) => { setFilter(e.target.value); setPage(1); }}><option value="">All statuses</option><option value="true">Active</option><option value="false">Inactive</option></Select></div>
      <Button color="primary" disabled={pending} onClick={() => start("new")}>Add package</Button>
    </div>
    <p className="text-sm text-slate-500">Billing cycles are monthly, quarterly or yearly. Usage counts include currently assigned customers.</p>
    {query.isError && <Button color="light" onClick={() => void query.refetch()}>Retry packages</Button>}
    <ListPageSection isLoading={query.isLoading} isError={query.isError} errorMessage={apiError(query.error, "Could not load packages.")} isEmpty={!query.data?.results.length} emptyTitle="No packages found" emptyDescription="Try another search or status, or create a package." emptyIcon="package">
      <DataTable columns={columns} rows={query.data?.results ?? []} rowKey={(p) => p.id} />
    </ListPageSection>
    {query.data && !query.isError && <TablePagination page={page} totalPages={Math.max(1, Math.ceil(query.data.count / 10))} onPage={setPage} rangeLabel={`${query.data.count} packages matching filters`} />}
    {remove.isError && !action && <ErrorAlert message={apiError(remove.error)} />}
    {form !== null && <PackageForm open onClose={closeForm} initial={form === "new" ? null : form} submitting={save.isPending} error={save.isError ? apiError(save.error) : null} onSubmit={(body) => save.mutate({ id: form === "new" ? undefined : form.id, body }, { onSuccess: () => setForm(null) })} />}
    <FormModal open={action !== null} onClose={() => { if (!pending) setAction(null); }} title={action?.kind === "delete" ? "Delete unused package" : `${action?.package.is_active ? "Deactivate" : "Activate"} package`} submitLabel={action?.kind === "delete" ? "Delete package" : action?.package.is_active ? "Deactivate package" : "Activate package"} onSubmit={confirm} submitting={remove.isPending || status.isPending} error={remove.isError ? apiError(remove.error) : status.isError ? apiError(status.error) : null}>
      <p className="sm:col-span-2 break-words">{action?.kind === "delete" ? `Permanently delete “${action.package.name}”? This cannot be undone.` : `${action?.package.is_active ? "Deactivate" : "Activate"} “${action?.package.name ?? ""}”? Existing customers remain assigned. This does not disconnect active subscribers.`}</p>
    </FormModal>
  </div>;
}
