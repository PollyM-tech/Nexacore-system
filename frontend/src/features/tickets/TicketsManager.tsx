import { Button, Select } from "flowbite-react";
import { useState } from "react";
import { ticketColumns } from "@/features/tickets/ticketColumns";
import { TicketDetail } from "@/features/tickets/TicketDetail";
import { TicketForm } from "@/features/tickets/TicketForm";
import { API } from "@/shared/api/endpoints";
import type { Column } from "@/shared/components/data/DataTable";
import { AdminResourceList as ResourceList } from "@/features/admin/AdminResourceList";
import { Icon } from "@/shared/components/icons/Icon";
import { IconButton, RowActions } from "@/shared/components/ui/RowActions";
import { useAdminCrud as useCrud } from "@/features/admin/useAdminCrud";
import { apiError } from "@/shared/utils/apiError";
import type { Ticket } from "@/shared/types/api";

export function TicketsManager() {
  const [createOpen, setCreateOpen] = useState(false);
  const [status, setStatus] = useState("");
  const [priority, setPriority] = useState("");
  const [detailId, setDetailId] = useState<number | null>(null);
  const { create } = useCrud("tickets", API.tickets);

  const columns: Column<Ticket>[] = [
    ...ticketColumns,
    {
      key: "actions", header: "Open ticket", align: "right",
      render: (t) => (
        <RowActions>
          <IconButton icon="eye" label="View thread" onClick={() => setDetailId(t.id)} />

        </RowActions>
      ),
    },
  ];

  return (
    <>
      <ResourceList<Ticket>
        queryKey="tickets" url={API.tickets} columns={columns} rowKey={(r) => r.id}
        searchPlaceholder="Search tickets…" emptyTitle="No support tickets"
        emptyDescription="Customer issues and admin replies show up here." emptyIcon="ticket"
        params={{status, priority}}
        filters={<><Select aria-label="Ticket status filter" value={status} onChange={e=>setStatus(e.target.value)}><option value="">All statuses</option>{["open","in_progress","resolved","closed"].map(s=><option key={s} value={s}>{s.replace("_"," ")}</option>)}</Select><Select aria-label="Ticket priority filter" value={priority} onChange={e=>setPriority(e.target.value)}><option value="">All priorities</option>{["low","medium","high","urgent"].map(s=><option key={s}>{s}</option>)}</Select></>}
        toolbarAction={
          <Button color="primary" onClick={() => setCreateOpen(true)}>
            <Icon name="plus" className="mr-2 h-4 w-4" /> Add ticket
          </Button>
        }
      />
      <TicketForm open={createOpen} onClose={() => setCreateOpen(false)}
        onSubmit={(body) => create.mutate(body, { onSuccess: () => setCreateOpen(false) })}
        submitting={create.isPending}
        error={create.isError ? apiError(create.error) : null} />
      <TicketDetail ticketId={detailId} onClose={() => setDetailId(null)} />
    </>
  );
}
