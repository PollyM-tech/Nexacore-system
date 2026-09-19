# Nexacore-system
Step by step guide for frontend team

Nexacore WiFi Billing System — Frontend Setup Guide
This guide is for the frontend developer working on the Nexacore WiFi Billing System.

The backend is built with Flask + PostgreSQL + JWT authentication.
The frontend should be built with React + Vite + Tailwind CSS.

1. Project Structure
NEXACORE
│
├── Platform
│   ├── Organizations / ISPs
│   ├── Platform administrators
│   └── SaaS subscriptions
│
├── ISP Customers
│   ├── Customers
│   ├── Customer accounts
│   ├── Tickets
│   └── Communication
│
├── Internet Access
│   ├── PPPoE
│   ├── Hotspot
│   ├── Static IP
│   └── DHCP
│
├── Network
│   ├── Sites
│   ├── MikroTik routers
│   ├── RADIUS
│   ├── CPE
│   ├── OLT
│   └── Router monitoring
│
├── Service Management
│   ├── Plans
│   ├── Subscriptions
│   ├── FUP
│   ├── Burst
│   └── Expiry / suspension
│
├── Finance
│   ├── Payments
│   ├── M-PESA
│   ├── Invoices
│   ├── Expenditure
│   └── Reports
│
└── Monitoring / Analytics
    ├── Online users
    ├── Traffic
    ├── Top downloaders
    ├── Router health
    ├── Server health
    └── Revenue analytics

billing-system/frontend/
2. Backend Development URL
The Flask API runs locally on:

http://127.0.0.1:5000
API base URL:

http://127.0.0.1:5000/api/v1
Do not call PostgreSQL, MikroTik, FreeRADIUS, or M-PESA directly from React. All frontend communication goes through Flask.

3. Start the React Frontend
cd ~/projects/billing-system/frontend
npm install
npm run dev
The frontend normally runs at:

http://localhost:5173
4. Create the Frontend Environment File
Create:

frontend/.env
Add:

VITE_API_BASE_URL=http://127.0.0.1:5000/api/v1
Do not hard-code the API URL throughout the app.

5. Install Frontend Packages
npm install axios react-router-dom lucide-react
Packages:

axios             API requests
react-router-dom  Routing and protected pages
lucide-react      Icons
6. Authentication API
The backend currently provides:

POST /api/v1/auth/register
POST /api/v1/auth/login
GET  /api/v1/auth/me
POST /api/v1/auth/refresh
Important:

/auth/register is for creating the first administrator during setup.

The normal frontend login flow uses /auth/login.

Protected endpoints require a JWT access token.

Use the JWT in the HTTP Authorization header.

7. First Administrator Registration
Endpoint:

POST /api/v1/auth/register
Request body:

{
  "full_name": "Example Admin",
  "email": "admin@example.com",
  "password": "StrongPassword123"
}
Example successful response:

{
  "status": "success",
  "message": "Administrator registered successfully.",
  "data": {
    "user": {
      "id": 1,
      "full_name": "Example Admin",
      "email": "admin@example.com",
      "role": "super_admin"
    }
  }
}
The production frontend should not expose public administrator registration.

8. Login
Endpoint:

POST /api/v1/auth/login
Request:

{
  "email": "admin@example.com",
  "password": "StrongPassword123"
}
Example response:

{
  "status": "success",
  "message": "Login successful.",
  "data": {
    "access_token": "JWT_ACCESS_TOKEN",
    "refresh_token": "JWT_REFRESH_TOKEN",
    "user": {
      "id": 1,
      "full_name": "Example Admin",
      "email": "admin@example.com",
      "role": "super_admin"
    }
  }
}
The frontend should store:

access_token
refresh_token
user
9. Token Usage
For protected API requests:

Authorization: Bearer ACCESS_TOKEN
Example:

GET /api/v1/auth/me
10. Current Logged-In User
Endpoint:

GET /api/v1/auth/me
This endpoint is protected.

Example response:

