import React, { useState, useRef, useCallback } from 'react';

interface WebSocketMessage {
  type: string;
  segment_text?: string;
  improved_text?: string;
  question?: string;
  question_number?: number;
  total_questions?: number;
  topic_display?: string;  // Добавляем поле для отображения темы
  improved_answer?: string;
  next_question?: {
    question: string;
    question_number: number;
    total_questions: number;
    topic_display?: string;  // Добавляем поле для отображения темы в следующем вопросе
  };
  total_answers?: number;
  summary?: string;
  evaluation?: string;
  message?: string;
  reset_timer?: boolean;  // Добавляем поле для сброса таймера
  final_report?: string;  // Добавляем поле для финального отчета
  feedback_message?: string;  // Добавляем поле для сообщений о динамических вопросах
  total_questions_updated?: number;  // Добавляем поле для обновленного количества вопросов
}

const SpeechRecognition: React.FC = () => {
  const [isConnected, setIsConnected] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [isInterviewMode, setIsInterviewMode] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isWaitingForAnswer, setIsWaitingForAnswer] = useState(false);
  const [status, setStatus] = useState('Добро пожаловать в AI систему HR! Вам будет задано несколько вопросов. Для каждого вопроса у вас есть время внимательно его прочитать и подготовиться к ответу. Когда будете готовы, нажимайте кнопку "Начать запись".');
  const [statusType, setStatusType] = useState<'connected' | 'disconnected' | 'recording'>('connected');
  const [accumulatedText, setAccumulatedText] = useState('');
  const [improvedText, setImprovedText] = useState('Улучшенный текст(с помощью LLM) появится здесь...');
  const [currentQuestion, setCurrentQuestion] = useState<string>('');
  const [questionCounter, setQuestionCounter] = useState<string>('');
  const [showQuestion, setShowQuestion] = useState(false);
  const [showSpinner, setShowSpinner] = useState(false);
  const [finalReport, setFinalReport] = useState<string | null>(null);
  const [feedbackMessage, setFeedbackMessage] = useState<string>('');

  const wsRef = useRef<WebSocket | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);

  const updateStatus = useCallback((text: string, type: 'connected' | 'disconnected' | 'recording') => {
    setStatus(text);
    setStatusType(type);
  }, []);

  const handleResult = useCallback((data: WebSocketMessage) => {
    console.log('Обрабатываем результат, тип:', data.type);
    console.log('Полные данные:', data);
    
    if (data.type === 'result') {
      console.log(' Обрабатываем результат распознавания');
      console.log(' Текст сегмента:', data.segment_text);
      
      if (data.segment_text) {
        console.log(' Добавляем текст к накопленному:', data.segment_text);
        setAccumulatedText(prev => {
          const newText = prev ? prev + ' | ' + data.segment_text : data.segment_text!;
          console.log(' Новый накопленный текст:', newText);
          return newText;
        });
      } else {
        console.log(' Нет текста сегмента для добавления');
      }
    }
    
    if (data.type === 'improved') {
      setImprovedText(data.improved_text || '');
      updateStatus('Подключено', 'connected');
      console.log('Gemini improved text:', data.improved_text);
    }
    
        if (data.type === 'question') {
          console.log(' Получен вопрос интервью:', data);
          setCurrentQuestion(data.question || '');
          // Use topic_display if available, otherwise fallback to question number
          const displayText = data.topic_display || `Вопрос ${data.question_number} (из 5-10)`;
          setQuestionCounter(displayText);
          setShowQuestion(true);
          setIsWaitingForAnswer(true);
      
      // НЕ сбрасываем таймер автоматически - только при нажатии кнопки "Начать запись"
    }
    
    if (data.type === 'processing_started') {
      console.log(' Начата обработка ответа');
      console.log(' isInterviewMode:', isInterviewMode);
      console.log(' Принудительно показываем спиннер');
      setIsProcessing(true);
      setShowSpinner(true);
      setIsRecording(false); // Останавливаем запись при начале обработки
      console.log(' Спиннер должен быть виден, запись остановлена');
    }
    
    if (data.type === 'answer_processed') {
      console.log(' Ответ обработан, показываем результат:', data);
      console.log(' WebSocket state после ответа:', wsRef.current?.readyState, 'isConnected:', isConnected);
      console.log(' Actual WebSocket connected:', wsRef.current?.readyState === WebSocket.OPEN);
      
      // ВСЕГДА скрываем спиннер при получении answer_processed
      console.log(' Принудительно скрываем спиннер');
      setShowSpinner(false);
      setIsProcessing(false);
      
      setIsWaitingForAnswer(false);
      setIsRecording(false); // Останавливаем запись при получении результата
      
      // Очищаем предыдущий текст
      setAccumulatedText('');
      setImprovedText('Улучшенный текст(с помощью LLM) появится здесь...');
      
      // Показываем улучшенный ответ
      setImprovedText(data.improved_answer || '');
      
      // Показываем сообщение о динамических вопросах, если есть
      if (data.feedback_message) {
        setFeedbackMessage(data.feedback_message);
        console.log(' Показываем сообщение о динамических вопросах:', data.feedback_message);
        // Автоматически скрываем сообщение через 7 секунд
        setTimeout(() => {
          setFeedbackMessage('');
        }, 7000);
      }
      
      // Обновляем счетчик вопросов, если количество изменилось
      if (data.total_questions_updated && data.next_question) {
        const displayText = data.next_question.topic_display || `Вопрос ${data.next_question.question_number} (из 5-10)`;
        setQuestionCounter(displayText);
        console.log(' Обновлен счетчик вопросов:', data.total_questions_updated);
      }
      
        // Сразу показываем следующий вопрос
        if (data.next_question) {
          console.log(' Показываем следующий вопрос:', data.next_question.question_number);
          setCurrentQuestion(data.next_question.question);
          // Use topic_display if available
          const displayText = data.next_question.topic_display || `Вопрос ${data.next_question.question_number} (из 5-10)`;
          setQuestionCounter(displayText);
          setShowQuestion(true);
        
        // НОВАЯ ЛОГИКА: Для 2-го вопроса и далее - ждем нажатия кнопки
        if (data.next_question.question_number >= 2) {
          setIsWaitingForAnswer(true); // Ждем нажатия кнопки
          setIsRecording(false); // НЕ автоматически продолжаем запись
          console.log(' Вопрос >=2: ждем нажатия кнопки');
          // Не показываем статус-подсказку на экране
        } else {
          setIsWaitingForAnswer(false); // Не ждем нажатия кнопки для первого вопроса
          setIsRecording(true); // Автоматически продолжаем запись
          console.log(' Первый вопрос: автоматическая запись');
          updateStatus('Слушаю ваш ответ...', 'recording');
        }
      }
    }
    
    if (data.type === 'interview_finished') {
      console.log(' Интервью завершено:', data);
      console.log(' Принудительно скрываем спиннер при завершении интервью');
      
      // Принудительно скрываем спиннер
      setShowSpinner(false);
      setIsProcessing(false);
      console.log(' Состояние спиннера сброшено: showSpinner=false, isProcessing=false');
      
      setIsWaitingForAnswer(false);
      setCurrentQuestion(' Интервью завершено!');
      setQuestionCounter('');
      setImprovedText('');
      setShowQuestion(false);
      setAccumulatedText('');
      setFeedbackMessage(''); // Очищаем сообщения о динамических вопросах
      
      // Сохраняем финальный отчет
      if (data.final_report) {
        setFinalReport(data.final_report);
      }
      
      setIsInterviewMode(false);
      updateStatus('Интервью завершено', 'connected');
    }
  }, [isInterviewMode, isProcessing, updateStatus]);

  const connect = useCallback(async () => {
    try {
      console.log(' Подключаемся к WebSocket...');
      updateStatus('Подключение...', 'recording');
      
      wsRef.current = new WebSocket('ws://localhost:8007/ws');
      
      wsRef.current.onopen = () => {
        console.log(' WebSocket подключен');
        setIsConnected(true);
        updateStatus('Подключено', 'connected');
        
        // Отправляем тестовое сообщение
        console.log(' Отправляем тестовое сообщение');
        wsRef.current?.send(JSON.stringify({action: "test", message: "Hello from React"}));
      };
      
      wsRef.current.onmessage = (event) => {
        console.log(' Получено WebSocket сообщение:', event.data);
        try {
          const data: WebSocketMessage = JSON.parse(event.data);
          console.log(' Распарсенные данные:', data);
          console.log(' Тип сообщения:', data.type);
          
          if (data.type === 'processing_started') {
            console.log(' ПОЛУЧЕНО СООБЩЕНИЕ processing_started!');
          }
          
          console.log(' Текст сегмента:', data.segment_text);
          handleResult(data);
        } catch (error) {
          console.error(' Ошибка парсинга WebSocket сообщения:', error);
        }
      };
      
      wsRef.current.onclose = () => {
        setIsConnected(false);
        updateStatus('Отключено', 'disconnected');
      };
      
      wsRef.current.onerror = (error) => {
        console.error('WebSocket error:', error);
        updateStatus('Ошибка подключения', 'disconnected');
      };
      
    } catch (error) {
      console.error('Connection error:', error);
      updateStatus('Ошибка: ' + (error as Error).message, 'disconnected');
    }
  }, [updateStatus, handleResult]);

  const startRecording = useCallback(async () => {
    try {
      console.log(' Начинаем запись...');
      
      if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
        throw new Error('WebSocket не подключен');
      }
      
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
        mediaRecorderRef.current.stop();
      }
      if (mediaStreamRef.current) {
        mediaStreamRef.current.getTracks().forEach(track => track.stop());
      }
      
      updateStatus('Запуск записи...', 'recording');
      
      // СБРАСЫВАЕМ ТАЙМЕР НА BACKEND ТОЛЬКО СЕЙЧАС
      console.log(' Сбрасываем таймер на backend при начале записи');
      wsRef.current.send(JSON.stringify({action: "reset_timer"}));
      
      // НОВОЕ: Активируем прослушивание для 2-го+ вопроса
      console.log(' Активируем прослушивание');
      wsRef.current.send(JSON.stringify({action: "activate_listening"}));
      
      // Отправляем команду на backend для запуска process_stream (только первый раз)
      console.log(' Отправляем команду start_recording');
      try {
        const message = JSON.stringify({action: "start_recording"});
        console.log(' Sending message:', message);
        console.log(' WebSocket state:', wsRef.current.readyState, 'OPEN=', WebSocket.OPEN);
        wsRef.current.send(message);
        console.log(' Message sent successfully');
      } catch (error) {
        console.error(' Error sending message:', error);
      }
      
      
      setAccumulatedText('');
      setImprovedText('');
      
      mediaStreamRef.current = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate: 16000,
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true
        }
      });
      
      mediaRecorderRef.current = new MediaRecorder(mediaStreamRef.current, {
        mimeType: 'audio/webm;codecs=opus'
      });
      
      mediaRecorderRef.current.ondataavailable = (event) => {
        if (event.data.size > 0 && wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
          event.data.arrayBuffer().then(buffer => {
            wsRef.current!.send(buffer);
          });
        } else {
          console.warn(' Не отправляем чанк - размер:', event.data.size, 'WebSocket:', wsRef.current?.readyState);
        }
      };
      
      mediaRecorderRef.current.start(100);
      setIsRecording(true);
      // Не показываем статусовую надпись о записи
      
    } catch (error) {
      console.error('Recording start error:', error);
      updateStatus('Ошибка записи: ' + (error as Error).message, 'disconnected');
    }
  }, [updateStatus]);

  const stopRecording = useCallback(() => {
    console.log(' Останавливаем запись...');
    setIsRecording(false);
    
    if (mediaRecorderRef.current) {
      console.log(' Останавливаем MediaRecorder, состояние:', mediaRecorderRef.current.state);
      mediaRecorderRef.current.stop();
      mediaRecorderRef.current = null;
    }
    
    if (mediaStreamRef.current) {
      console.log(' Останавливаем MediaStream');
      mediaStreamRef.current.getTracks().forEach(track => track.stop());
      mediaStreamRef.current = null;
    }
  }, []);

  const startInterview = useCallback(() => {
    console.log(' Запускаем HR интервью...');
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      console.log(' WebSocket готов, отправляем команду start_interview');
      setIsInterviewMode(true);
      setFinalReport(null); // Сбрасываем предыдущий отчет
      wsRef.current.send(JSON.stringify({action: "start_interview"}));
      updateStatus('Режим HR интервью', 'recording');
    } else {
      console.error(' WebSocket не готов для интервью:', wsRef.current?.readyState);
    }
  }, [updateStatus]);

  return (
    <div>
      {/* Если есть финальный отчет — показываем только его */}
      {finalReport && (
        <div style={{
          marginTop: '10px',
          padding: '20px',
          backgroundColor: '#f0f8ff',
          borderRadius: '10px',
          border: '2px solid #007bff',
          boxShadow: '0 4px 6px rgba(0,0,0,0.1)'
        }}>
          <h2 style={{ 
            color: '#007bff', 
            marginBottom: '20px',
            textAlign: 'center',
            fontSize: '28px'
          }}>
             Результат интервью
          </h2>
          <div style={{ 
            fontSize: '18px', 
            lineHeight: '1.8', 
            whiteSpace: 'pre-wrap',
            color: '#333',
            backgroundColor: 'white',
            padding: '20px',
            borderRadius: '8px'
          }}>
            {finalReport}
          </div>
        </div>
      )}

      {/* Скрываем остальной интерфейс, если показан финальный отчет */}
      {!finalReport && (
        <div>
          <h1>AI HR интервьюер</h1>
          <div className={`status ${statusType}`}>{status}</div>
          <div style={{ display: 'flex', justifyContent: 'center', gap: '10px', margin: '20px 0' }}>
            {!isInterviewMode && !isConnected && (
              <button 
                className="start" 
                onClick={async () => {
                  await connect();
                  setTimeout(() => {
                    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
                      startInterview();
                    }
                  }, 500);
                }}
              >
                Подключиться и начать интервью
              </button>
            )}
          </div>

          {showQuestion && (
            <div className="interview-question">
              <h3> HR Интервьюер</h3>
              <div style={{ textAlign: 'center', fontSize: '16px', marginBottom: '15px', color: '#666' }}>
                {questionCounter}
              </div>
              <div style={{ fontSize: '24px', fontWeight: 'bold', lineHeight: '1.4', marginBottom: '15px' }}>
                {currentQuestion}
              </div>
              {isWaitingForAnswer && (
                <div style={{ marginTop: '10px', padding: '10px', background: '#fff3cd', borderRadius: '6px', fontSize: '14px' }}>
                  {isRecording 
                    ? " Говорите ваш ответ. Через 5 секунд молчания ответ будет автоматически обработан."
                    : "Когда будете готовы, нажимайте кнопку \"Начать запись\"."
                  }
                </div>
              )}
              {(() => {
                console.log(' Проверка показа кнопки:', { isInterviewMode, isWaitingForAnswer, isConnected, isRecording });
                return isInterviewMode && isWaitingForAnswer;
              })() && (
                <div style={{ display: 'flex', justifyContent: 'center', marginTop: '20px' }}>
                  {isRecording ? (
                    <div style={{ 
                      fontSize: '18px', 
                      padding: '12px 24px',
                      backgroundColor: '#ffc107',
                      color: '#212529',
                      border: 'none',
                      borderRadius: '8px',
                      fontWeight: 'bold'
                    }}>
                      Идет запись
                    </div>
                  ) : (
                    <button 
                      className="start" 
                      onClick={startRecording}
                      disabled={!isConnected}
                      style={{ 
                        fontSize: '18px', 
                        padding: '12px 24px',
                        backgroundColor: '#28a745',
                        color: 'white',
                        border: 'none',
                        borderRadius: '8px',
                        cursor: 'pointer'
                      }}
                    >
                      Начать запись
                    </button>
                  )}
                </div>
              )}
            </div>
          )}

          <div className="results">
            {accumulatedText ? (
              <div style={{ fontSize: '20px', lineHeight: '1.6', padding: '20px' }}>
                {accumulatedText}
              </div>
            ) : (
              <p>Ваш ответ появится здесь...</p>
            )}
          </div>

          <div className="results" style={{ marginTop: '20px', borderLeft: '4px solid #28a745' }}>
            <h3 style={{ color: '#28a745', marginBottom: '10px' }}> Улучшенный текст:</h3>
            <div style={{ fontSize: '18px', lineHeight: '1.6', padding: '15px', background: '#f8fff8', whiteSpace: 'pre-wrap' }}>
              {improvedText}
            </div>
          </div>

          {/* Feedback message for dynamic questions */}
          {feedbackMessage && (
            <div style={{ 
              marginTop: '20px', 
              padding: '15px', 
              backgroundColor: '#fff3cd', 
              border: '1px solid #ffeaa7', 
              borderRadius: '8px',
              color: '#856404'
            }}>
              <div style={{ fontSize: '16px', fontWeight: 'bold', marginBottom: '5px' }}>ℹ️ Информация:</div>
              <div style={{ fontSize: '14px' }}>{feedbackMessage}</div>
            </div>
          )}
        </div>
      )}

      {/* Spinner overlay */}
      <div className={`spinner-overlay ${showSpinner ? 'show' : ''}`}>
        <div className="spinner-container">
          <div className="spinner"></div>
          <div className="spinner-text">Ваш ответ обрабатывается...</div>
        </div>
      </div>
    </div>
  );
};

export default SpeechRecognition;
