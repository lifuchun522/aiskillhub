import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { RotateCcw, Save, Send } from 'lucide-react'
import { customerApi, type Customer } from '../../api/customer'
import { metaApi, type DictItem } from '../../api/meta'
import { toast } from '../../components/toast'
import { Badge } from '../../utils/status'

const emptyForm = {
  customer_name: '',
  customer_type: '',
  industry: '',
  contact_person: '',
  contact_phone: '',
  customer_level: '',
  address: '',
  remark: '',
}

export default function CustomerApply() {
  const [searchParams, setSearchParams] = useSearchParams()
  const id = searchParams.get('id')
  const [form, setForm] = useState({ ...emptyForm })
  const [customerId, setCustomerId] = useState<number | null>(id ? Number(id) : null)
  const [status, setStatus] = useState('')
  const [types, setTypes] = useState<DictItem[]>([])
  const [levels, setLevels] = useState<DictItem[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    metaApi.dictionaries().then((d) => {
      setTypes(d.CUSTOMER_TYPE)
      setLevels(d.CUSTOMER_LEVEL)
    })
  }, [])

  useEffect(() => {
    if (customerId) {
      customerApi.get(customerId).then((c) => {
        setForm({
          customer_name: c.customer_name,
          customer_type: c.customer_type,
          industry: c.industry || '',
          contact_person: c.contact_person || '',
          contact_phone: c.contact_phone || '',
          customer_level: c.customer_level,
          address: c.address || '',
          remark: c.remark || '',
        })
        setStatus(c.status)
      })
    }
  }, [customerId])

  const set = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }))

  const editable = status === '' || status === '草稿' || status === '已驳回'

  const saveDraft = async (): Promise<number | null> => {
    if (!form.customer_name || !form.customer_type || !form.customer_level) {
      toast('请填写客户名称、客户类型、客户等级', 'error')
      return null
    }
    try {
      if (customerId) {
        await customerApi.updateDraft(customerId, form)
        return customerId
      }
      const c = await customerApi.createDraft(form)
      setCustomerId(c.id)
      setSearchParams({ id: String(c.id) })
      return c.id
    } catch (err: any) {
      toast(err.message, 'error')
      return null
    }
  }

  const handleDraft = async () => {
    const savedId = await saveDraft()
    if (savedId) toast('暂存成功')
  }

  const handleSubmit = async () => {
    setLoading(true)
    try {
      const savedId = await saveDraft()
      if (!savedId) return
      const c = await customerApi.submit(savedId)
      setStatus(c.status)
      toast('提交成功，已启动客户审批流')
    } catch (err: any) {
      toast(err.message, 'error')
    } finally {
      setLoading(false)
    }
  }

  const handleReset = () => {
    setForm({ ...emptyForm })
    setCustomerId(null)
    setStatus('')
    setSearchParams({})
  }

  return (
    <div className="card">
      <div className="card-title">
        <h2>客户申请</h2>
        <div className="toolbar">
          {status && status !== '草稿' && status !== '已驳回' && <Badge status={status} />}
          <button className="btn btn-secondary" onClick={handleReset}>
            <RotateCcw size={14} /> 重置
          </button>
          <button className="btn btn-secondary" onClick={handleDraft} disabled={!editable}>
            <Save size={14} /> 暂存
          </button>
          <button className="btn btn-primary" onClick={handleSubmit} disabled={!editable || loading}>
            <Send size={14} /> 提交
          </button>
        </div>
      </div>

      <div className="form-grid-2">
        <div className="form-item">
          <label className="field-label required">客户名称</label>
          <div className="field-control">
            <input value={form.customer_name} onChange={(e) => set('customer_name', e.target.value)} disabled={!editable} />
          </div>
        </div>
        <div className="form-item">
          <label className="field-label required">客户类型</label>
          <div className="field-control">
            <select value={form.customer_type} onChange={(e) => set('customer_type', e.target.value)} disabled={!editable}>
              <option value="">请选择</option>
              {types.map((t) => (
                <option key={t.code} value={t.code}>{t.label}</option>
              ))}
            </select>
          </div>
        </div>
        <div className="form-item">
          <label className="field-label">所属行业</label>
          <div className="field-control">
            <input value={form.industry} onChange={(e) => set('industry', e.target.value)} disabled={!editable} />
          </div>
        </div>
        <div className="form-item">
          <label className="field-label">联系人</label>
          <div className="field-control">
            <input value={form.contact_person} onChange={(e) => set('contact_person', e.target.value)} disabled={!editable} />
          </div>
        </div>
        <div className="form-item">
          <label className="field-label">联系电话</label>
          <div className="field-control">
            <input value={form.contact_phone} onChange={(e) => set('contact_phone', e.target.value)} disabled={!editable} />
          </div>
        </div>
        <div className="form-item">
          <label className="field-label required">客户等级</label>
          <div className="field-control">
            <select value={form.customer_level} onChange={(e) => set('customer_level', e.target.value)} disabled={!editable}>
              <option value="">请选择</option>
              {levels.map((t) => (
                <option key={t.code} value={t.code}>{t.label}</option>
              ))}
            </select>
          </div>
        </div>
        <div className="form-item span-2">
          <label className="field-label">客户地址</label>
          <div className="field-control">
            <input value={form.address} onChange={(e) => set('address', e.target.value)} disabled={!editable} />
          </div>
        </div>
        <div className="form-item span-2">
          <label className="field-label">备注</label>
          <div className="field-control">
            <textarea rows={3} value={form.remark} onChange={(e) => set('remark', e.target.value)} disabled={!editable} />
          </div>
        </div>
      </div>
    </div>
  )
}
