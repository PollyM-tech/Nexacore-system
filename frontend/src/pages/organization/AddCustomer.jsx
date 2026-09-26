import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { createCustomer } from "../../api/customer";

export default function AddCustomer() {
  const navigate = useNavigate();

  const [form, setForm] = useState({
    full_name: "",
    phone: "",
    email: "",
    address: "",
    notes: "",
  });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  function handleChange(event) {
    const { name, value } = event.target;

    setForm((current) => ({
      ...current,
      [name]: value,
    }));
  }

  async function handleSubmit(event) {
    event.preventDefault();

    setError("");
    setSuccess("");

    if (!form.full_name.trim()) {
      setError("Full name is required.");
      return;
    }

    if (!form.phone.trim()) {
      setError("Phone number is required.");
      return;
    }

    try {
      setLoading(true);

      await createCustomer({
        full_name: form.full_name.trim(),
        phone: form.phone.trim(),
        email: form.email.trim() || null,
        address: form.address.trim() || null,
        notes: form.notes.trim() || null,
      });

      setSuccess("Customer created successfully.");

      setTimeout(() => {
        navigate("/isp/customers");
      }, 700);
    } catch (error) {
      setError(
        error.response?.data?.message ||
          error.message ||
          "Unable to create customer."
      );
    } finally {
      setLoading(false);
    }
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

        <h1 className="text-2xl font-semibold text-gray-900">
          Add Customer
        </h1>

        <p className="mt-1 text-sm text-gray-500">
          Create a new subscriber account.
        </p>
      </div>

      {/* Form */}
      <div className="max-w-3xl rounded-xl border bg-white p-6 shadow-sm">

        {error && (
          <div className="mb-5 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
            {error}
          </div>
        )}

        {success && (
          <div className="mb-5 rounded-lg border border-green-200 bg-green-50 p-4 text-sm text-green-700">
            {success}
          </div>
        )}

        <form
          onSubmit={handleSubmit}
          className="space-y-5"
        >

          {/* Full Name */}
          <div>
            <label
              htmlFor="full_name"
              className="mb-2 block text-sm font-medium text-gray-700"
            >
              Full Name
              <span className="text-red-500"> *</span>
            </label>

            <input
              id="full_name"
              name="full_name"
              type="text"
              value={form.full_name}
              onChange={handleChange}
              placeholder="e.g. John Kamau"
              disabled={loading}
              className="w-full rounded-lg border border-gray-300 px-4 py-2.5 text-sm outline-none transition focus:border-slate-500 focus:ring-2 focus:ring-slate-200 disabled:bg-gray-100"
            />
          </div>

          {/* Phone */}
          <div>
            <label
              htmlFor="phone"
              className="mb-2 block text-sm font-medium text-gray-700"
            >
              Phone Number
              <span className="text-red-500"> *</span>
            </label>

            <input
              id="phone"
              name="phone"
              type="tel"
              value={form.phone}
              onChange={handleChange}
              placeholder="e.g. 0712345678"
              disabled={loading}
              className="w-full rounded-lg border border-gray-300 px-4 py-2.5 text-sm outline-none transition focus:border-slate-500 focus:ring-2 focus:ring-slate-200 disabled:bg-gray-100"
            />

            <p className="mt-1 text-xs text-gray-500">
              Kenyan numbers can be entered as 07XXXXXXXX or
              +254XXXXXXXXX.
            </p>
          </div>

          {/* Email */}
          <div>
            <label
              htmlFor="email"
              className="mb-2 block text-sm font-medium text-gray-700"
            >
              Email
            </label>

            <input
              id="email"
              name="email"
              type="email"
              value={form.email}
              onChange={handleChange}
              placeholder="customer@example.com"
              disabled={loading}
              className="w-full rounded-lg border border-gray-300 px-4 py-2.5 text-sm outline-none transition focus:border-slate-500 focus:ring-2 focus:ring-slate-200 disabled:bg-gray-100"
            />
          </div>

          {/* Address */}
          <div>
            <label
              htmlFor="address"
              className="mb-2 block text-sm font-medium text-gray-700"
            >
              Address
            </label>

            <input
              id="address"
              name="address"
              type="text"
              value={form.address}
              onChange={handleChange}
              placeholder="e.g. Juja, Kiambu"
              disabled={loading}
              className="w-full rounded-lg border border-gray-300 px-4 py-2.5 text-sm outline-none transition focus:border-slate-500 focus:ring-2 focus:ring-slate-200 disabled:bg-gray-100"
            />
          </div>

          {/* Notes */}
          <div>
            <label
              htmlFor="notes"
              className="mb-2 block text-sm font-medium text-gray-700"
            >
              Notes
            </label>

            <textarea
              id="notes"
              name="notes"
              rows={4}
              value={form.notes}
              onChange={handleChange}
              placeholder="Additional customer information..."
              disabled={loading}
              className="w-full resize-none rounded-lg border border-gray-300 px-4 py-2.5 text-sm outline-none transition focus:border-slate-500 focus:ring-2 focus:ring-slate-200 disabled:bg-gray-100"
            />
          </div>

          {/* Actions */}
          <div className="flex items-center justify-end gap-3 border-t pt-5">

            <button
              type="button"
              onClick={() =>
                navigate("/isp/customers")
              }
              disabled={loading}
              className="rounded-lg border border-gray-300 px-5 py-2.5 text-sm font-medium text-gray-700 transition hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Cancel
            </button>

            <button
              type="submit"
              disabled={loading}
              className="rounded-lg bg-slate-900 px-5 py-2.5 text-sm font-medium text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {loading
                ? "Creating..."
                : "Create Customer"}
            </button>

          </div>

        </form>

      </div>
    </div>
  );
}