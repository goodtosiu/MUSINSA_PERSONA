import React, { useState } from 'react';
import './App.css';
import CollagePage from './CollagePage';
import { questions, personas, personaDescriptions } from './data'; 

function App() {
  const [step, setStep] = useState('main'); 
  const [currentIdx, setCurrentIdx] = useState(0);
  const [scores, setScores] = useState(Object.fromEntries(personas.map(p => [p, 0])));
  const [history, setHistory] = useState([]);
  const [result, setResult] = useState("");
  const [recommendedProducts, setRecommendedProducts] = useState(null); // 서버에서 받은 데이터 저장
  const [isLoading, setIsLoading] = useState(false); // 로딩 상태 추가

  // 퀴즈 시작 핸들러
  const handleStart = () => {
    setStep('question');
    setCurrentIdx(0);
    setScores(Object.fromEntries(personas.map(p => [p, 0])));
    setHistory([]);
    setRecommendedProducts(null);
  };

  // Flask에서 추천 데이터 가져오는 함수
  const fetchRecommendations = async () => {
    setIsLoading(true);
    try {
      const res = await fetch('http://localhost:5000/api/products');
      const data = await res.json();
      setRecommendedProducts(data); // { 상의: [], 바지: [], ... } 형태 저장
      setStep('collage');
    } catch (err) {
      console.error("Flask 통신 에러:", err);
      alert("서버 연결에 실패했습니다. Flask 서버가 켜져 있는지 확인해주세요.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleAnswer = (types) => {
    setHistory([...history, { ...scores }]);
    const newScores = { ...scores };
    types.forEach(type => { if (newScores[type] !== undefined) newScores[type]++; });
    setScores(newScores);

    if (currentIdx + 1 < questions.length) {
      setCurrentIdx(currentIdx + 1);
    } else {
      const sorted = Object.keys(newScores).sort((a, b) => newScores[b] - newScores[a]);
      setResult(sorted[0]);
      setStep('result');
    }
  };

  const handleBack = () => {
    if (currentIdx > 0) {
      setScores(history[history.length - 1]);
      setHistory(history.slice(0, -1));
      setCurrentIdx(currentIdx - 1);
    }
  };

  return (
    <div className="App">
      {step === 'main' && (
        <div className="main-container fade-in">
          <div className="content-wrapper">
            <h2 className="top-title">패션 인격 찾기</h2>
            <h1 className="main-title">LOOK × MBTI</h1>
            
            <div className="description">
              <p>총 8가지 문항으로 옷장 속 숨겨진 당신의</p>
              <p><strong>16가지 패션 페르소나를 찾아보세요</strong></p>
            </div>

            <button className="start-btn" onClick={handleStart}>
              테스트 시작
            </button>
          </div>
        </div>
      )}

      {step === 'question' && (
        <div className="question-container fade-in">
          <div className="progress-bar">
            <div className="progress" style={{ width: `${((currentIdx + 1) / questions.length) * 100}%` }}></div>
          </div>
          <p className="q-count">{currentIdx + 1} / {questions.length}</p>
          <h2 className="question-text">{questions[currentIdx].q}</h2>
          <div className="answer-group">
            {questions[currentIdx].a.map((ans, i) => (
              <button key={i} className="ans-btn" onClick={() => handleAnswer(ans.score)}>{ans.text}</button>
            ))}
          </div>
          <button className="back-btn" onClick={handleBack}>이전 질문으로</button>
        </div>
      )}

      {step === 'result' && (
        <div className="result-container fade-in">
          <p className="result-label">당신의 페르소나는</p>
          <h1 className="result-title">{result}</h1>
          <p className="persona-desc">
            {personaDescriptions[result] || "당신만의 특별한 스타일을 탐구해보세요."}
          </p>
          <div className="btn-group">
            <button 
              className="start-btn" 
              onClick={fetchRecommendations} 
              disabled={isLoading}
            >
              {isLoading ? "스타일 분석 중..." : "추천 상품 확인하기"}
            </button>
            <button className="secondary-btn" onClick={() => setStep('main')}>
              다시하기
            </button>
          </div>
        </div>
      )}

      {step === 'collage' && recommendedProducts && (
        <CollagePage 
          result={result} 
          products={recommendedProducts} // Flask에서 받은 데이터 직접 전달
          onBackToMain={() => setStep('main')}
        />
      )}
    </div>
  );
}

export default App;