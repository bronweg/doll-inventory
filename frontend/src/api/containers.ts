/**
 * API client for containers endpoints.
 */
import { apiRequest } from './client';

export interface Container {
  id: number;
  name: string;
  sort_order: number;
  is_active: boolean;
  is_system: boolean;
  created_at: string;
  updated_at: string;
}

export interface ContainerListResponse {
  items: Container[];
  total: number;
}

export interface ContainerCreateData {
  name: string;
}

export interface ContainerUpdateData {
  name?: string;
  sort_order?: number;
  is_active?: boolean;
}

/**
 * Get all active containers ordered by sort_order.
 */
export async function getContainers(): Promise<ContainerListResponse> {
  return apiRequest<ContainerListResponse>('/api/containers');
}

/**
 * Create a new container.
 */
export async function createContainer(data: ContainerCreateData): Promise<Container> {
  return apiRequest<Container>('/api/containers', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
  });
}

/**
 * Update a container.
 */
export async function updateContainer(id: number, data: ContainerUpdateData): Promise<Container> {
  return apiRequest<Container>(`/api/containers/${id}`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
  });
}

/**
 * Delete a container (soft delete).
 */
export async function deleteContainer(id: number): Promise<void> {
  return apiRequest<void>(`/api/containers/${id}`, {
    method: 'DELETE',
  });
}

