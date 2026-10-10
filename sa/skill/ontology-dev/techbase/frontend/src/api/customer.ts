import { http, type PageResult } from './request'

export interface Customer {
  id: number
  customer_no: string
  customer_name: string
  customer_type: string
  industry: string | null
  contact_person: string | null
  contact_phone: string | null
  customer_level: string
  address: string | null
  remark: string | null
  status: string
  applicant_id: number | null
  applicant_name: string | null
  instance_id: number | null
  created_at: string
  flow_status?: string
}

export const customerApi = {
  list(params: { page?: number; size?: number; customer_no?: string; customer_name?: string; status?: string }) {
    return http.get<PageResult<Customer>>('/customer', params)
  },
  get(id: number) {
    return http.get<Customer>(`/customer/${id}`)
  },
  createDraft(data: Partial<Customer>) {
    return http.post<Customer>('/customer/draft', data)
  },
  updateDraft(id: number, data: Partial<Customer>) {
    return http.put<Customer>(`/customer/${id}/draft`, data)
  },
  submit(id: number) {
    return http.post<Customer>(`/customer/${id}/submit`)
  },
  withdraw(id: number) {
    return http.post<Customer>(`/customer/${id}/withdraw`)
  },
}
