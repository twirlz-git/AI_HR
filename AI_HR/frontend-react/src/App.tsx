import React, { useState } from 'react';
import './App.css';
import SpeechRecognition from './components/SpeechRecognition';
import ResumeAnalysis from './components/ResumeAnalysis';

const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'stt' | 'resume'>('stt');

  return (
    <div className="App">
      <div className="tabs">
        <button 
          className={`tab-btn ${activeTab === 'stt' ? 'active' : ''}`}
          onClick={() => setActiveTab('stt')}
        >
          Интервью
        </button>
        <button 
          className={`tab-btn ${activeTab === 'resume' ? 'active' : ''}`}
          onClick={() => setActiveTab('resume')}
        >
          Анализ резюме
        </button>
      </div>
      
      <div className="container">
        {activeTab === 'stt' ? <SpeechRecognition /> : <ResumeAnalysis />}
      </div>
    </div>
  );
};

export default App;