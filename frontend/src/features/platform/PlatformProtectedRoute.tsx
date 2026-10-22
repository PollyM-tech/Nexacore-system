import { Navigate, Outlet, useLocation, Link } from "react-router-dom";
import { Spinner } from "flowbite-react";
import { usePlatformMe } from "./queries";
import { httpStatus, PlatformError } from "./PlatformFeedback";
export function PlatformProtectedRoute() {
 const q=usePlatformMe();const location=useLocation();
 if(q.isPending || q.isFetching)return <div role="status" className="flex min-h-screen items-center justify-center gap-3"><Spinner />Checking platform authorization…</div>;
 if(q.isError && httpStatus(q.error)===401)return <Navigate to="/admin/login" replace state={{returnTo:location.pathname+location.search}} />;
 if(q.isError)return <main className="mx-auto max-w-xl p-8"><h1 className="mb-4 text-xl font-semibold">Platform Administration</h1><PlatformError error={q.error} retry={httpStatus(q.error)===403?undefined:()=>void q.refetch()} /><Link to="/admin" className="mt-4 inline-block underline">Return to ISP admin</Link></main>;
 if(q.data?.is_platform_admin!==true)return <main role="alert" className="p-8">Access denied. Platform administrator authorization is required.</main>;
 return <Outlet />;
}
