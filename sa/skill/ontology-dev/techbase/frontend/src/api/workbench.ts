import { http, type PageResult } from './request'
import type { FlowTask } from './flow'
import type { Customer } from './customer'

export interface TodoItem extends FlowTask {
  customer_name?: string
  customer_no?: string
  applicant_name?: string
  started_at?: string
}

export interface DoneItem extends FlowTask {
  customer_name?: string
  customer_no?: string
}

export interface RequestedItem extends Customer {
  flow_status?: string
}

export const workbenchApi = {
  todo(params: { page?: number; size?: number }) {
    return http.get<PageResult<TodoItem>>('/workbench/todo', params)
  },
  done(params: { page?: number; size?: number }) {
    return http.get<PageResult<DoneItem>>('/workbench/done', params)
  },
  requested(params: { page?: number; size?: number }) {
    return http.get<PageResult<RequestedItem>>('/workbench/requested', params)
  },
  approve(taskId: number, comment: string) {
    return http.post(`/workbench/todo/${taskId}/approve`, { comment })
  },
  reject(taskId: number, comment: string) {
    return http.post(`/workbench/todo/${taskId}/reject`, { comment })
  },
  returnTask(taskId: number, comment: string) {
    return http.post(`/workbench/todo/${taskId}/return`, { comment })
  },
}
