import { useState, useRef } from 'react'
import { ingestion } from '../services/api'
import { Upload, FileText, CheckCircle, AlertTriangle, X, ChevronDown } from 'lucide-react'
import { Link } from 'react-router-dom'

const SOURCES = [
  {
    id: 'sap',
    label: 'SAP Export',
    scope: 'Scope 1',
    desc: 'Fuel & procurement flat file (MM movement type 261). Semicolon or tab-delimited, German or English headers.',
    accept: '.csv,.txt,.xls,.xlsx',
    sample: '/sample_data/sap_fuel_export.csv',
    color: '#f59e0b',
    fields: ['WERKS/PLANT', 'KOSTL', 'MENGE', 'MEINS', 'BUDAT', 'MATNR', 'MAKTX'],
  },
  {
    id: 'utility',
    label: 'Utility Data',
    scope: 'Scope 2',
    desc: 'Electricity portal CSV export. Columns: account number, meter ID, billing period, kWh, demand, tariff.',
    accept: '.csv,.xlsx',
    sample: '/sample_data/utility_electricity_export.csv',
    color: '#60a5fa',
    fields: ['Account Number', 'Meter ID', 'Service Address', 'Billing Period Start/End', 'kWh'],
  },
  {
    id: 'travel',
    label: 'Corporate Travel',
    scope: 'Scope 3',
    desc: 'Concur / Navan CSV export. Covers flights, hotels, car rental, rail, taxi.',
    accept: '.csv,.xlsx',
    sample: '/sample_data/travel_concur_export.csv',
    color: '#10b981',
    fields: ['Employee Name', 'Travel Date', 'Trip Type', 'Origin', 'Destination', 'Distance (km)', 'Class'],
  },
]