{
  "status": "success",
  "data": {
    "user": {
      "id": 1,
      "full_name": "Example Admin",
      "email": "admin@example.com",
      "role": "super_admin",
      "is_active": true
    }
  }
}
Use this endpoint when restoring a session or checking whether the access token is still valid.

11. Refreshing the Access Token
Endpoint:

POST /api/v1/auth/refresh
Send the refresh token as the Bearer token:

Authorization: Bearer REFRESH_TOKEN
Example response:

{
  "status": "success",
  "data": {
    "access_token": "NEW_ACCESS_TOKEN"
  }
}
Replace the old access token with the new one.

12. Recommended API Client
Create:

src/api/api.js
Example:

import axios from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

api.interceptors.request.use((config) => {
  const accessToken = localStorage.getItem("access_token");

  if (accessToken) {
    config.headers.Authorization = `Bearer ${accessToken}`;
  }

  return config;
});

export default api;
13. Login Service
Create:

src/services/authService.js
Example:

import api from "../api/api";

export async function login(email, password) {
  const response = await api.post("/auth/login", {
    email,
    password,
  });

  return response.data;
}
14. Login Page Flow
Login form
   ↓
POST /auth/login
   ↓
Receive access_token + refresh_token
   ↓
Save tokens
   ↓
Save user
   ↓
Redirect to /dashboard
Example:

const handleLogin = async (event) => {
  event.preventDefault();

  try {
    const result = await login(email, password);

    localStorage.setItem(
      "access_token",
      result.data.access_token
    );

    localStorage.setItem(
      "refresh_token",
      result.data.refresh_token
    );

    localStorage.setItem(
      "user",
      JSON.stringify(result.data.user)
    );

    navigate("/dashboard");
  } catch (error) {
    console.error(error);
  }
};
15. Recommended Frontend Structure
src/
├── api/
│   └── api.js
├── components/
├── context/
│   └── AuthContext.jsx
├── layouts/
├── pages/
│   ├── Login.jsx
│   └── Dashboard.jsx
├── routes/
│   └── ProtectedRoute.jsx
├── services/
│   └── authService.js
└── App.jsx
16. Authentication State
The frontend should maintain:

user
accessToken
isAuthenticated
loading
login()
logout()
Startup flow:

Check access token
       ↓
GET /auth/me
       ↓
Valid?
 ├── Yes → restore user
 └── No  → try refresh token / logout
17. Protected Routes
Example:

import { Navigate } from "react-router-dom";

function ProtectedRoute({ children }) {
  const token = localStorage.getItem("access_token");

  if (!token) {
    return <Navigate to="/login" replace />;
  }

  return children;
}

export default ProtectedRoute;
Then:

<Route
  path="/dashboard"
  element={
    <ProtectedRoute>
      <Dashboard />
    </ProtectedRoute>
  }
/>
Later this should rely on AuthContext state rather than only local storage.

18. Logout
For the current development version:

function logout() {
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
  localStorage.removeItem("user");

  window.location.href = "/login";
}
A server-side token revocation endpoint can be added later.

19. Initial Frontend Pages
The frontend team can begin with:

/login

/dashboard
/dashboard/customers
/dashboard/plans
/dashboard/pppoe
/dashboard/hotspot
/dashboard/payments
/dashboard/sessions
/dashboard/routers
/dashboard/sites
/dashboard/reports
/dashboard/settings
Only authentication APIs are complete at this stage. Other pages can initially contain placeholders.

20. Dashboard Navigation
Recommended navigation:

Dashboard
Customers
PPPoE
Hotspot
Packages
Payments
Sessions
Routers
Sites
Reports
Settings
21. Suggested Dashboard Layout
┌──────────────────────────────────────┐
│ Top Navigation                       │
├────────────┬─────────────────────────┤
│ Sidebar    │ Main Content            │
│            │                         │
│ Dashboard  │                         │
│ Customers  │                         │
│ PPPoE      │                         │
│ Hotspot    │                         │
│ Packages   │                         │
│ Payments   │                         │
│ Sessions   │                         │
│ Routers    │                         │
│ Reports    │                         │
│ Settings   │                         │
└────────────┴─────────────────────────┘
22. Role Handling
Current role:

