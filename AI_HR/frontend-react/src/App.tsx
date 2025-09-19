import React, { useEffect, useState } from 'react';
import './App.css';
import SpeechRecognition from './components/SpeechRecognition';
import ResumeAnalysis from './components/ResumeAnalysis';

type Page = 'home' | 'interview' | 'analyse';

const getPageFromHash = (): Page => {
  const h = (window.location.hash || '').toLowerCase();
  if (h.includes('interview')) return 'interview';
  if (h.includes('analyse')) return 'analyse';
  return 'home';
};

const App: React.FC = () => {
  const [page, setPage] = useState<Page>(getPageFromHash());

  useEffect(() => {
    const onHash = () => setPage(getPageFromHash());
    window.addEventListener('hashchange', onHash);
    return () => window.removeEventListener('hashchange', onHash);
  }, []);

  const Logo: React.FC = () => (
    <div
      aria-label="AI HR"
      style={{
        width: 36,
        height: 36,
        borderRadius: 8,
        background: 'linear-gradient(135deg,#007bff,#28a745)',
        color: '#fff',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontWeight: 700,
        letterSpacing: 0.5,
        cursor: 'pointer'
      }}
      onClick={() => (window.location.hash = '/')}
      title="На главную"
    >
      AI
    </div>
  );

  const Header: React.FC<{ title: string }> = ({ title }) => (
    <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: 16 }}>
      <Logo />
      <h2 style={{ margin: 0 }}>{title}</h2>
    </div>
  );

  if (page === 'home') {
    return (
      <div
        style={{
          position: 'fixed',
          inset: 0,
          width: '100vw',
          height: '100vh',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          padding: 0,
          background:
            'radial-gradient(1200px 600px at 10% -10%, rgba(0, 123, 255, 0.12), transparent 60%),' +
            'radial-gradient(900px 500px at 110% 10%, rgba(40, 167, 69, 0.12), transparent 60%),' +
            'linear-gradient(180deg, #f7faff 0%, #ffffff 100%)'
        }}
      >
        <div
          style={{
            width: '100%',
            maxWidth: 920,
            textAlign: 'center',
            padding: '28px 24px'
          }}
        >
          <h1 style={{ margin: 0, fontSize: 40 }}>AI HR агент</h1>
          <p style={{ color: '#444', fontSize: 18, marginTop: 12 }}>
            Умный и быстрый помощник для подбора и оценки кандидатов. Анализирует резюме, проводит
            интервью и формирует понятную обратную связь.
          </p>
          <div style={{ color: '#666', fontSize: 16, marginTop: 8 }}>
            <div>— Улучшаем ответы кандидата и считаем паузы автоматически</div>
            <div>— Поддерживаем живое интервью с распознаванием речи (Vosk)</div>
            <div>— Генерируем краткий отчет и рекомендации</div>
          </div>
          <div
            style={{
              display: 'flex',
              justifyContent: 'center',
              gap: 16,
              marginTop: 28
            }}
          >
            <button
              onClick={() => (window.location.hash = '/interview')}
              style={{
                padding: '14px 20px',
                fontSize: 16,
                background: '#28a745',
                color: '#fff',
                border: 'none',
                borderRadius: 10,
                cursor: 'pointer',
                minWidth: 200
              }}
            >
              Собеседование
            </button>
            <button
              onClick={() => (window.location.hash = '/analyse')}
              style={{
                padding: '14px 20px',
                fontSize: 16,
                background: '#007bff',
                color: '#fff',
                border: 'none',
                borderRadius: 10,
                cursor: 'pointer',
                minWidth: 200
              }}
            >
              Анализ резюме
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (page === 'interview') {
    return (
      <div
        style={{
          position: 'fixed',
          inset: 0,
          width: '100vw',
          height: '100vh',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: 8,
          padding: 16,
          overflowY: 'auto',
          background:
            'radial-gradient(1200px 600px at 10% -10%, rgba(0, 123, 255, 0.12), transparent 60%),' +
            'radial-gradient(900px 500px at 110% 10%, rgba(40, 167, 69, 0.12), transparent 60%),' +
            'linear-gradient(180deg, #f7faff 0%, #ffffff 100%)'
        }}
      >
        <Header title="Interview" />
        <div className="container">
          <SpeechRecognition />
        </div>
      </div>
    );
  }

  if (page === 'analyse') {
    return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        width: '100vw',
        height: '100vh',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: 8,
        padding: 16,
        overflowY: 'auto',
        background:
          'radial-gradient(1200px 600px at 10% -10%, rgba(0, 123, 255, 0.12), transparent 60%),' +
          'radial-gradient(900px 500px at 110% 10%, rgba(40, 167, 69, 0.12), transparent 60%),' +
          'linear-gradient(180deg, #f7faff 0%, #ffffff 100%)'
      }}
    >
      <Header title="Анализ резюме" />
      <div className="container" style={{ width: '100%', maxWidth: 800 }}>
        <ResumeAnalysis />
      </div>
    </div>
    );
  }

  return null;
};

export default App;