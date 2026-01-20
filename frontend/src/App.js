import React, { useState, useEffect } from 'react';
import './App.css';
import CollagePage from './CollagePage';
import PurchasePage from './PurchasePage';
// personaBackMap은 배경 경로를 생성하기 위해 import합니다.
import { step1Questions, step2Groups, personaDescriptions, personaBackMap } from './data'; 
const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://127.0.0.1:5000';

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

  // [추가] PurchasePage로 넘겨줄 최종 선택 아이템 상태
  const [finalSelectedItems, setFinalSelectedItems] = useState([]);

  const [prices, setPrices] = useState({
    outer: { min: '', max: '' },
    top: { min: '', max: '' },
    bottom: { min: '', max: '' },
    shoes: { min: '', max: '' },
    acc: { min: '', max: '' }
  });

  useEffect(() => {
    const fetchInitialRanges = async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/api/price-ranges`);
        const data = await res.json();
        if (data && !data.error) {
          setServerPriceRanges(data);
        }
      } catch (err) {
        console.error("가격 범위를 가져오는데 실패했습니다.", err);
      }
    };
    fetchInitialRanges();
  }, []);

  const isAnyPriceError = Object.keys(prices).some((cat) => {
    const range = serverPriceRanges ? serverPriceRanges[cat] : null;
    if (!range) return false;
    const minVal = prices[cat].min !== '' ? Number(prices[cat].min) : null;
    const maxVal = prices[cat].max !== '' ? Number(prices[cat].max) : null;
    const isMinErr = minVal !== null && minVal >= range.max;
    const isMaxErr = maxVal !== null && maxVal <= range.min;
    const isCrossErr = (minVal !== null && maxVal !== null) && minVal > maxVal;
    return isMinErr || isMaxErr || isCrossErr;
  });

  const handlePriceChange = (category, type, value) => {
    const numericValue = value === '' ? '' : Math.max(0, Number(value));
    setPrices(prev => ({ ...prev, [category]: { ...prev[category], [type]: value } }));
  };

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

  const fetchRecommendations = async () => {
    setIsLoading(true);
    try {
      const queryParams = new URLSearchParams({ persona: result });
      Object.keys(prices).forEach(cat => {
        if (prices[cat].min) queryParams.append(`min_${cat}`, prices[cat].min);
        if (prices[cat].max) queryParams.append(`max_${cat}`, prices[cat].max);
      });
      const res = await fetch(`${API_BASE_URL}/api/products?${queryParams.toString()}`);
      const data = await res.json();
      if (data.items) {
        setRecommendedProducts(data.items); 
        setCurrentOutfitId(data.current_outfit_id); 
        setStep('collage');
      }
    } catch (err) {
      alert("데이터 로드 실패");
    } finally {
      setIsLoading(false);
    }
  };

  // [추가] 콜라주 페이지에서 구매하기를 눌렀을 때 실행될 함수
  const handleGoToPurchase = (items) => {
    setFinalSelectedItems(items);
    setStep('purchase');
  };

  const resetAll = () => {
    setStep('main');
    setCurrentIdx(0);
    setHistory([]);
    setTypeScores({ A: 0, B: 0, C: 0, D: 0 });
    setPersonaScores({});
    setSelectedType(null);
    setResult("");
    setRecommendedProducts(null);
    setCurrentOutfitId(null);
    setFinalSelectedItems([]); // 초기화 시 아이템도 비움
    setPrices({
      outer: { min: '', max: '' },
      top: { min: '', max: '' },
      bottom: { min: '', max: '' },
      shoes: { min: '', max: '' },
      acc: { min: '', max: '' }
    });
  };

  return (
    <div className="App">
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
          <button className="back-btn mt-15" onClick={() => setStep('descriptions')}>
            모든 페르소나 설명 보기
          </button>
        </div>
      )}

      {step === 'descriptions' && (
        <div className="question-container fade-in">
          <h2 className="price-title">페르소나 가이드</h2>
          <div className="desc-list-container">
            {Object.entries(personaDescriptions).map(([name, desc]) => (
              <div key={name} className="desc-item">
                <strong className="desc-item-name">{name}</strong>
                <p className="desc-item-text">{desc}</p>
              </div>
            ))}
          </div>
          <button className="back-btn mt-30" onClick={() => setStep('result')}>
            결과로 돌아가기
          </button>
        </div>
      )}

      {step === 'price_setting' && (
        <div className="price-setting-container fade-in">
          <h2 className="price-title">예산 설정</h2>
          <p className="price-subtitle">각 카테고리별로 원하는 가격대를 입력해주세요.</p>
          <div className="price-input-list">
            {Object.keys(prices).map((cat) => {
              const range = serverPriceRanges ? serverPriceRanges[cat] : null;
              const minVal = prices[cat].min !== '' ? Number(prices[cat].min) : null;
              const maxVal = prices[cat].max !== '' ? Number(prices[cat].max) : null;
              const isMinErr = range && minVal !== null && minVal >= range.max;
              const isMaxErr = range && maxVal !== null && maxVal <= range.min;
              const isCrossErr = (minVal !== null && maxVal !== null) && minVal > maxVal;
              const hasError = isMinErr || isMaxErr || isCrossErr;
              return (
                <div key={cat} className="price-item-wrapper">
                  <div className={`price-input-row ${hasError ? 'error-border' : ''}`}>
                    <span className="price-cat-label">
                      {cat === 'outer' ? '아우터' : cat === 'top' ? '상의' : cat === 'bottom' ? '하의' : cat === 'shoes' ? '신발' : '액세서리'}
                    </span>
                    <input type="number" min = "0" step="5000" className="price-input-field" placeholder={range ? `${range.min.toLocaleString()}` : "계산 중..."} value={prices[cat].min} onChange={(e) => handlePriceChange(cat, 'min', e.target.value)} />
                    <span className="price-tilde">~</span>
                    <input type="number" min = "0" step="5000" className="price-input-field" placeholder={range ? `${range.max.toLocaleString()}` : "계산 중..."} value={prices[cat].max} onChange={(e) => handlePriceChange(cat, 'max', e.target.value)} />
                  </div>
                  {hasError && range && (
                    <p className="error-message">
                      {isCrossErr ? "최소 가격이 최대 가격보다 클 수 없습니다." : `${range.min.toLocaleString()}원 ~ ${range.max.toLocaleString()}원 사이로 입력해주세요.`}
                    </p>
                  )}
                </div>
              );
            })}
          </div>
          <div className="btn-group-center mt-30">
            <button className="start-btn" onClick={fetchRecommendations} disabled={isLoading || isAnyPriceError || !serverPriceRanges}>
              {isLoading ? "분석 중..." : "추천 상품 확인하기"}
            </button>
            <button className="secondary-btn" onClick={() => {
              window.location.reload(); 
              setPrices({
                outer: { min: '', max: '' },
                top: { min: '', max: '' },
                bottom: { min: '', max: '' },
                shoes: { min: '', max: '' },
                acc: { min: '', max: '' }
              });
            }}>다시하기</button>
          </div>
        </div>
      )}

      {/* [수정] onNavigateToPurchase 추가 */}
      {step === 'collage' && recommendedProducts && (
        <CollagePage 
          result={result} 
          products={recommendedProducts} 
          currentOutfitId={currentOutfitId} 
          onBackToMain={resetAll} 
          onBackToResult={() => setStep('price_setting')} 
          prices={prices}
          onNavigateToPurchase={handleGoToPurchase} 
        />
      )}

      {/* [추가] PurchasePage 렌더링 섹션 */}
      {step === 'purchase' && (
        <PurchasePage 
          selectedItems={finalSelectedItems} 
          onBack={() => setStep('collage')} 
          onBackToMain={resetAll}
          persona={result}
          bgPath={personaBackMap[result] ? `/backgrounds/${personaBackMap[result]}` : null}
        />
      )}
    </div>
  );
}

export default App;