super_admin
More roles may be added later:

admin
support
finance
technician
agent
Use:

user.role
for UI decisions. The backend remains responsible for actual authorization.

23. Error Handling
Backend errors may look like:

{
  "status": "error",
  "message": "Invalid email or password."
}
Use:

error.response?.data?.message
Example:

try {
  await login(email, password);
} catch (error) {
  const message =
    error.response?.data?.message ||
    "Unable to complete request.";

  setError(message);
}
24. HTTP Status Codes
200  Successful request
201  Resource created
400  Invalid request
401  Authentication failed / invalid token
403  Authenticated but not allowed
404  Resource not found
409  Conflict / resource already exists
500  Internal server error
503  Service unavailable
25. Handling 401 Responses
Future flow:

Request fails with 401
        ↓
Use refresh_token
        ↓
POST /auth/refresh
        ↓
Receive new access_token
        ↓
Retry original request
If refresh fails:

Clear tokens
    ↓
Redirect to /login
26. Security Rules
Do not:

Commit .env
Hard-code passwords
Hard-code JWT tokens
Store database credentials in React
Call PostgreSQL directly
Call MikroTik directly
Call M-PESA directly from React
Trust frontend role checks as security
All sensitive operations must go through Flask.

27. Health Endpoints
GET /api/v1/health
GET /api/v1/health/db
Expected database response:

{
  "database": "connected",
  "status": "ok"
}
28. Git Workflow
Recommended frontend branch:

git checkout -b frontend-development
Typical workflow:

git status
git add .
git commit -m "feat: build authentication pages"
git push -u origin frontend-development
Then create a Pull Request into main.

29. Current Frontend Priority
Set VITE_API_BASE_URL.

Install Axios and React Router.

Create reusable Axios client.

Create Login page.

Integrate POST /auth/login.

Save access and refresh tokens.

Create AuthContext.

Integrate GET /auth/me.

Create ProtectedRoute.

Build Dashboard shell.

Create sidebar navigation.

Add Logout.

Add token refresh handling.

Create placeholder pages for future modules.

30. Backend Features Coming Next
Customers
Sites
Routers
Plans
Subscriptions
PPPoE accounts
Hotspot accounts
Payments
M-PESA STK Push
FreeRADIUS
Online sessions
MikroTik management
Reports
31. Development Checklist
[ ] React app starts successfully
[ ] Flask backend is running
[ ] Login page renders
[ ] Invalid login shows an error
[ ] Valid login returns tokens
[ ] Access token is stored
[ ] Refresh token is stored
[ ] /auth/me works
[ ] Dashboard is protected
[ ] Unauthenticated visitor redirects to login
[ ] Logout clears authentication
[ ] API base URL comes from .env
[ ] No backend credentials exist in frontend code
32. Backend Contract for New Features
When a backend feature is ready, the frontend developer should receive:

HTTP method
Endpoint
Authentication requirement
Request body
Query parameters
Example success response
Possible error responses
Example:

Feature:
Create Customer

Method:
POST

Endpoint:
/api/v1/customers

Authentication:
Bearer access token

Body:
{
  "full_name": "John Doe",
  "phone": "2547XXXXXXXX"
}

Success:
201 Created
Current API Summary
BASE URL
http://127.0.0.1:5000/api/v1

AUTH
POST /auth/register
POST /auth/login
GET  /auth/me
POST /auth/refresh

HEALTH
GET /health
GET /health/db
Current Frontend Deliverable
For now, the frontend team's main deliverable should be:

Authentication UI
+
Protected dashboard shell
+
Reusable API/auth architecture
This will make it easy to connect customer, PPPoE, Hotspot, payment, router, and reporting modules as their backend APIs become available.


