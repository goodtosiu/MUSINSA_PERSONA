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
  
  // [수정] 서버 데이터 상태 관리
  const [recommendedProducts, setRecommendedProducts] = useState(null); 
  const [currentOutfitId, setCurrentOutfitId] = useState(null); // 셔플을 위한 Outfit ID 저장
  
  const [isLoading, setIsLoading] = useState(false);

    // [수정 완료] 누락되었던 prices 상태 추가
  const [prices, setPrices] = useState({
    outer: { min: '', max: '' },
    top: { min: '', max: '' },
    bottom: { min: '', max: '' },
    shoes: { min: '', max: '' },
    accessory: { min: '', max: '' }
  });

  // [수정 완료] 누락되었던 handlePriceChange 함수 추가
  const handlePriceChange = (category, type, value) => {
    setPrices(prev => ({
      ...prev,
      [category]: {
        ...prev[category],
        [type]: value
      }
    }));
  };

  // 퀴즈 시작 핸들러
  const handleStart = () => {
    setStep('question');
    setCurrentIdx(0);
    setScores(Object.fromEntries(personas.map(p => [p, 0])));
    setHistory([]);
    setRecommendedProducts(null);
    setCurrentOutfitId(null); // 초기화
  };

  // [수정] Flask에서 추천 데이터 가져오는 함수
  const fetchRecommendations = async () => {
    setIsLoading(true);
    try {
      const priceParams = Object.keys(prices).map(cat => 
        `min_${cat}=${prices[cat].min}&max_${cat}=${prices[cat].max}`
      ).join('&');

      const url = `http://127.0.0.1:5000/api/products?persona=${result}&${priceParams}`;
      const res = await fetch(url);
      
      if (!res.ok) throw new Error("서버 응답 에러");
      
      const data = await res.json();

      // 2. 변경된 데이터 구조 처리 ({ current_outfit_id, items })
      if (data.items) {
        setRecommendedProducts(data.items); // 상품 리스트 저장
        setCurrentOutfitId(data.current_outfit_id); // 셔플용 ID 저장
        setStep('collage');
      } else {
        alert("추천 상품을 불러오는데 문제가 발생했습니다.");
      }

    } catch (err) {
      console.error(err);
      alert("서버 연결에 실패했습니다. Flask 서버가 실행 중인지 확인해주세요.");
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
    } else {
      setStep('main');
    }
  };

  return (
    <div className="App">
      {/* 메인 화면 */}
      {step === 'main' && (
        <div className="main-container fade-in">
          <div className="content-wrapper">
            <h2 className="top-title">패션 페르소나 찾기</h2>
            <h1 className="main-title">
              <span className="brand">MUSINSA</span>
              <span className="separator"> X </span>
              <span className="brand">PERSONA</span>
            </h1>
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

      {/* 질문 화면 (진행 바 통합 버전) */}
      {step === 'question' && (
        <div className="question-container fade-in">
          {/* 상단 진행 바 영역 */}
          <div className="progress-area">
            <div className="progress-bar">
              <div 
                className="progress" 
                style={{ width: `${((currentIdx + 1) / questions.length) * 100}%` }}
              ></div>
            </div>
            <p className="q-count">
              <span className="current">{currentIdx + 1}</span> / {questions.length}
            </p>
          </div>

          <h2 className="question-text">{questions[currentIdx].q}</h2>
          
          <div className="answer-group">
            {questions[currentIdx].a.map((ans, i) => (
              <button key={i} className="ans-btn" onClick={() => handleAnswer(ans.score)}>
                {ans.text}
              </button>
            ))}
          </div>
          <button className="back-btn" onClick={handleBack}>이전 질문으로</button>
        </div>
      )}

      {/* STEP 1: 결과 설명 창 */}
      {step === 'result' && (
        <div className="result-container fade-in" style={{ maxWidth: '800px', margin: '80px auto', padding: '40px', background: 'rgba(255,255,255,0.05)', borderRadius: '20px', textAlign: 'center' }}>
          <p className="result-label">당신의 페르소나는</p>
          <h1 className="result-title" style={{ fontSize: '3.5rem', margin: '20px 0' }}>{result}</h1>
          <p className="persona-desc" style={{ marginBottom: '40px', fontSize: '1.2rem', lineHeight: '1.8', color: '#ccc' }}>
            {personaDescriptions[result] || "당신만의 특별한 스타일을 탐구해보세요."}
          </p>
          <div className="btn-group" style={{ display: 'flex', justifyContent: 'center', gap: '20px' }}>
            <button className="start-btn" onClick={() => setStep('price_setting')}>확인</button>
            <button className="secondary-btn" onClick={() => setStep('main')}>다시하기</button>
          </div>
        </div>
      )}

      {/* STEP 2: 가격 카테고리 설정 창 */}
      {step === 'price_setting' && (
        <div className="price-setting-container fade-in" style={{ maxWidth: '700px', margin: '60px auto', padding: '30px', background: 'rgba(255,255,255,0.05)', borderRadius: '25px', border: '1px solid rgba(255,255,255,0.1)' }}>
          <h2 style={{ marginBottom: '10px', color: '#fff' }}>예산 설정</h2>
          <p style={{ color: '#888', marginBottom: '25px' }}>각 카테고리별로 원하는 가격대를 입력해주세요.</p>
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
            {Object.keys(prices).map((cat) => (
              <div key={cat} style={{ display: 'flex', alignItems: 'center', gap: '12px', background: 'rgba(0,0,0,0.3)', padding: '12px 20px', borderRadius: '12px' }}>
                <span style={{ width: '90px', color: '#eee', fontWeight: 'bold', fontSize: '1rem', textAlign: 'left' }}>
                  {cat === 'outer' ? '아우터' : cat === 'top' ? '상의' : cat === 'bottom' ? '하의' : cat === 'shoes' ? '신발' : '액세서리'}
                </span>
                <input 
                  type="number" 
                  placeholder="최소"
                  value={prices[cat].min}
                  step="5000"
                  onChange={(e) => handlePriceChange(cat, 'min', e.target.value)}
                  style={{ flex: 1, padding: '10px', borderRadius: '8px', border: '1px solid #444', background: '#222', color: '#fff', fontSize: '0.9rem' }}
                />
                <span style={{ color: '#666' }}>~</span>
                <input 
                  type="number" 
                  placeholder="최대"
                  value={prices[cat].max}
                  step="5000"
                  onChange={(e) => handlePriceChange(cat, 'max', e.target.value)}
                  style={{ flex: 1, padding: '10px', borderRadius: '8px', border: '1px solid #444', background: '#222', color: '#fff', fontSize: '0.9rem' }}
                />
              </div>
            ))}
          </div>

          <div className="btn-group" style={{ marginTop: '30px', display: 'flex', justifyContent: 'center', gap: '20px' }}>
            <button className="start-btn" onClick={fetchRecommendations} disabled={isLoading}>
              {isLoading ? "분석 중..." : "추천 상품 확인하기"}
            </button>
            <button className="secondary-btn" onClick={() => setStep('main')}>다시하기</button>
          </div>
        </div>
      )}

      {/* 콜라주 페이지 */}
      {step === 'collage' && recommendedProducts && (
        <CollagePage 
          result={result} 
          products={recommendedProducts} 
          currentOutfitId={currentOutfitId} // [추가] 셔플을 위해 ID 전달
          onBackToMain={() => setStep('main')}
          onBackToResult={() => setStep('price_setting')}
        />
      )}
    </div>
  );
}

export default App;