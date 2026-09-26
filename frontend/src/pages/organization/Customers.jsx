import { useEffect, useState } from "react";
import { getCustomers } from "../../api/customer";
import { useNavigate } from "react-router-dom";
export default function Customers() {
  const [customers, setCustomers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const navigate = useNavigate();

  useEffect(() => {
    let cancelled = false;

    async function loadCustomers() {
      try {
        setLoading(true);
        setError("");

        const response = await getCustomers();

        if (!cancelled) {
          setCustomers(
            response.data?.customers || []
          );
        }
      } catch (error) {
        if (!cancelled) {
          setError(
            error.response?.data?.message ||
              error.message ||
              "Unable to load customers."
          );
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    loadCustomers();

    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="min-h-full bg-gray-50 p-6">

      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-gray-900">
          Customers
        </h1>

        <p className="mt-1 text-sm text-gray-500">
          Manage your ISP subscribers.
        </p>
      </div>

      {/* Error */}
      {error && (
        <div className="mb-6 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Loading */}
      {loading ? (
        <div className="rounded-xl border bg-white p-8 text-center text-gray-500">
          Loading customers...
        </div>
      ) : (
        <div className="overflow-hidden rounded-xl border bg-white">

          <div className="overflow-x-auto">

            <table className="w-full">

              <thead className="border-b bg-gray-50">
                <tr>
                  <th className="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
                    Customer
                  </th>

                  <th className="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
                    Phone
                  </th>

                  <th className="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
                    Email
                  </th>

                  <th className="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
                    Status
                  </th>
                </tr>
              </thead>

              <tbody className="divide-y">

                {customers.map((customer) => (
                  <tr
                    key={customer.id}
                    onClick={() => navigate(`/isp/customers/${customer.id}`)}
                    className="hover:bg-gray-50"
                  >

                    <td className="px-5 py-4">
                      <div className="font-medium text-gray-900">
                        {customer.full_name}
                      </div>

                      <div className="mt-1 text-xs text-gray-500">
                        {customer.customer_code}
                      </div>
                    </td>

                    <td className="px-5 py-4 text-sm text-gray-700">
                      {customer.phone}
                    </td>

                    <td className="px-5 py-4 text-sm text-gray-700">
                      {customer.email || "—"}
                    </td>

                    <td className="px-5 py-4">

                      <span
                        className={
                          customer.status === "active"
                            ? "rounded-full bg-green-100 px-3 py-1 text-xs font-medium text-green-700"
                            : "rounded-full bg-gray-100 px-3 py-1 text-xs font-medium text-gray-600"
                        }
                      >
                        {customer.status}
                      </span>

                    </td>

                  </tr>
                ))}

              </tbody>

            </table>

          </div>

          {customers.length === 0 && (
            <div className="p-10 text-center text-sm text-gray-500">
              No customers found.
            </div>
          )}

        </div>
      )}

    </div>
  );
}