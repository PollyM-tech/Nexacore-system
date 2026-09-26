import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getCustomers } from "../../api/customer";

const DEFAULT_PAGINATION = {
  page: 1,
  per_page: 20,
  pages: 1,
  total: 0,
  has_next: false,
  has_prev: false,
};

export default function Customers() {
  const navigate = useNavigate();

  const [customers, setCustomers] = useState([]);

  const [pagination, setPagination] = useState(
    DEFAULT_PAGINATION
  );

  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function loadCustomers(
    page = 1,
    currentSearch = "",
    currentStatus = ""
  ) {
    try {
      setLoading(true);
      setError("");

      const response = await getCustomers({
        page,
        perPage: 20,
        search: currentSearch,
        status: currentStatus,
      });

      setCustomers(
        response.data?.customers || []
      );

      setPagination(
        response.data?.pagination ||
          DEFAULT_PAGINATION
      );
    } catch (error) {
      setError(
        error.response?.data?.message ||
          error.message ||
          "Unable to load customers."
      );
    } finally {
      setLoading(false);
    }
  }

  /*
   * Initial customer load.
   *
   * IMPORTANT:
   * Keep the dependency array empty.
   * This prevents the page from repeatedly
   * calling the API and blinking.
   */
  useEffect(() => {
    let isMounted = true;

    async function fetchInitialCustomers() {
      try {
        setLoading(true);
        setError("");

        const response = await getCustomers({
          page: 1,
          perPage: 20,
          search: "",
          status: "",
        });

        if (!isMounted) {
          return;
        }

        setCustomers(
          response.data?.customers || []
        );

        setPagination(
          response.data?.pagination ||
            DEFAULT_PAGINATION
        );
      } catch (error) {
        if (!isMounted) {
          return;
        }

        setError(
          error.response?.data?.message ||
            error.message ||
            "Unable to load customers."
        );
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    }

    fetchInitialCustomers();

    return () => {
      isMounted = false;
    };
  }, []);

  function handleSearchSubmit(event) {
    event.preventDefault();

    const newSearch = searchInput.trim();

    setSearch(newSearch);

    loadCustomers(
      1,
      newSearch,
      status
    );
  }

  function handleStatusChange(event) {
    const newStatus = event.target.value;

    setStatus(newStatus);

    loadCustomers(
      1,
      search,
      newStatus
    );
  }

  function clearFilters() {
    setSearchInput("");
    setSearch("");
    setStatus("");

    loadCustomers(1, "", "");
  }

  function goToPage(page) {
    if (page < 1) {
      return;
    }

    if (
      pagination.pages > 0 &&
      page > pagination.pages
    ) {
      return;
    }

    loadCustomers(
      page,
      search,
      status
    );
  }

  return (
    <div className="min-h-full bg-gray-50 p-6">

      {/* Header */}
      <div className="mb-6 flex flex-col justify-between gap-4 sm:flex-row sm:items-center">

        <div>
          <h1 className="text-2xl font-semibold text-gray-900">
            Customers
          </h1>

          <p className="mt-1 text-sm text-gray-500">
            Manage your ISP subscribers.
          </p>
        </div>

        <button
          type="button"
          onClick={() =>
            navigate("/isp/customers/new")
          }
          className="rounded-lg bg-slate-900 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-slate-800"
        >
          + Add Customer
        </button>

      </div>

      {/* Filters */}
      <div className="mb-5 rounded-xl border bg-white p-4">

        <form
          onSubmit={handleSearchSubmit}
          className="flex flex-col gap-3 lg:flex-row"
        >

          {/* Search */}
          <div className="flex-1">
            <input
              type="text"
              value={searchInput}
              onChange={(event) =>
                setSearchInput(
                  event.target.value
                )
              }
              placeholder="Search by name, phone, email or customer code..."
              className="w-full rounded-lg border border-gray-300 px-4 py-2.5 text-sm outline-none transition focus:border-slate-500 focus:ring-2 focus:ring-slate-200"
            />
          </div>

          {/* Status */}
          <select
            value={status}
            onChange={handleStatusChange}
            className="rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm outline-none focus:border-slate-500 focus:ring-2 focus:ring-slate-200"
          >
            <option value="">
              All Statuses
            </option>

            <option value="active">
              Active
            </option>

            <option value="suspended">
              Suspended
            </option>

            <option value="inactive">
              Inactive
            </option>
          </select>

          {/* Search Button */}
          <button
            type="submit"
            disabled={loading}
            className="rounded-lg bg-slate-900 px-5 py-2.5 text-sm font-medium text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50"
          >
            Search
          </button>

          {/* Clear */}
          {(search || status) && (
            <button
              type="button"
              onClick={clearFilters}
              disabled={loading}
              className="rounded-lg border border-gray-300 px-5 py-2.5 text-sm font-medium text-gray-700 transition hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Clear
            </button>
          )}

        </form>

      </div>

      {/* Error */}
      {error && (
        <div className="mb-5 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Results count */}
      <div className="mb-3 text-sm text-gray-500">
        {pagination.total} customer
        {pagination.total === 1
          ? ""
          : "s"}
      </div>

      {/* Customers Table */}
      <div className="overflow-hidden rounded-xl border bg-white">

        {loading ? (
          <div className="p-10 text-center text-sm text-gray-500">
            Loading customers...
          </div>
        ) : (
          <>
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

                    <th className="px-5 py-3 text-right text-xs font-semibold uppercase tracking-wide text-gray-500">
                      Action
                    </th>

                  </tr>

                </thead>

                <tbody className="divide-y">

                  {customers.map(
                    (customer) => (
                      <tr
                        key={customer.id}
                        onClick={() =>
                          navigate(
                            `/isp/customers/${customer.id}`
                          )
                        }
                        className="cursor-pointer hover:bg-gray-50"
                      >

                        {/* Customer */}
                        <td className="px-5 py-4">

                          <div className="font-medium text-gray-900">
                            {customer.full_name}
                          </div>

                          <div className="mt-1 text-xs text-gray-500">
                            {customer.customer_code}
                          </div>

                        </td>

                        {/* Phone */}
                        <td className="px-5 py-4 text-sm text-gray-700">
                          {customer.phone}
                        </td>

                        {/* Email */}
                        <td className="px-5 py-4 text-sm text-gray-700">
                          {customer.email || "—"}
                        </td>

                        {/* Status */}
                        <td className="px-5 py-4">

                          <span
                            className={
                              customer.status ===
                              "active"
                                ? "rounded-full bg-green-100 px-3 py-1 text-xs font-medium text-green-700"
                                : customer.status ===
                                  "suspended"
                                ? "rounded-full bg-yellow-100 px-3 py-1 text-xs font-medium text-yellow-700"
                                : "rounded-full bg-gray-100 px-3 py-1 text-xs font-medium text-gray-600"
                            }
                          >
                            {customer.status}
                          </span>

                        </td>

                        {/* Action */}
                        <td className="px-5 py-4 text-right">

                          <button
                            type="button"
                            onClick={(event) => {
                              event.stopPropagation();

                              navigate(
                                `/isp/customers/${customer.id}`
                              );
                            }}
                            className="text-sm font-medium text-slate-700 hover:text-slate-900"
                          >
                            View
                          </button>

                        </td>

                      </tr>
                    )
                  )}

                </tbody>

              </table>

            </div>

            {/* Empty State */}
            {customers.length === 0 && (
              <div className="p-10 text-center">

                <p className="text-sm text-gray-500">
                  No customers found.
                </p>

                {(search || status) && (
                  <button
                    type="button"
                    onClick={clearFilters}
                    className="mt-3 text-sm font-medium text-slate-700 hover:text-slate-900"
                  >
                    Clear filters
                  </button>
                )}

              </div>
            )}

            {/* Pagination */}
            {pagination.pages > 1 && (
              <div className="flex items-center justify-between border-t px-5 py-4">

                {/* Previous */}
                <button
                  type="button"
                  disabled={
                    !pagination.has_prev ||
                    loading
                  }
                  onClick={() =>
                    goToPage(
                      pagination.page - 1
                    )
                  }
                  className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 transition hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-40"
                >
                  Previous
                </button>

                {/* Page */}
                <span className="text-sm text-gray-500">
                  Page{" "}
                  {pagination.page} of{" "}
                  {pagination.pages}
                </span>

                {/* Next */}
                <button
                  type="button"
                  disabled={
                    !pagination.has_next ||
                    loading
                  }
                  onClick={() =>
                    goToPage(
                      pagination.page + 1
                    )
                  }
                  className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 transition hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-40"
                >
                  Next
                </button>

              </div>
            )}

          </>
        )}

      </div>

    </div>
  );
}