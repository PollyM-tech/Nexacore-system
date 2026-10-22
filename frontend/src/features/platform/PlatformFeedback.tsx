import { Alert, Button } from "flowbite-react";
import { Link, useLocation } from "react-router-dom";
import { apiError } from "@/shared/utils/apiError";
export const httpStatus=(error:unknown)=>(error as {response?:{status?:number}})?.response?.status;
export function platformError(error:unknown) {
 const status=httpStatus(error);
 if(status===401)return "Your session has expired. Sign in again.";
 if(status===403)return "Access denied. Platform Administration requires platform administrator authorization.";
 if(status===404)return "This platform resource was not found.";
 if(status===400)return apiError(error,"Check the submitted fields.");
 return "Unable to load or save platform data. Check your connection and retry.";
}
export function PlatformError({error,retry}:{error:unknown;retry?:()=>void}) {
 const location=useLocation();
 return <div role="alert" className="space-y-3"><Alert color="failure">{platformError(error)}</Alert>{httpStatus(error)===401?<Link to="/admin/login" state={{returnTo:location.pathname+location.search}} className="underline">Sign in</Link>:retry?<Button color="light" onClick={retry}>Retry</Button>:null}</div>;
}
