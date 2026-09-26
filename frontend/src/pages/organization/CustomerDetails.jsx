import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { getCustomer } from "../../api/customer";

export default function CustomerDetails() {
  const { customerId } = useParams();
  const navigate = useNavigate();

  const [customer, setCustomer] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;

    async function loadCustomer() {
      try {
        setLoading(true);
        setError("");

        const response = await getCustomer(customerId);

        if (!cancelled) {
          setCustomer(response.data.customer);
        }
      } catch (error) {
        if (!cancelled) {
          setError(
            error.response?.data?.message ||
              error.message ||
              "Unable to load customer."
          );
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    loadCustomer();

    return () => {
      cancelled = true;
    };
  }, [customerId]);

  if (loading) {
    return (
      <div className="min-h-full bg-gray-50 p-6">
        <div className="rounded-xl border bg-white p-8 text-center text-gray-500">
          Loading customer...
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-full bg-gray-50 p-6">
        <button
          type="button"
          onClick={() => navigate("/isp/customers")}
          className="mb-4 text-sm font-medium text-slate-600 hover:text-slate-900"
        >
          ← Back to Customers
        </button>

        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {error}
        </div>
      </div>
    );
  }

  if (!customer) {
    return null;
  }

  return (
    <div className="min-h-full bg-gray-50 p-6">

      {/* Header */}
      <div className="mb-6">

        <button
          type="button"
          onClick={() => navigate("/isp/customers")}
          className="mb-3 text-sm font-medium text-slate-600 hover:text-slate-900"
        >
          ← Back to Customers
        </button>

        <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">

          <div>
            <h1 className="text-2xl font-semibold text-gray-900">
              {customer.full_name}
            </h1>

            <p className="mt-1 text-sm text-gray-500">
              {customer.customer_code}
            </p>
          </div>

          <span
            className={
              customer.status === "active"
                ? "w-fit rounded-full bg-green-100 px-3 py-1 text-xs font-medium text-green-700"
                : "w-fit rounded-full bg-gray-100 px-3 py-1 text-xs font-medium text-gray-600"
            }
          >
            {customer.status}
          </span>

        </div>
      </div>

      {/* Information */}
      <div className="grid gap-6 lg:grid-cols-2">

        {/* Contact Information */}
        <div className="rounded-xl border bg-white p-6">

          <h2 className="mb-5 text-lg font-semibold text-gray-900">
            Contact Information
          </h2>

          <div className="space-y-5">

            <div>
              <p className="text-xs font-medium uppercase tracking-wide text-gray-500">
                Full Name
              </p>

              <p className="mt-1 text-sm text-gray-900">
                {customer.full_name}
              </p>
            </div>

            <div>
              <p className="text-xs font-medium uppercase tracking-wide text-gray-500">
                Phone
              </p>

              <p className="mt-1 text-sm text-gray-900">
                {customer.phone}
              </p>
            </div>

            <div>
              <p className="text-xs font-medium uppercase tracking-wide text-gray-500">
                Email
              </p>

              <p className="mt-1 text-sm text-gray-900">
                {customer.email || "—"}
              </p>
            </div>

            <div>
              <p className="text-xs font-medium uppercase tracking-wide text-gray-500">
                Address
              </p>

              <p className="mt-1 text-sm text-gray-900">
                {customer.address || "—"}
              </p>
            </div>

          </div>
        </div>

        {/* Account Information */}
        <div className="rounded-xl border bg-white p-6">

          <h2 className="mb-5 text-lg font-semibold text-gray-900">
            Account Information
          </h2>

          <div className="space-y-5">

            <div>
              <p className="text-xs font-medium uppercase tracking-wide text-gray-500">
                Customer Code
              </p>

              <p className="mt-1 text-sm text-gray-900">
                {customer.customer_code}
              </p>
            </div>

            <div>
              <p className="text-xs font-medium uppercase tracking-wide text-gray-500">
                Organization
              </p>

              <p className="mt-1 text-sm text-gray-900">
                Tendazi Networks
              </p>
            </div>

            <div>
              <p className="text-xs font-medium uppercase tracking-wide text-gray-500">
                Status
              </p>

              <p className="mt-1 text-sm capitalize text-gray-900">
                {customer.status}
              </p>
            </div>

            <div>
              <p className="text-xs font-medium uppercase tracking-wide text-gray-500">
                Created
              </p>

              <p className="mt-1 text-sm text-gray-900">
                {customer.created_at
                  ? new Date(
                      customer.created_at
                    ).toLocaleString()
                  : "—"}
              </p>
            </div>

            <div>
              <p className="text-xs font-medium uppercase tracking-wide text-gray-500">
                Last Updated
              </p>

              <p className="mt-1 text-sm text-gray-900">
                {customer.updated_at
                  ? new Date(
                      customer.updated_at
                    ).toLocaleString()
                  : "—"}
              </p>
            </div>

          </div>
        </div>

        {/* Notes */}
        <div className="rounded-xl border bg-white p-6 lg:col-span-2">

          <h2 className="mb-4 text-lg font-semibold text-gray-900">
            Notes
          </h2>

          <p className="whitespace-pre-wrap text-sm leading-6 text-gray-700">
            {customer.notes || "No notes recorded."}
          </p>

        </div>

      </div>

      {/* Actions */}
      <div className="mt-6 flex justify-end gap-3">

        <button
          type="button"
          onClick={() =>
            navigate(
              `/isp/customers/${customer.id}/edit`
            )
          }
          className="rounded-lg bg-slate-900 px-5 py-2.5 text-sm font-medium text-white transition hover:bg-slate-800"
        >
          Edit Customer
        </button>

      </div>

    </div>
  );
}