import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  getCustomer,
  updateCustomer,
} from "../../api/customer";

export default function EditCustomer() {
  const { customerId } = useParams();
  const navigate = useNavigate();

  const [form, setForm] = useState({
    full_name: "",
    phone: "",
    email: "",
    address: "",
    notes: "",
  });

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  useEffect(() => {
    let cancelled = false;

    async function loadCustomer() {
      try {
        setLoading(true);
        setError("");

        const response =
          await getCustomer(customerId);

        if (!cancelled) {
          const customer =
            response.data.customer;

          setForm({
            full_name:
              customer.full_name || "",
            phone:
              customer.phone || "",
            email:
              customer.email || "",
            address:
              customer.address || "",
            notes:
              customer.notes || "",
          });
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
      setSaving(true);

      await updateCustomer(
          customerId,
          {
            full_name:
              form.full_name.trim(),
            phone:
              form.phone.trim(),
            email:
              form.email.trim() || null,
            address:
              form.address.trim() || null,
            notes:
              form.notes.trim() || null,
          }
        );

      setSuccess(
        "Customer updated successfully."
      );

      setTimeout(() => {
        navigate(
          `/isp/customers/${customerId}`
        );
      }, 700);
    } catch (error) {
      setError(
        error.response?.data?.message ||
          error.message ||
          "Unable to update customer."
      );
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <div className="min-h-full bg-gray-50 p-6">
        <div className="rounded-xl border bg-white p-8 text-center text-gray-500">
          Loading customer...
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-full bg-gray-50 p-6">

      {/* Header */}
      <div className="mb-6">

        <button
          type="button"
          onClick={() =>
            navigate(
              `/isp/customers/${customerId}`
            )
          }
          className="mb-3 text-sm font-medium text-slate-600 hover:text-slate-900"
        >
          ← Back to Customer
        </button>

        <h1 className="text-2xl font-semibold text-gray-900">
          Edit Customer
        </h1>

        <p className="mt-1 text-sm text-gray-500">
          Update the customer's information.
        </p>

      </div>

      {/* Error */}
      {error && (
        <div className="mb-5 max-w-3xl rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Success */}
      {success && (
        <div className="mb-5 max-w-3xl rounded-lg border border-green-200 bg-green-50 p-4 text-sm text-green-700">
          {success}
        </div>
      )}

      {/* Form */}
      <div className="max-w-3xl rounded-xl border bg-white p-6 shadow-sm">

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
              <span className="text-red-500">
                {" "}
                *
              </span>
            </label>

            <input
              id="full_name"
              name="full_name"
              type="text"
              value={form.full_name}
              onChange={handleChange}
              disabled={saving}
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
              <span className="text-red-500">
                {" "}
                *
              </span>
            </label>

            <input
              id="phone"
              name="phone"
              type="tel"
              value={form.phone}
              onChange={handleChange}
              disabled={saving}
              className="w-full rounded-lg border border-gray-300 px-4 py-2.5 text-sm outline-none transition focus:border-slate-500 focus:ring-2 focus:ring-slate-200 disabled:bg-gray-100"
            />

            <p className="mt-1 text-xs text-gray-500">
              Kenyan numbers can be entered as
              07XXXXXXXX or +254XXXXXXXXX.
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
              disabled={saving}
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
              disabled={saving}
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
              disabled={saving}
              className="w-full resize-none rounded-lg border border-gray-300 px-4 py-2.5 text-sm outline-none transition focus:border-slate-500 focus:ring-2 focus:ring-slate-200 disabled:bg-gray-100"
            />
          </div>

          {/* Actions */}
          <div className="flex items-center justify-end gap-3 border-t pt-5">

            <button
              type="button"
              onClick={() =>
                navigate(
                  `/isp/customers/${customerId}`
                )
              }
              disabled={saving}
              className="rounded-lg border border-gray-300 px-5 py-2.5 text-sm font-medium text-gray-700 transition hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Cancel
            </button>

            <button
              type="submit"
              disabled={saving}
              className="rounded-lg bg-slate-900 px-5 py-2.5 text-sm font-medium text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {saving
                ? "Saving..."
                : "Save Changes"}
            </button>

          </div>

        </form>

      </div>
    </div>
  );
}