export default function UploadPage() {
  const [selected, setSelected] = useState(null)
  const [file, setFile] = useState(null)
  const [notes, setNotes] = useState('')
  const [dragging, setDragging] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const fileRef = useRef()

  const handleFile = f => {
    setFile(f); setResult(null); setError('')
  }

  const handleDrop = e => {
    e.preventDefault(); setDragging(false)
    const f = e.dataTransfer.files[0]
    if (f) handleFile(f)
  }

  const submit = async () => {
    if (!selected || !file) return
    setUploading(true); setError(''); setResult(null)
    try {
      const { data } = await ingestion.upload(file, selected.id, notes)
      setResult(data)
      setFile(null); setNotes('')
    } catch (e) {
      setError(e.response?.data?.error || 'Upload failed')
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="fade-in" style={{ maxWidth: 760 }}>
      <div style={{ marginBottom: 28 }}>
        <h1 style={{ fontSize: 22, fontWeight: 600, marginBottom: 4 }}>Upload Data</h1>
        <p style={{ color: 'var(--muted)', fontSize: 13 }}>
          Ingest activity data from SAP, utility portals, or your corporate travel platform.
        </p>
      </div>

      {/* Source selector */}
      <div style={{ marginBottom: 24 }}>
        <label style={{ marginBottom: 10, display: 'block' }}>1. Select data source</label>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12 }}>
          {SOURCES.map(s => (
            <button key={s.id}
              onClick={() => { setSelected(s); setResult(null); setError('') }}
              style={{
                background: selected?.id === s.id ? `${s.color}18` : 'var(--surface)',
                border: `1px solid ${selected?.id === s.id ? s.color : 'var(--border)'}`,
                borderRadius: 8, padding: 16, cursor: 'pointer', textAlign: 'left',
                transition: 'all 0.15s',
              }}>
              <div style={{ fontSize: 11, fontFamily: 'var(--font-mono)', color: s.color,
                fontWeight: 500, letterSpacing: '0.06em', textTransform: 'uppercase', marginBottom: 6 }}>
                {s.scope}
              </div>
              <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--text)', marginBottom: 6 }}>{s.label}</div>
              <div style={{ fontSize: 11, color: 'var(--muted)', lineHeight: 1.5 }}>{s.desc}</div>
            </button>
          ))}
        </div>
      </div>

      {selected && (
        <>
          {/* Expected fields */}
          <div className="card" style={{ marginBottom: 20, padding: 14 }}>
            <div style={{ fontSize: 11, color: 'var(--muted)', marginBottom: 8, fontFamily: 'var(--font-mono)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
              Expected columns
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
              {selected.fields.map(f => (
                <span key={f} className="badge badge-pending" style={{ fontSize: 10 }}>{f}</span>
              ))}
              <span style={{ fontSize: 11, color: 'var(--muted)', alignSelf: 'center' }}>+ others (flexible mapping)</span>
            </div>
          </div>

          {/* Drop zone */}
          <div style={{ marginBottom: 16 }}>
            <label style={{ marginBottom: 8, display: 'block' }}>2. Upload file</label>
            <div
              onDragOver={e => { e.preventDefault(); setDragging(true) }}
              onDragLeave={() => setDragging(false)}
              onDrop={handleDrop}
              onClick={() => fileRef.current?.click()}
              style={{
                border: `2px dashed ${dragging ? selected.color : file ? '#34d399' : 'var(--border)'}`,
                borderRadius: 10, padding: '36px 24px', textAlign: 'center',
                cursor: 'pointer', transition: 'all 0.15s',
                background: dragging ? `${selected.color}08` : file ? '#064e3b22' : 'var(--surface)',
              }}>
              {file ? (
                <div>
                  <CheckCircle size={28} color="#34d399" style={{ marginBottom: 8 }} />
                  <div style={{ fontWeight: 500, marginBottom: 4 }}>{file.name}</div>
                  <div style={{ fontSize: 12, color: 'var(--muted)' }}>{(file.size / 1024).toFixed(1)} KB</div>
                  <button onClick={e => { e.stopPropagation(); setFile(null) }}
                    style={{ marginTop: 10, background: 'none', border: 'none', color: 'var(--muted)',
                      cursor: 'pointer', fontSize: 12, display: 'inline-flex', alignItems: 'center', gap: 4 }}>
                    <X size={12} /> Remove
                  </button>
                </div>
              ) : (
                <div>
                  <Upload size={28} color="var(--muted)" style={{ marginBottom: 10 }} />
                  <div style={{ fontSize: 14, fontWeight: 500, marginBottom: 4 }}>
                    Drop file here or click to browse
                  </div>
                  <div style={{ fontSize: 12, color: 'var(--muted)' }}>
                    Accepts {selected.accept}
                  </div>
                </div>
              )}
              <input ref={fileRef} type="file" accept={selected.accept} style={{ display: 'none' }}
                onChange={e => handleFile(e.target.files[0])} />
            </div>
          </div>

          {/* Notes */}
          <div style={{ marginBottom: 20 }}>
            <label>3. Notes (optional)</label>
            <textarea value={notes} onChange={e => setNotes(e.target.value)}
              rows={2} placeholder="e.g. Q1 2024 fuel data for Delhi & Mumbai plants" />
          </div>

          {/* Error */}
          {error && (
            <div style={{ background: '#450a0a', border: '1px solid var(--danger)', borderRadius: 8,
              padding: '12px 16px', marginBottom: 16, fontSize: 13, color: 'var(--danger)' }}>
              <AlertTriangle size={14} style={{ marginRight: 8, verticalAlign: 'middle' }} />
              {error}
            </div>
          )}

          {/* Submit */}
          <button className="btn btn-primary" disabled={!file || uploading} onClick={submit}
            style={{ minWidth: 160, justifyContent: 'center' }}>
            {uploading ? (
              <span className="pulse">Processing…</span>
            ) : (
              <><Upload size={15} /> Ingest File</>
            )}
          </button>
        </>
      )}

      {/* Result */}
      {result && (
        <div className="card fade-in" style={{
          marginTop: 24, borderColor: '#10b981',
          background: 'rgba(16,185,129,0.05)',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
            <CheckCircle size={20} color="#34d399" />
            <span style={{ fontWeight: 600, fontSize: 15 }}>Ingestion complete</span>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12, marginBottom: 16 }}>
            {[
              { label: 'Records created', value: result.created, color: '#34d399' },
              { label: 'Parse errors', value: result.errors, color: result.errors > 0 ? '#f87171' : 'var(--muted)' },
              { label: 'Warnings', value: result.warnings, color: result.warnings > 0 ? '#fbbf24' : 'var(--muted)' },
            ].map(s => (
              <div key={s.label} style={{ background: 'var(--surface2)', borderRadius: 8, padding: 14 }}>
                <div style={{ fontSize: 11, color: 'var(--muted)', fontFamily: 'var(--font-mono)',
                  textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 4 }}>{s.label}</div>
                <div style={{ fontSize: 22, fontWeight: 600, color: s.color }}>{s.value}</div>
              </div>
            ))}
          </div>

          {result.error_detail?.length > 0 && (
            <details style={{ marginBottom: 12 }}>
              <summary style={{ fontSize: 12, color: 'var(--warn)', cursor: 'pointer', marginBottom: 8 }}>
                Show parse errors ({result.error_detail.length})
              </summary>
              <div style={{ background: 'var(--surface2)', borderRadius: 6, padding: 12, maxHeight: 200, overflow: 'auto' }}>
                {result.error_detail.map((e, i) => (
                  <div key={i} style={{ fontSize: 11, fontFamily: 'var(--font-mono)', color: 'var(--muted)', marginBottom: 4 }}>
                    Row {e.row}: {e.error}
                  </div>
                ))}
              </div>
            </details>
          )}

          <Link to="/records" className="btn btn-secondary" style={{ textDecoration: 'none' }}>
            Review records →
          </Link>
        </div>
      )}
    </div>
  )
}
