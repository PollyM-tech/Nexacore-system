import {
  BrowserRouter,
  Navigate,
  Route,
  Routes,
} from "react-router-dom";

import { useAuth } from "./auth/AuthContext";

import Login from "./pages/login";
import PlatformDashboard from "./pages/platform/Dashboard";
import OrganizationDashboard from "./pages/organization/Dashboard";
import Customers from "./pages/organization/Customers";
import AddCustomer from "./pages/organization/AddCustomer";
import CustomerDetails from "./pages/organization/CustomerDetails";
import EditCustomer from "./pages/organization/EditCustomer";

function LoadingScreen() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-100">
      <div className="text-center">
        <div className="mb-3 text-xl font-semibold text-slate-900">
          Lintech
        </div>

        <p className="text-sm text-slate-500">
          Loading...
        </p>
      </div>
    </div>
  );
}


function ProtectedRoute({ children }) {
  const { user, loading } = useAuth();

  if (loading) {
    return <LoadingScreen />;
  }

  if (!user) {
    return (
      <Navigate
        to="/login"
        replace
      />
    );
  }

  return children;
}


function RoleRoute({ role, children }) {
  const { user, loading } = useAuth();

  if (loading) {
    return <LoadingScreen />;
  }

  if (!user || user.role !== role) {
    return (
      <Navigate
        to="/login"
        replace
      />
    );
  }

  return children;
}


export default function App() {
  return (
    <BrowserRouter>

      <Routes>

        {/* Lintech Login */}
        <Route
          path="/login"
          element={<Login />}
        />


        {/* Lintech Platform */}
        <Route
          path="/platform"
          element={
            <ProtectedRoute>
              <RoleRoute role="super_admin">
                <PlatformDashboard />
              </RoleRoute>
            </ProtectedRoute>
          }
        />


        {/* ISP Organization Portal */}
        <Route
          path="/isp"
          element={
            <ProtectedRoute>
              <RoleRoute role="organization_admin">
                <OrganizationDashboard />
              </RoleRoute>
            </ProtectedRoute>
          }
        />
        <Route
  path="/isp/customers"
  element={
    <ProtectedRoute>
      <RoleRoute role="organization_admin">
        <Customers />
      </RoleRoute>
    </ProtectedRoute>
  }
/>

<Route
  path="/isp/customers/new"
  element={
    <ProtectedRoute>
      <RoleRoute role="organization_admin">
        <AddCustomer />
      </RoleRoute>
    </ProtectedRoute>
  }
/>

<Route
  path="/isp/customers/:customerId"
  element={
    <ProtectedRoute>
      <RoleRoute role="organization_admin">
        <CustomerDetails />
      </RoleRoute>
    </ProtectedRoute>
  }
/>

<Route
  path="/isp/customers/:customerId/edit"
  element={
    <ProtectedRoute>
      <RoleRoute role="organization_admin">
        <EditCustomer />
      </RoleRoute>
    </ProtectedRoute>
  }
/>


        {/* Default */}
        <Route
          path="/"
          element={
            <Navigate
              to="/login"
              replace
            />
          }
        />


        {/* Unknown routes */}
        <Route
          path="*"
          element={
            <Navigate
              to="/login"
              replace
            />
          }
        />

      </Routes>

    </BrowserRouter>
  );
}