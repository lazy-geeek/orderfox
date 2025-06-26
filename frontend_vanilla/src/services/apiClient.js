
const API_BASE_URL = 'http://localhost:8000/api/v1';

const apiClient = {
  get: async (url) => {
    const response = await fetch(`${API_BASE_URL}${url}`);
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || errorData.message || `HTTP error! status: ${response.status}`);
    }
    return response.json();
  },

  post: async (url, data) => {
    const response = await fetch(`${API_BASE_URL}${url}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    });
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || errorData.message || `HTTP error! status: ${response.status}`);
    }
    return response.json();
  },
};

export default apiClient;
