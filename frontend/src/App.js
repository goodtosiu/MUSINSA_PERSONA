import React, { useState, useEffect } from 'react';
import './App.css';
import CollagePage from './CollagePage';
import { step1Questions, step2Groups, personaDescriptions } from './data'; 

function App() {
  const [step, setStep] = useState('main'); 
  const [currentIdx, setCurrentIdx] = useState(0);
  const [history, setHistory] = useState([]);
  
  const [typeScores, setTypeScores] = useState({ A: 0, B: 0, C: 0, D: 0 });
  const [personaScores, setPersonaScores] = useState({});
  const [selectedType, setSelectedType] = useState(null);
  const [result, setResult] = useState("");

  const [recommendedProducts, setRecommendedProducts] = useState(null); 
  const [currentOutfitId, setCurrentOutfitId] = useState(null); 
  const [serverPriceRanges, setServerPriceRanges] = useState(null);
  const [isLoading, setIsLoading] = useState(false);

  // 1. 가격 필터링 반영: app.py 규격에 맞춰 키값을 'acc'로 관리
  const [prices, setPrices] = useState({
    outer: { min: '', max: '' },
    top: { min: '', max: '' },
    bottom: { min: '', max: '' },
    shoes: { min: '', max: '' },
    acc: { min: '', max: '' } // accessory 대신 acc 사용
  });

  const isAnyPriceError = Object.keys(prices).some((cat) => {
    const range = serverPriceRanges ? serverPriceRanges[cat] : null;
    if (!range) return false;
    const isMinErr = prices[cat].min !== '' && Number(prices[cat].min) > range.max;
    const isMaxErr = prices[cat].max !== '' && Number(prices[cat].max) < range.min;
    return isMinErr || isMaxErr;
  });

  const handlePriceChange = (category, type, value) => {
    setPrices(prev => ({ ...prev, [category]: { ...prev[category], [type]: value } }));
  };

  useEffect(() => {
    const fetchInitialRanges = async () => {
      try {
        const res = await fetch('http://127.0.0.1:5000/api/products?persona=아메카지');
        const data = await res.json();
        if (data.price_ranges) {
          setServerPriceRanges(data.price_ranges);
        }
      } catch (err) {
        console.error("초기 가격 범위를 가져오는데 실패했습니다.", err);
      }
    };
    fetchInitialRanges();
  }, []);

  const handleAnswer = (answer) => {
    setHistory([...history, { typeScores: {...typeScores}, personaScores: {...personaScores}, currentIdx, selectedType, step }]);

    if (step === 'step1') {
      const newScores = { ...typeScores, [answer.type]: typeScores[answer.type] + 1 };
      setTypeScores(newScores);
      if (currentIdx + 1 < step1Questions.length) {
        setCurrentIdx(currentIdx + 1);
      } else {
        const finalType = Object.keys(newScores).reduce((a, b) => newScores[a] >= newScores[b] ? a : b);
        setSelectedType(finalType);
        setCurrentIdx(0);
        setStep('step2');
      }
    } else if (step === 'step2') {
      const targetPersona = answer.res;
      const newPersonaScores = { ...personaScores, [targetPersona]: (personaScores[targetPersona] || 0) + 1 };
      setPersonaScores(newPersonaScores);
      const currentGroupQuestions = step2Groups[selectedType].questions;
      if (currentIdx + 1 < currentGroupQuestions.length) {
        setCurrentIdx(currentIdx + 1);
      } else {
        const finalResult = Object.keys(newPersonaScores).reduce((a, b) => newPersonaScores[a] >= newPersonaScores[b] ? a : b);
        setResult(finalResult);
        setStep('result');
      }
    }
  };

  const goBack = () => {
    if (history.length === 0) { setStep('main'); return; }
    const last = history[history.length - 1];
    setTypeScores(last.typeScores);
    setPersonaScores(last.personaScores);
    setCurrentIdx(last.currentIdx);
    setSelectedType(last.selectedType);
    setStep(last.step);
    setHistory(history.slice(0, -1));
  };

  // 2. 가격 필터링을 app.py API 규격에 맞춰 전송
  const fetchRecommendations = async () => {
    setIsLoading(true);
    try {
      // app.py가 기대하는 min_카테고리, max_카테고리 형태로 쿼리 생성
      const queryParams = new URLSearchParams({ persona: result });
      Object.keys(prices).forEach(cat => {
        if (prices[cat].min) queryParams.append(`min_${cat}`, prices[cat].min);
        if (prices[cat].max) queryParams.append(`max_${cat}`, prices[cat].max);
      });

      const res = await fetch(`http://127.0.0.1:5000/api/products?${queryParams.toString()}`);
      const data = await res.json();

      if (data.items) {
        setRecommendedProducts(data.items); 
        setCurrentOutfitId(data.current_outfit_id); 
        setStep('collage');
      }
    } catch (err) {
      console.error(err);
      alert("서버 연결에 실패했습니다.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="App">
      {step === 'main' && (
        <div className="main-container fade-in">
          <div className="content-wrapper">
            <h2 className="top-title">패션 인격 찾기</h2>
            <h1 className="main-title">
              <span className="brand">MUSINSA</span>
              <span className="separator"> X </span>
              <span className="brand">PERSONA</span>
            </h1>
            <div className="description">
              <p>총 8가지 문항으로 옷장 속 숨겨진 당신의</p>
              <p><strong>16가지 패션 페르소나를 찾아보세요</strong></p>
            </div>
            <button className="start-btn" onClick={() => { setStep('step1'); setCurrentIdx(0); }}>
              테스트 시작
            </button>
          </div>
        </div>
      )}

      {(step === 'step1' || step === 'step2') && (
        <div className="question-container fade-in">
          <div className="progress-bar">
            <div className="progress" style={{ width: `${((step === 'step1' ? currentIdx : currentIdx + 4) / 8) * 100}%` }}></div>
          </div>
          <p className="q-count">Q. {step === 'step1' ? currentIdx + 1 : currentIdx + 5} / 8</p>
          <h2 className="question-text">
            {step === 'step1' ? step1Questions[currentIdx].q : step2Groups[selectedType].questions[currentIdx].q}
          </h2>
          <div className="answer-group">
            {(step === 'step1' ? step1Questions[currentIdx].a : step2Groups[selectedType].questions[currentIdx].a).map((a, i) => (
              <button key={i} className="ans-btn" onClick={() => handleAnswer(a)}>{a.text}</button>
            ))}
          </div>
          <button className="back-btn" onClick={goBack}>이전 질문으로</button>
        </div>
      )}

      {step === 'result' && (
        <div className="result-container fade-in">
          <p className="result-label">당신의 페르소나는</p>
          <h1 className="result-title-main">{result}</h1>
          <p className="persona-desc">{personaDescriptions[result]}</p>
          <div className="btn-group-center">
            <button className="start-btn" onClick={() => setStep('price_setting')}>확인</button>
            <button className="secondary-btn" onClick={() => window.location.reload()}>다시하기</button>
          </div>
        </div>
      )}

      {step === 'price_setting' && (
        <div className="price-setting-container fade-in">
          <h2 className="price-title">예산 설정</h2>
          <p className="price-subtitle">각 카테고리별로 원하는 가격대를 입력해주세요.</p>
          <div className="price-input-list">
            {Object.keys(prices).map((cat) => {
              const range = serverPriceRanges ? serverPriceRanges[cat] : null;
              const isMinError = range && prices[cat].min !== '' && Number(prices[cat].min) > range.max;
              const isMaxError = range && prices[cat].max !== '' && Number(prices[cat].max) < range.min;
              const hasError = isMinError || isMaxError;

              return (
                <div key={cat} className="price-item-wrapper">
                  <div className={`price-input-row ${hasError ? 'error-border' : ''}`}>
                    <span className="price-cat-label">
                      {cat === 'outer' ? '아우터' : cat === 'top' ? '상의' : cat === 'bottom' ? '하의' : cat === 'shoes' ? '신발' : '액세서리'}
                    </span>
                    <input type="number" className="price-input-field" placeholder={range ? `${range.min.toLocaleString()}` : "최소"} value={prices[cat].min} onChange={(e) => handlePriceChange(cat, 'min', e.target.value)} />
                    <span className="price-tilde">~</span>
                    <input type="number" className="price-input-field" placeholder={range ? `${range.max.toLocaleString()}` : "최대"} value={prices[cat].max} onChange={(e) => handlePriceChange(cat, 'max', e.target.value)} />
                  </div>
                  {hasError && range && (
                    <p className="error-message">{range.min.toLocaleString()}원 ~ {range.max.toLocaleString()}원 사이만 가능합니다.</p>
                  )}
                </div>
              );
            })}
          </div>
          <div className="btn-group-center mt-30">
            <button className="start-btn" onClick={fetchRecommendations} disabled={isLoading || isAnyPriceError}>
              {isLoading ? "분석 중..." : "추천 상품 확인하기"}
            </button>
            <button className="secondary-btn" onClick={() => setStep('main')}>다시하기</button>
          </div>
        </div>
      )}

      {step === 'collage' && recommendedProducts && (
        <CollagePage result={result} products={recommendedProducts} currentOutfitId={currentOutfitId} onBackToMain={() => setStep('main')} onBackToResult={() => setStep('price_setting')} />
      )}
    </div>
  );
}

export default App;