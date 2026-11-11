"use client"
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';

export default function ReviewPage({ params }: { params: { projectId: string } }) {
  const [data, setData] = useState<any>(null);
  const [progressData, setProgressData] = useState<any>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [selectedLineId, setSelectedLineId] = useState<string | null>(null);
  const router = useRouter();

  useEffect(() => {
    let timeoutId: NodeJS.Timeout;
    
    const fetchProgress = async () => {
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';
        const res = await fetch(`${apiUrl}/uploads/${params.projectId}/progress`);
        if (res.ok) {
          const result = await res.json();
          setProgressData(result);
          
          if (result.status === "processing") {
            timeoutId = setTimeout(fetchProgress, 2000);
          } else if (result.status === "draft" || result.status === "completed") {
            fetchPreview();
          }
        } else {
          fetchPreview();
        }
      } catch (err) {
        console.error(err);
        timeoutId = setTimeout(fetchProgress, 2000);
      }
    };

    const fetchPreview = async () => {
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';
        const res = await fetch(`${apiUrl}/uploads/${params.projectId}/preview`);
        if (res.ok) {
          const result = await res.json();
          setData(result);
        }
      } catch (err) {
        console.error(err);
      }
    };
    
    fetchProgress();
    
    return () => {
      if (timeoutId) clearTimeout(timeoutId);
    };
  }, [params.projectId]);

  const handleLineChange = (lineId: string, field: string, value: any) => {
    const newLines = data.lines.map((l: any) => {
      if (l.id === lineId) {
        if (field.startsWith('pro.')) {
          const parts = field.split('.'); // e.g. pro.electrical.wattage
          if (parts.length === 3) {
            const category = parts[1];
            const prop = parts[2];
            return {
              ...l,
              pro: {
                ...l.pro,
                [category]: {
                  ...(l.pro?.[category] || {}),
                  [prop]: value
                }
              }
            };
          }
        }
        return { ...l, [field]: value };
      }
      return l;
    });
    setData({ ...data, lines: newLines });
  };

  const handleConfirm = async () => {
    setIsSubmitting(true);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';
      const payload = { lines: data.lines };
      const res = await fetch(`${apiUrl}/uploads/${params.projectId}/confirm`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (res.ok) {
        router.push(`/project/${params.projectId}`);
      } else {
        alert("Confirmation failed");
      }
    } catch(err) {
      console.error(err);
      alert("Network error");
    } finally {
      setIsSubmitting(false);
    }
  };

  const getHealthColor = (line: any) => {
    const w = line.pro?.electrical?.wattage;
    const l = line.pro?.photometric?.delivered_lumens || line.pro?.photometric?.lumens_min?.value;
    const ip = line.pro?.mechanical?.ip_rating_min;
    
    let score = 0;
    if (w !== null && w !== undefined && w !== '') score++;
    if (l !== null && l !== undefined && l !== '') score++;
    if (ip !== null && ip !== undefined && ip !== '') score++;

    if (score === 3) return 'health-green';
    if (score >= 1) return 'health-orange';
    return 'health-red';
  };

  if (!data && !progressData) return <div className="validation-container" style={{ padding: '2rem' }}>Chargement de l'aperçu...</div>;

  if (progressData && progressData.status === "processing" && !data?.lines) {
    // ... loading UI
    const total = progressData.total || 1;
    const completed = progressData.processed || 0;
    const percent = progressData.percent || 0;
    
    let etaDisplay = "Calcul en cours...";
    if (progressData.eta_seconds !== null && progressData.eta_seconds !== undefined) {
      const minutes = Math.floor(progressData.eta_seconds / 60);
      const seconds = progressData.eta_seconds % 60;
      etaDisplay = `~${minutes} min ${seconds} s`;
    }

    let marketingMessage = "Lecture du document...";
    if (total > 1 && completed > 0) {
        marketingMessage = `Extraction des luminaires ${completed}/${total} (Groq)`;
    }

    return (
      <div className="validation-container" style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ padding: '4rem', textAlign: 'center', maxWidth: '800px', width: '100%' }}>
          <div style={{ marginBottom: '2rem', display: 'flex', justifyContent: 'center' }}>
            <div className="badge badge-warning animate-spin" style={{ width: '48px', height: '48px', borderRadius: '50%', padding: 0, border: '3px solid var(--primary)', borderTopColor: 'transparent', boxShadow: '0 0 15px rgba(37, 99, 235, 0.3)' }}></div>
          </div>
          
          <h2 style={{ color: 'var(--text-main)', marginBottom: '0.5rem', fontSize: '2.2rem', fontWeight: 700, letterSpacing: '-0.02em' }}>
            Intelligence Documentaire Active
          </h2>
          
          <p style={{ color: 'var(--primary)', marginBottom: '3rem', fontSize: '1.1rem', fontWeight: 500, height: '1.5rem', transition: 'all 0.3s ease' }}>
            {marketingMessage}
          </p>

          <div className="progress-container" style={{ width: '100%', margin: '0 auto', maxWidth: '600px' }}>
            <div className="progress-track" style={{ height: '12px', background: '#e2e8f0', borderRadius: '6px', overflow: 'hidden' }}>
              <div className="progress-fill" style={{ width: `${percent}%`, background: 'linear-gradient(90deg, #2563eb, #3b82f6)', height: '100%', transition: 'width 0.5s ease' }}></div>
            </div>
            <div className="progress-text" style={{ marginTop: '1rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ color: 'var(--text-muted)' }}>⏱ Temps restant estimé : <strong style={{color: 'var(--text-main)'}}>{etaDisplay}</strong></span>
              <span style={{ fontWeight: 600, color: 'var(--text-main)' }}>
                {percent}% <span style={{ opacity: 0.5, fontSize: '0.8rem', marginLeft: '0.3rem' }}>({completed} / {total})</span>
              </span>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (data?.status === "error" || progressData?.status === "error") {
    return (
      <div className="validation-container" style={{ padding: '4rem', textAlign: 'center' }}>
        <h2 style={{ color: 'var(--danger)', marginBottom: '1rem' }}>Erreur d'extraction</h2>
        <p style={{ color: 'var(--text-muted)' }}>
          Impossible d'extraire des lignes valides. Veuillez vérifier le format.
        </p>
      </div>
    );
  }

  if (!data || !data.lines) {
    return <div className="validation-container" style={{ padding: '2rem', textAlign: 'center' }}>Chargement des données finales...</div>;
  }

  const selectedLine = data.lines.find((l: any) => l.id === selectedLineId);
  const originalFileName = data.original_filename || "Document Source";

  return (
    <div className="validation-container" style={{ padding: '2rem', paddingBottom: '100px' }}>
      <div style={{ marginBottom: '2rem' }}>
        <h1 style={{ fontSize: '2rem', marginBottom: '0.5rem', color: 'var(--text-main)', background: 'none', WebkitTextFillColor: 'initial' }}>Extraction Validation</h1>
        <p style={{ color: 'var(--text-muted)' }}>
          Verify the extracted data from Document Intelligence. Correct any errors before launching the substitution engine.
        </p>
      </div>

      <div className="validation-wrapper">
        <div className="validation-table-col">
          <div style={{ overflowX: 'auto', background: 'var(--bg-card)', borderRadius: '12px', border: '1px solid var(--border)' }}>
            <table className="validation-table" style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr>
                  <th style={{ width: '8%' }}>Mark</th>
                  <th style={{ width: '10%' }}>Family</th>
                  <th style={{ width: '10%' }}>Watts</th>
                  <th style={{ width: '10%' }}>Lumens</th>
                  <th style={{ width: '15%' }}>IP / IK</th>
                  <th style={{ width: '10%' }}>QTY</th>
                  <th style={{ width: '5%', textAlign: 'center' }}>Health</th>
                  <th style={{ width: '5%' }}></th>
                </tr>
              </thead>
              <tbody>
                {data.lines.map((line: any) => {
                  const pf = line.pro?.product_family || '';
                  let badgeColor = 'badge-autre';
                  if (pf === 'lampadaire') badgeColor = 'badge-lampadaire';
                  else if (pf === 'secours') badgeColor = 'badge-secours';
                  else if (pf === 'panel') badgeColor = 'badge-panel';
                  else if (pf === 'spot') badgeColor = 'badge-spot';
                  else if (pf === 'suspension') badgeColor = 'badge-suspension';
                  else if (pf === 'linear') badgeColor = 'badge-linear';
                  else if (pf === 'applique') badgeColor = 'badge-applique';
                  else if (pf === 'downlight') badgeColor = 'badge-downlight';
                  else if (pf === 'projecteur') badgeColor = 'badge-projecteur';

                  const formatVal = (val: any) => (val === null || val === undefined || val === '') ? '—' : val;
                  const isSelected = selectedLineId === line.id;
                  
                  const watts = formatVal(line.pro?.electrical?.wattage);
                  const lumens = formatVal(line.pro?.photometric?.delivered_lumens || line.pro?.photometric?.lumens_min?.value);
                  const ip = formatVal(line.pro?.mechanical?.ip_rating_min);
                  const ik = formatVal(line.pro?.mechanical?.ik_rating_min);

                  return (
                    <tr 
                      key={line.id} 
                      onClick={() => setSelectedLineId(isSelected ? null : line.id)}
                      style={{ 
                        cursor: 'pointer', 
                        backgroundColor: isSelected ? 'var(--bg-card-hover)' : 'transparent',
                        borderLeft: isSelected ? '4px solid var(--primary)' : '4px solid transparent'
                      }}
                    >
                      <td style={{ padding: '1rem', fontWeight: 500, color: 'var(--text-main)' }}>{line.mark || '—'}</td>
                      <td>
                        <span className={`badge ${badgeColor}`}>{pf || '—'}</span>
                      </td>
                      <td style={{ color: watts === '—' ? 'var(--danger)' : 'inherit' }}>{watts}{watts !== '—' ? 'W' : ''}</td>
                      <td style={{ color: lumens === '—' ? 'var(--danger)' : 'inherit' }}>{lumens}{lumens !== '—' ? 'lm' : ''}</td>
                      <td>{ip}/{ik}</td>
                      <td>{line.quantity || 1} units</td>
                      <td style={{ textAlign: 'center' }}>
                        <span className={`health-dot ${getHealthColor(line)}`}></span>
                      </td>
                      <td style={{ textAlign: 'center', color: 'var(--text-muted)' }}>
                         ⋮ 
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {selectedLine && (
          <div className="validation-side-panel">
            <div className="side-panel-header">
              <div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.2rem' }}>
                  Extracted from: {originalFileName}
                </div>
                <h3 style={{ margin: 0, color: 'var(--text-main)', fontSize: '1.2rem' }}>Technical Data Sheet - {selectedLine.mark || 'N/A'}</h3>
                <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.4rem', alignItems: 'center' }}>
                  <span style={{ 
                    fontSize: '0.7rem', 
                    fontWeight: 600, 
                    padding: '0.2rem 0.5rem', 
                    borderRadius: '4px',
                    background: selectedLine.raw_data?.engine_used === 'groq_escalated' ? 'rgba(245, 158, 11, 0.15)' : 'rgba(37, 99, 235, 0.1)',
                    color: selectedLine.raw_data?.engine_used === 'groq_escalated' ? 'var(--warning)' : 'var(--primary)'
                  }}>
                    {selectedLine.raw_data?.engine_used === 'groq_escalated' ? '⚡ Escaladé Groq (Teacher)' : '🤖 SLM Local (Qwen 2.5:3b)'}
                  </span>
                  {selectedLine.raw_data?.confidence_score && (
                    <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                      Confiance : {Math.round(selectedLine.raw_data.confidence_score * 100)}%
                    </span>
                  )}
                </div>
              </div>
              <button 
                onClick={() => setSelectedLineId(null)} 
                style={{ background: 'none', border: 'none', fontSize: '1.5rem', cursor: 'pointer', color: 'var(--text-muted)' }}
              >
                &times;
              </button>
            </div>
            
            <div className="side-panel-body">
              <div className="side-panel-section">
                <div className="side-panel-section-title">📄 Original Extracted Source Text</div>
                <div className="source-text-box">
                  {selectedLine.description || "Aucun texte source disponible."}
                </div>
              </div>

              <div className="side-panel-section">
                <div className="side-panel-section-title">⚡ Electrical Specifications</div>
                <div className="input-grid">
                  <div className="input-group">
                    <label>Power (W)</label>
                    <input 
                      type="text" 
                      className="panel-input"
                      value={selectedLine.pro?.electrical?.wattage ?? ''}
                      onChange={(e) => handleLineChange(selectedLine.id, 'pro.electrical.wattage', e.target.value ? parseFloat(e.target.value) : null)}
                    />
                  </div>
                  <div className="input-group">
                    <label>Voltage</label>
                    <input 
                      type="text" 
                      className="panel-input"
                      value={selectedLine.pro?.electrical?.voltage ?? ''}
                      onChange={(e) => handleLineChange(selectedLine.id, 'pro.electrical.voltage', e.target.value)}
                    />
                  </div>
                  <div className="input-group">
                    <label>Dimming</label>
                    <input 
                      type="text" 
                      className="panel-input"
                      value={selectedLine.pro?.electrical?.dimming_protocol ?? ''}
                      onChange={(e) => handleLineChange(selectedLine.id, 'pro.electrical.dimming_protocol', e.target.value)}
                    />
                  </div>
                </div>
              </div>

              <div className="side-panel-section">
                <div className="side-panel-section-title">☀️ Photometric Specifications</div>
                <div className="input-grid">
                  <div className="input-group">
                    <label>Flux (Lumens)</label>
                    <input 
                      type="text" 
                      className="panel-input"
                      value={(selectedLine.pro?.photometric?.delivered_lumens || selectedLine.pro?.photometric?.lumens_min?.value) ?? ''}
                      onChange={(e) => handleLineChange(selectedLine.id, 'pro.photometric.delivered_lumens', e.target.value ? parseInt(e.target.value) : null)}
                    />
                  </div>
                  <div className="input-group">
                    <label>CCT (K)</label>
                    <input 
                      type="text" 
                      className="panel-input"
                      value={(selectedLine.pro?.photometric?.cct_k || selectedLine.pro?.photometric?.cct?.value) ?? ''}
                      onChange={(e) => handleLineChange(selectedLine.id, 'pro.photometric.cct_k', e.target.value ? parseInt(e.target.value) : null)}
                    />
                  </div>
                  <div className="input-group">
                    <label>CRI</label>
                    <input 
                      type="text" 
                      className="panel-input"
                      value={selectedLine.pro?.photometric?.cri_min ?? ''}
                      onChange={(e) => handleLineChange(selectedLine.id, 'pro.photometric.cri_min', e.target.value ? parseInt(e.target.value) : null)}
                    />
                  </div>
                  <div className="input-group">
                    <label>Beam Angle</label>
                    <input 
                      type="text" 
                      className="panel-input"
                      value={selectedLine.pro?.photometric?.beam_angle_deg ?? ''}
                      onChange={(e) => handleLineChange(selectedLine.id, 'pro.photometric.beam_angle_deg', e.target.value ? parseFloat(e.target.value) : null)}
                    />
                  </div>
                </div>
              </div>

              <div className="side-panel-section">
                <div className="side-panel-section-title">🛠 Mechanical Specifications</div>
                <div className="input-grid">
                  <div className="input-group">
                    <label>IP Rating</label>
                    <input 
                      type="text" 
                      className="panel-input"
                      value={selectedLine.pro?.mechanical?.ip_rating_min ?? ''}
                      onChange={(e) => handleLineChange(selectedLine.id, 'pro.mechanical.ip_rating_min', e.target.value)}
                    />
                  </div>
                  <div className="input-group">
                    <label>IK Rating</label>
                    <input 
                      type="text" 
                      className="panel-input"
                      value={selectedLine.pro?.mechanical?.ik_rating_min ?? ''}
                      onChange={(e) => handleLineChange(selectedLine.id, 'pro.mechanical.ik_rating_min', e.target.value)}
                    />
                  </div>
                  <div className="input-group" style={{ gridColumn: '1 / -1' }}>
                    <label>Mounting Type</label>
                    <input 
                      type="text" 
                      className="panel-input"
                      value={selectedLine.pro?.mechanical?.mounting_type ?? ''}
                      onChange={(e) => handleLineChange(selectedLine.id, 'pro.mechanical.mounting_type', e.target.value)}
                    />
                  </div>
                </div>
              </div>
              
              <div style={{ marginTop: '2rem', display: 'flex', gap: '1rem', justifyContent: 'flex-end' }}>
                 <button 
                   onClick={() => setSelectedLineId(null)}
                   style={{ padding: '0.6rem 1rem', background: 'transparent', border: '1px solid var(--border)', borderRadius: '6px', cursor: 'pointer' }}
                 >
                   Fermer
                 </button>
              </div>

            </div>
          </div>
        )}
      </div>

      <div className="action-bar" style={{ position: 'fixed', bottom: 0, left: 0, right: 0, padding: '1rem 2rem', borderTop: '1px solid var(--border)', zIndex: 50 }}>
        <button 
          onClick={handleConfirm} 
          disabled={isSubmitting} 
          className="btn"
          style={{ float: 'right' }}
        >
          {isSubmitting ? 'Processing...' : 'Confirm & Launch Matching →'}
        </button>
      </div>
    </div>
  );
}
