"use client"
import { useState, useRef } from 'react';
import { useRouter } from 'next/navigation';

export default function Home() {
  const [isUploading, setIsUploading] = useState(false);
  const [pipelineType, setPipelineType] = useState<'BOQ' | 'CPC'>('BOQ');
  const fileInputRef = useRef<HTMLInputElement>(null);
  const router = useRouter();

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setIsUploading(true);
      const file = e.target.files[0];
      const formData = new FormData();
      formData.append('file', file);
      formData.append('pipeline_type', pipelineType);

      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';
        const response = await fetch(`${apiUrl}/uploads`, {
          method: 'POST',
          body: formData,
        });
        
        if (response.ok) {
          const data = await response.json();
          router.push(`/review/${data.project_id}`);
        } else {
          try {
            const errData = await response.json();
            if (errData.error) {
              alert("⚠️ " + errData.error);
            } else {
              alert('Upload failed.');
            }
          } catch (e) {
            alert('Upload failed.');
          }
          setIsUploading(false);
        }
      } catch (err) {
        console.error(err);
        alert('Network error.');
        setIsUploading(false);
      }
    }
  };

  return (
    <>
      <div className="hero-section">
        <h1>Transformez vos appels d'offres<br/>en alternatives compétitives</h1>
        <p>Optimisez vos propositions d'éclairage avec notre moteur de substitution intelligent.</p>
      </div>

      <div className="pipeline-cards">
        <div 
          className={`pipeline-card ${pipelineType === 'BOQ' ? 'selected' : ''}`}
          onClick={() => setPipelineType('BOQ')}
        >
          <div className="pipeline-card-header">
            <svg className="pipeline-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" /></svg>
            <div className="radio-circle"></div>
          </div>
          <h3>AO Privé / BOQ</h3>
          <ul className="pipeline-list">
            <li>
              <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" /></svg>
              Tableaux & fiches techniques
            </li>
            <li>
              <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" /></svg>
              Extraction structurée par colonnes
            </li>
          </ul>
        </div>

        <div 
          className={`pipeline-card ${pipelineType === 'CPC' ? 'selected' : ''}`}
          onClick={() => setPipelineType('CPC')}
        >
          <div className="pipeline-card-header">
            <svg className="pipeline-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" /><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 9h1.5m-1.5 4h6m-6 4h6" /></svg>
            <div className="radio-circle"></div>
          </div>
          <h3>AO Public / CPC</h3>
          <ul className="pipeline-list">
            <li>
              {pipelineType === 'CPC' ? (
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" /></svg>
              ) : (
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 10h16M4 14h16M4 18h16" /></svg>
              )}
              Prose réglementaire (CPS/CPC)
            </li>
            <li>
              {pipelineType === 'CPC' ? (
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" /></svg>
              ) : (
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" /></svg>
              )}
              Isolation intelligente des luminaires
            </li>
          </ul>
        </div>
      </div>

      <div className="upload-zone-wrapper" onClick={() => fileInputRef.current?.click()}>
        {isUploading ? (
          <div>
            <svg className="upload-icon animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
            <h3>Traitement en cours...</h3>
            {pipelineType === 'CPC' ? (
              <p>📄 Traitement d'un document scanné en cours...<br/>Cela peut prendre 5 à 15 minutes selon la taille.<br/>Le traitement continue en arrière-plan — vous pouvez revenir plus tard.</p>
            ) : (
              <p>Analyse et extraction des données via le moteur LAE.</p>
            )}
          </div>
        ) : (
          <div>
            <svg className="upload-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" /></svg>
            <h3>Glissez votre document ou cliquez pour parcourir</h3>
            <p>Formats supportés : PDF, Excel, CSV, Word</p>
          </div>
        )}
        <input 
          type="file" 
          className="input-file" 
          ref={fileInputRef} 
          accept=".xlsx,.csv,.pdf,.docx,.doc"
          onChange={handleFileChange}
          disabled={isUploading}
        />
      </div>

      <div className="recent-header">
        <h2>Projets Récents</h2>
        <a href="#">Voir tout</a>
      </div>

      <div className="recent-grid">
        <div className="recent-card">
          <div className="recent-card-top">
            <svg className="recent-card-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" /></svg>
            <span className="status-badge status-term">TERMINÉ</span>
          </div>
          <div className="recent-card-title">Tour_Montparnasse_BOQ.xlsx</div>
          <div className="recent-card-meta">12 Oct 2026 • AO Privé</div>
        </div>

        <div className="recent-card">
          <div className="recent-card-top">
            <svg className="recent-card-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>
            <span className="status-badge status-cours">EN COURS</span>
          </div>
          <div className="recent-card-title">CHU_Nantes_CCTP_Eclairage.pdf</div>
          <div className="recent-card-meta">10 Oct 2026 • AO Public</div>
        </div>

        <div className="recent-card">
          <div className="recent-card-top">
            <svg className="recent-card-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" /></svg>
            <span className="status-badge status-err">ERREUR</span>
          </div>
          <div className="recent-card-title">Ecole_Maternelle_Devis.csv</div>
          <div className="recent-card-meta">08 Oct 2026 • AO Privé</div>
        </div>
      </div>
    </>
  );
}
