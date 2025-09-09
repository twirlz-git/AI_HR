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
  const [jobDescription, setJobDescription] = useState('');
  const [resumes, setResumes] = useState<string[]>(['', '']);
  const [results, setResults] = useState<AnalysisResult[]>([]);
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  const addResumeField = () => {
    setResumes([...resumes, '']);
  };

  const updateResume = (index: number, value: string) => {
    const newResumes = [...resumes];
    newResumes[index] = value;
    setResumes(newResumes);
  };

  const analyzeText = async () => {
    const filteredResumes = resumes.filter(resume => resume.trim());
    
    if (!jobDescription.trim() || !filteredResumes.length) {
      alert('Введите описание вакансии и хотя бы одно резюме.');
      return;
    }

    setIsAnalyzing(true);
    setResults([]);

    try {
      const response = await fetch('http://localhost:8007/analyze_resumes', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          job_description: jobDescription, 
          resumes: filteredResumes 
        })
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
      console.error('Ошибка анализа резюме:', error);
      alert('Ошибка анализа резюме. Проверьте подключение к серверу и настройки API.');
    } finally {
      setIsAnalyzing(false);
    }
  };


  return (
    <div>
      <h1>📄 Анализ резюме</h1>
      

      <div className="field">
        <label><strong>Описание вакансии</strong></label>
        <textarea
          value={jobDescription}
          onChange={(e) => setJobDescription(e.target.value)}
          placeholder="Вставьте текст вакансии здесь..."
        />
      </div>


      <div className="row">
        <button className="link" onClick={addResumeField}>
          Добавить резюме
        </button>
        <button 
          className="start" 
          onClick={analyzeText}
          disabled={isAnalyzing}
        >
          {isAnalyzing ? 'Анализируем...' : 'Анализировать'}
        </button>
      </div>

      <div className="field">
        {resumes.map((resume, index) => (
          <div key={index} className="field">
            <label><strong>Резюме {index + 1}</strong></label>
            <textarea
              className="small"
              value={resume}
              onChange={(e) => updateResume(index, e.target.value)}
              placeholder="Вставьте текст резюме..."
            />
          </div>
        ))}
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
                  🔄 Анализируем резюме...
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
