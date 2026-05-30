import { apiRequest } from './client';

export interface MeResponse {
  id: string;
  email: string;
  display_name: string;
  role: string;
  groups: string[];
  permissions: string[];
}

export async function getMe(): Promise<MeResponse> {
  return apiRequest<MeResponse>('/api/me');
}
