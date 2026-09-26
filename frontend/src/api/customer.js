import api from "./client";

export async function getCustomers({
  page = 1,
  perPage = 20,
  search = "",
  status = "",
} = {}) {
  const params = {
    page,
    per_page: perPage,
  };

  if (search) {
    params.search = search;
  }

  if (status) {
    params.status = status;
  }

  const response = await api.get(
    "/customers",
    { params }
  );

  return response.data;
}

export async function getCustomer(customerId) {
  const response = await api.get(
    `/customers/${customerId}`
  );

  return response.data;
}

export async function createCustomer(customer) {
  const response = await api.post(
    "/customers",
    customer
  );

  return response.data;
}

export async function updateCustomer(
  customerId,
  customer
) {
  const response = await api.patch(
    `/customers/${customerId}`,
    customer
  );

  return response.data;
}

export async function updateCustomerStatus(
  customerId,
  status
) {
  const response = await api.patch(
    `/customers/${customerId}/status`,
    { status }
  );

  return response.data;
}