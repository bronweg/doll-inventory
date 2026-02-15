import { apiRequest } from './client';

export interface Doll {
  id: number;
  name: string;
  location: 'HOME' | 'BAG';
  bag_number: number | null;
  primary_photo_url: string | null;
  created_at: string;
  updated_at: string;
  photos_count?: number;
}

export interface DollsListResponse {
  items: Doll[];
  total: number;
  limit: number;
  offset: number;
}

export interface Photo {
  id: number;
  doll_id: number;
  url: string;
  is_primary: boolean;
  created_at: string;
  created_by: string;
}

export interface PhotosListResponse {
  doll_id: number;
  primary_photo_id: number | null;
  photos: Photo[];
}

export interface DollUpdateData {
  location?: 'HOME' | 'BAG';
  bag_number?: number | null;
}

export async function getDolls(params?: {
  q?: string;
  location?: 'HOME' | 'BAG';
  bag?: number;
  limit?: number;
  offset?: number;
}): Promise<DollsListResponse> {
  const searchParams = new URLSearchParams();
  
  if (params?.q) searchParams.append('q', params.q);
  if (params?.location) searchParams.append('location', params.location);
  if (params?.bag !== undefined) searchParams.append('bag', params.bag.toString());
  if (params?.limit) searchParams.append('limit', params.limit.toString());
  if (params?.offset) searchParams.append('offset', params.offset.toString());
  
  const query = searchParams.toString();
  const endpoint = `/api/dolls${query ? `?${query}` : ''}`;
  
  return apiRequest<DollsListResponse>(endpoint);
}

export async function getDoll(id: number): Promise<Doll> {
  return apiRequest<Doll>(`/api/dolls/${id}`);
}

export async function updateDoll(id: number, data: DollUpdateData): Promise<Doll> {
  return apiRequest<Doll>(`/api/dolls/${id}`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
  });
}

export async function getPhotos(dollId: number): Promise<PhotosListResponse> {
  return apiRequest<PhotosListResponse>(`/api/dolls/${dollId}/photos`);
}

export async function uploadPhoto(
  dollId: number,
  file: File,
  makePrimary: boolean = true
): Promise<Photo> {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('make_primary', makePrimary.toString());
  
  return apiRequest<Photo>(`/api/dolls/${dollId}/photos`, {
    method: 'POST',
    body: formData,
  });
}

export async function setPrimaryPhoto(photoId: number): Promise<void> {
  return apiRequest<void>(`/api/photos/${photoId}/set-primary`, {
    method: 'POST',
  });
}

