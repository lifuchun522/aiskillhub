import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Eye, RotateCcw, Search } from 'lucide-react'
import { customerApi, type Customer } from '../../api/customer'
import { metaApi, type DictItem } from '../../api/meta'
import Pagination from '../../components/Pagination'
import { Badge } from '../../utils/status'

export default function CustomerQuery() {
  const navigate = useNavigate()
  const [filters, setFilters] = useState({ customer_no: '', customer_name: '', status: '' })
  const [page, setPage] = useState(1)
  const [size] = useState(10)
  const [data, setData] = useState<Customer[]>([])
  const [total, setTotal] = useState(0)
  const [types, setTypes] = useState<DictItem[]>([])
  const [levels, setLevels] = useState<DictItem[]>([])
  const [statuses, setStatuses] = useState<string[]>([])

  const label = (items: DictItem[], code: string) => items.find((i) => i.code === code)?.label || code

  useEffect(() => {
    metaApi.dictionaries().then((d) => {
      setTypes(d.CUSTOMER_TYPE)
      setLevels(d.CUSTOMER_LEVEL)
    })
    metaApi.customerStatus().then(setStatuses)
  }, [])

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page])

  const load = async () => {
    const res = await customerApi.list({ page, size, ...filters })
    setData(res.list)
    setTotal(res.total)
  }

  const handleQuery = () => {
    setPage(1)
    load()
  }

  const handleReset = () => {
    setFilters({ customer_no: '', customer_name: '', status: '' })
    setPage(1)
  }

  return (
    <div>
      <div className="card" style={{ padding: '20px' }}>
        <div className="form-grid-3">
          <div className="form-item">
            <label className="field-label">客户编号</label>
            <div className="field-control">
              <input value={filters.customer_no} onChange={(e) => setFilters({ ...filters, customer_no: e.target.value })} />
            </div>
          </div>
          <div className="form-item">
            <label className="field-label">客户名称</label>
            <div className="field-control">
              <input value={filters.customer_name} onChange={(e) => setFilters({ ...filters, customer_name: e.target.value })} />
            </div>
          </div>
          <div className="form-item">
            <label className="field-label">审批状态</label>
            <div className="field-control">
              <select value={filters.status} onChange={(e) => setFilters({ ...filters, status: e.target.value })}>
                <option value="">全部</option>
                {statuses.map((s) => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
            </div>
          </div>
        </div>
        <div className="toolbar-right">
          <button className="btn btn-primary" onClick={handleQuery}>
            <Search size={14} /> 查询
          </button>
          <button className="btn btn-secondary" onClick={handleReset}>
            <RotateCcw size={14} /> 重置
          </button>
        </div>
      </div>

      <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
        <div style={{ padding: '14px 20px', borderBottom: '1px solid var(--divider-color)' }}>
          <h3 style={{ fontWeight: 700 }}>查询结果</h3>
        </div>
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>客户编号</th>
                <th>客户名称</th>
                <th>客户类型</th>
                <th>客户等级</th>
                <th>联系人</th>
                <th>联系电话</th>
                <th>审批状态</th>
                <th>申请人</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {data.map((c) => (
                <tr key={c.id}>
                  <td>{c.customer_no}</td>
                  <td>{c.customer_name}</td>
                  <td>{label(types, c.customer_type)}</td>
                  <td>{label(levels, c.customer_level)}</td>
                  <td>{c.contact_person || '-'}</td>
                  <td>{c.contact_phone || '-'}</td>
                  <td><Badge status={c.status} /></td>
                  <td>{c.applicant_name || '-'}</td>
                  <td>
                    <button
                      className="btn btn-secondary btn-sm"
                      onClick={() => navigate(`/customer/apply?id=${c.id}`)}
                    >
                      <Eye size={14} /> 查看
                    </button>
                  </td>
                </tr>
              ))}
              {data.length === 0 && (
                <tr>
                  <td colSpan={9} style={{ textAlign: 'center', color: '#94a3b8' }}>
                    暂无数据
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        <div style={{ padding: '14px 20px', display: 'flex', justifyContent: 'flex-end' }}>
          <Pagination page={page} size={size} total={total} onChange={setPage} />
        </div>
      </div>
    </div>
  )
}
