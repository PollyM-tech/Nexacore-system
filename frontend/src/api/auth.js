import api from "./client";


export async function login(email, password) {
  const response = await api.post(
    "/auth/login",
    {
      email,
      password,
    }
  );

  return response.data;
}


export async function getMe() {
  const response = await api.get(
    "/auth/me"
  );

  return response.data;
}


export async function refreshAccessToken() {
  const refreshToken =
    localStorage.getItem("refresh_token");

  const response = await api.post(
    "/auth/refresh",
    {},
    {
      headers: {
        Authorization: `Bearer ${refreshToken}`,
      },
    }
  );

  return response.data;
}