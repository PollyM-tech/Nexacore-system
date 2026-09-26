import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";

export default function Login() {
  const navigate = useNavigate();
  const { login } = useAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(event) {
    event.preventDefault();

    setError("");
    setLoading(true);

    try {
      console.log("Attempting Lintech login...");

      const user = await login(
        email,
        password
      );

      console.log("Authenticated user:", user);
      console.log("User role:", user.role);

      if (user.role === "super_admin") {
        console.log("Redirecting to /platform");
        navigate("/platform", { replace: true });

        return;
      }

      if (user.role === "organization_admin") {
        console.log("Redirecting to /isp");
        navigate("/isp", { replace: true });

        return;
      }

      setError(
        "Your account does not have an assigned application role."
      );

    } catch (err) {
      console.error(
        "Lintech login failed:",
        err
      );

      const message =
        err.response?.data?.message ||
        "Unable to sign in. Please check your credentials.";

      setError(message);

    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-950 px-4">

      <div className="w-full max-w-md">

        <div className="mb-8 text-center">

          <h1 className="text-3xl font-bold tracking-wide text-white">
            LINTECH
          </h1>

          <p className="mt-2 text-sm text-slate-400">
            ISP Billing & Network Management Platform
          </p>

        </div>


        <div className="rounded-2xl bg-white p-8 shadow-2xl">

          <div className="mb-6">

            <h2 className="text-2xl font-semibold text-slate-900">
              Sign in
            </h2>

            <p className="mt-1 text-sm text-slate-500">
              Access your Lintech account
            </p>

          </div>


          {error && (
            <div className="mb-5 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              {error}
            </div>
          )}


          <form
            onSubmit={handleSubmit}
            className="space-y-5"
          >

            <div>

              <label
                htmlFor="email"
                className="mb-2 block text-sm font-medium text-slate-700"
              >
                Email
              </label>

              <input
                id="email"
                type="email"
                value={email}
                onChange={(event) =>
                  setEmail(event.target.value)
                }
                required
                autoComplete="email"
                placeholder="you@example.com"
                className="w-full rounded-lg border border-slate-300 px-4 py-3 outline-none focus:border-slate-900 focus:ring-2 focus:ring-slate-200"
              />

            </div>


            <div>

              <label
                htmlFor="password"
                className="mb-2 block text-sm font-medium text-slate-700"
              >
                Password
              </label>

              <input
                id="password"
                type="password"
                value={password}
                onChange={(event) =>
                  setPassword(event.target.value)
                }
                required
                autoComplete="current-password"
                placeholder="Enter your password"
                className="w-full rounded-lg border border-slate-300 px-4 py-3 outline-none focus:border-slate-900 focus:ring-2 focus:ring-slate-200"
              />

            </div>


            <button
              type="submit"
              disabled={loading}
              className="w-full rounded-lg bg-slate-900 px-4 py-3 font-medium text-white hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {loading
                ? "Signing in..."
                : "Sign in"}
            </button>

          </form>

        </div>


        <p className="mt-6 text-center text-xs text-slate-500">
          Lintech Network Management Platform
        </p>

      </div>

    </div>
  );
}