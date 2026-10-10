import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Eye, Undo2 } from 'lucide-react'
import { workbenchApi, type RequestedItem } from '../../api/workbench'
import { customerApi } from '../../api/customer'
import Pagination from '../../components/Pagination'
import { toast } from '../../components/toast'
import { Badge } from '../../utils/status'

export default function Requested() {
  const navigate = useNavigate()
  const [page, setPage] = useState(1)
  const [size] = useState(10)
  const [data, setData] = useState<RequestedItem[]>([])
  const [total, setTotal] = useState(0)

  const load = async () => {
    const res = await workbenchApi.requested({ page, size })
    setData(res.list)
    setTotal(res.total)
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page])

  const handleWithdraw = async (c: RequestedItem) => {
    if (!window.confirm(`确认撤回客户「${c.customer_name}」的申请？`)) return
    try {
      await customerApi.withdraw(c.id)
      toast('已撤回')
      load()
    } catch (err: any) {
      toast(err.message, 'error')
    }
  }

  return (
    <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
      <div style={{ padding: '14px 20px', borderBottom: '1px solid var(--divider-color)' }}>
        <h3 style={{ fontWeight: 700 }}>我的申请</h3>
      </div>
      <div className="table-container">
        <table>
          <thead>
            <tr>
              <th>客户编号</th>
              <th>客户名称</th>
              <th>客户类型</th>
              <th>审批状态</th>
              <th>申请时间</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            {data.map((c) => (
              <tr key={c.id}>
                <td>{c.customer_no}</td>
                <td>{c.customer_name}</td>
                <td>{c.customer_type}</td>
                <td><Badge status={c.status} /></td>
                <td>{c.created_at}</td>
                <td>
                  <button className="btn btn-secondary btn-sm" onClick={() => navigate(`/customer/apply?id=${c.id}`)}>
                    <Eye size={14} /> 查看
                  </button>
                  {c.status === '待客户经理审批' && (
                    <button className="btn btn-secondary btn-sm" style={{ marginLeft: 8 }} onClick={() => handleWithdraw(c)}>
                      <Undo2 size={14} /> 撤回
                    </button>
                  )}
                </td>
              </tr>
            ))}
            {data.length === 0 && (
              <tr>
                <td colSpan={6} style={{ textAlign: 'center', color: '#94a3b8' }}>暂无申请</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      <div style={{ padding: '14px 20px', display: 'flex', justifyContent: 'flex-end' }}>
        <Pagination page={page} size={size} total={total} onChange={setPage} />
      </div>
    </div>
  )
}
