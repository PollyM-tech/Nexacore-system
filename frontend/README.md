
That version reflects what **you are actually doing**, rather than telling you to use `uv` when you chose `requirements.txt`.

For `frontend/README.md`, change it to:

```markdown
# Lintech Frontend

React 19 + TypeScript frontend for the Lintech ISP management platform.

The current frontend provides the working admin dashboard and customer portal.
It will be progressively redesigned with Lintech branding, UI/UX, and navigation
while preserving the existing backend integrations.

## Current Stack

- React 19
- TypeScript
- Vite
- Tailwind CSS v4
- Flowbite React
- React Router
- TanStack Query
- Axios

## Structure

```text
src/
├── app/        # Router, providers, authentication
├── pages/      # Route screens
├── features/   # Domain UI and hooks
└── shared/     # Components, API client, tables, theme