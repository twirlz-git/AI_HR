import React, { useState, useRef } from 'react';

interface AnalysisResult {
  name: string;
  score: number;
}

interface ApiResponse {
  results: AnalysisResult[];
  error?: string;
}

const ResumeAnalysis: React.FC = () => {
  const [results, setResults] = useState<AnalysisResult[]>([]);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [jobFile, setJobFile] = useState<File | null>(null);
  const [resumeFiles, setResumeFiles] = useState<File[]>([]);
  const jobFileInputRef = useRef<HTMLInputElement>(null);
  const resumeFileInputRef = useRef<HTMLInputElement>(null);

  const handleJobFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      setJobFile(file);
    }
  };

  const handleResumeFilesUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files || []);
    setResumeFiles(files);
  };

  const clearJobFile = () => {
    setJobFile(null);
    if (jobFileInputRef.current) {
      jobFileInputRef.current.value = '';
    }
  };

  const clearResumeFiles = () => {
    setResumeFiles([]);
    if (resumeFileInputRef.current) {
      resumeFileInputRef.current.value = '';
    }
  };

  const analyzeFiles = async () => {
    if (!jobFile || resumeFiles.length === 0) {
      alert('Загрузите файл описания вакансии и файлы резюме.');
      return;
    }

    setIsAnalyzing(true);
    setResults([]);

    try {
      const formData = new FormData();
      formData.append('job', jobFile);
      resumeFiles.forEach(file => {
        formData.append('resumes', file);
      });

      const response = await fetch('http://localhost:8007/upload_analyze', {
        method: 'POST',
        body: formData
      });

      const data: ApiResponse = await response.json();
      console.log('Received data:', data);
      
      if (data.error) {
        alert('Ошибка: ' + data.error);
        return;
      }

      console.log('Setting results:', data.results);
      setResults(data.results || []);
    } catch (error) {
      console.error('Ошибка анализа файлов:', error);
      alert('Ошибка анализа файлов. Проверьте подключение к серверу и настройки API.');
    } finally {
      setIsAnalyzing(false);
    }
  };



  return (
    <div>
      <h1>Анализ резюме</h1>
      
      <div style={{ marginBottom: '20px', padding: '15px', border: '2px dashed #ccc', borderRadius: '8px' }}>
        <h3>Загрузка файлов</h3>
        
        <div className="field">
          <label><strong>Описание вакансии (файл)</strong></label>
          <div style={{ fontSize: '12px', color: '#666', marginBottom: '5px' }}>
            Поддерживаемые форматы: PDF, DOC, DOCX, RTF, TXT, HTML, ODT, Pages
          </div>
          <div className="row">
            <input
              type="file"
              ref={jobFileInputRef}
              onChange={handleJobFileUpload}
              accept=".pdf,.doc,.docx,.txt,.rtf,.odt,.pages,.html,.htm"
              style={{ marginRight: '10px' }}
            />
            {jobFile && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <span style={{ color: 'green' }}>✓ {jobFile.name}</span>
                <button className="link" onClick={clearJobFile}>Очистить</button>
              </div>
            )}
          </div>
        </div>

        <div className="field">
          <label><strong>Резюме (файлы)</strong></label>
          <div style={{ fontSize: '12px', color: '#666', marginBottom: '5px' }}>
            Поддерживаемые форматы: PDF, DOC, DOCX, RTF, TXT, HTML, ODT, Pages
          </div>
          <div className="row">
            <input
              type="file"
              ref={resumeFileInputRef}
              onChange={handleResumeFilesUpload}
              accept=".pdf,.doc,.docx,.txt,.rtf,.odt,.pages,.html,.htm"
              multiple
              style={{ marginRight: '10px' }}
            />
            {resumeFiles.length > 0 && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <span style={{ color: 'green' }}>✓ {resumeFiles.length} файл(ов)</span>
                <button className="link" onClick={clearResumeFiles}>Очистить</button>
              </div>
            )}
          </div>
          {resumeFiles.length > 0 && (
            <div style={{ marginTop: '5px', fontSize: '12px', color: '#666' }}>
              {resumeFiles.map((file, index) => (
                <div key={index}>• {file.name}</div>
              ))}
            </div>
          )}
        </div>

        <button 
          className="start" 
          onClick={analyzeFiles}
          disabled={isAnalyzing || !jobFile || resumeFiles.length === 0}
          style={{ marginTop: '10px' }}
        >
          {isAnalyzing ? 'Анализируем...' : 'Анализировать'}
        </button>
      </div>


      <div className="results">
        <h3>Результаты: {results.length > 0 ? `(${results.length})` : ''}</h3>
        <table>
          <thead>
            <tr>
              <th>Имя</th>
              <th>Скор</th>
            </tr>
          </thead>
          <tbody>
            {isAnalyzing ? (
              <tr>
                <td colSpan={2} className="loading-message">
                   Анализируем резюме...
                </td>
              </tr>
            ) : results.length > 0 ? (
              results.map((result, index) => (
                <tr key={index}>
                  <td>{result.name || 'Unknown'}</td>
                  <td>{result.score?.toString() || '0'}</td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={2} style={{ textAlign: 'center', color: '#666' }}>
                  Результаты анализа появятся здесь...
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default ResumeAnalysis;
