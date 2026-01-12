import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './CollagePage.css';
import { personaBackMap } from './data';

// --- 내부 Sub-Component: PurchaseView (디자인 및 데이터 매칭 수정) ---
const PurchaseView = ({ selectedItems, onBack, bgPath }) => {
  // [수정] 가격 합계 계산 시 데이터 타입 방어 코드 추가
  const totalPrice = selectedItems.reduce((sum, item) => {
    const p = typeof item.price === 'number' ? item.price : parseInt(item.price) || 0;
    return sum + p;
  }, 0);

  return (
    <div className="advanced-collage-layout dark-theme">
      {/* 왼쪽: 기존 캔버스 유지 */}
      <section className="left-canvas-area">
        <div className="canvas-header">
           <span style={{ background: '#333', padding: '4px 12px', borderRadius: '20px', fontSize: '0.7rem', color: '#fff', marginBottom: '10px' }}>마이 아웃핏</span>
        </div>
        <div className="collage-canvas" 
             style={{ backgroundImage: bgPath ? `url(${bgPath})` : 'none', backgroundSize: 'cover', backgroundPosition: 'center', position: 'relative', overflow: 'hidden', border: '1px solid #333' }}>
          {selectedItems.map((item) => (
            <div key={item.instanceId} className="canvas-item"
                 style={{ left: `${item.x}px`, top: `${item.y}px`, transform: `scale(${item.scale})`, position: 'absolute', zIndex: item.zIndex }}>
              <img src={item.img_url} alt="" style={{ width: '150px', userSelect: 'none' }} draggable="false" />
            </div>
          ))}
        </div>
      </section>

      {/* 오른쪽: 상세 내역 (이미지 요청 디자인 & 폰트 스타일링) */}
      <section className="right-list-area" style={{ justifyContent: 'space-between', paddingRight: '20px' }}>
        <div>
          <h2 className="sidebar-title" style={{ textAlign: 'center', marginBottom: '40px', fontFamily: 'inherit' }}>선택 상품</h2>
          <div className="purchase-list" style={{ overflowY: 'auto', maxHeight: '500px' }}>
            {selectedItems.map((item) => (
              <div key={item.instanceId} style={{ display: 'flex', alignItems: 'center', marginBottom: '25px', gap: '20px', borderBottom: '1px solid #1a1a1a', paddingBottom: '15px' }}>
                <div style={{ width: '90px', height: '90px', background: '#fff', borderRadius: '8px', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                  <img src={item.img_url} alt="" style={{ width: '85%', height: '85%', objectFit: 'contain' }} />
                </div>
                <div style={{ color: '#fff', textAlign: 'left' }}>
                  {/* app.py에서 정의된 product_name과 price 사용 */}
                  <p style={{ fontSize: '0.95rem', fontWeight: '600', margin: '0', lineHeight: '1.4' }}>{item.product_name}</p>
                  <p style={{ fontSize: '1rem', color: '#fff', margin: '8px 0 0 0', fontWeight: '700' }}>{item.price?.toLocaleString()}원</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* 로고 영역 */}
        <div style={{ textAlign: 'center', margin: '30px 0', color: '#fff', letterSpacing: '6px', fontSize: '0.85rem', fontWeight: '300', lineHeight: '1.8' }}>
          <p style={{ margin: 0 }}>LOOK</p>
          <p style={{ margin: 0 }}>×</p>
          <p style={{ margin: 0 }}>MBTI</p>
        </div>

        {/* 버튼 섹션 */}
        <div className="action-button-group" style={{ padding: '0', gap: '12px' }}>
          <button className="btn-secondary" 
                  style={{ width: '100%', height: '55px', background: 'transparent', color: '#fff', border: '1px solid #fff', borderRadius: '8px', cursor: 'pointer', fontSize: '1rem' }}
                  onClick={() => alert("사용 가능한 쿠폰이 없습니다.")}>
            쿠폰 사용
          </button>
          <button className="buy-red-btn" 
                  style={{ width: '100%', height: '55px', background: '#fff', color: '#000', fontWeight: '800', fontSize: '1.1rem', border: 'none', borderRadius: '8px' }}
                  onClick={() => alert("결제 페이지로 이동합니다!")}>
            {totalPrice.toLocaleString()}원 결제하기
          </button>
          <button onClick={onBack} style={{ background: 'none', border: 'none', color: '#666', textDecoration: 'underline', marginTop: '10px', cursor: 'pointer', fontSize: '0.85rem' }}>
            수정하러 가기
          </button>
        </div>
      </section>
    </div>
  );
};

// --- 메인 CollagePage 컴포넌트 (변경 없음) ---
const CollagePage = ({ result, products, currentOutfitId, onBackToMain, onBackToResult, prices }) => {
  const [viewMode, setViewMode] = useState('collage');
  const [displayItems, setDisplayItems] = useState({ outer: [], top: [], bottom: [], shoes: [], acc: [] });
  const [selectedItems, setSelectedItems] = useState([]);
  const [isDragging, setIsDragging] = useState(false);
  const [dragTarget, setDragTarget] = useState(null);
  const [offset, setOffset] = useState({ x: 0, y: 0 });
  const [maxZ, setMaxZ] = useState(10); 
  const [shuffleLoading, setShuffleLoading] = useState({});

  useEffect(() => {
    if (products && Array.isArray(products)) {
      const grouped = { outer: [], top: [], bottom: [], shoes: [], acc: [] };
      products.forEach(item => { if (grouped[item.category]) grouped[item.category].push(item); });
      setDisplayItems(grouped);
    } else if (products && typeof products === 'object') {
      setDisplayItems(prev => ({ ...prev, ...products }));
    }
  }, [products]);

  const bgImageName = personaBackMap[result];
  const bgPath = bgImageName ? `/backgrounds/${bgImageName}` : null;

  const handleShuffle = async (category) => {
    try {
      setShuffleLoading(prev => ({ ...prev, [category]: true }));
      const response = await axios.get(`http://127.0.0.1:5000/api/products`, {
        params: {
          persona: result,
          outfit_id: currentOutfitId,
          category: category,
          [`min_${category}`]: prices[category].min,
          [`max_${category}`]: prices[category].max,
          _t: Date.now()
        }
      });
      const newItemsData = response.data.items;
      if (newItemsData && newItemsData[category]) {
        setDisplayItems(prev => ({ ...prev, [category]: newItemsData[category] }));
      }
    } catch (error) {
      console.error("셔플 실패:", error);
    } finally {
      setShuffleLoading(prev => ({ ...prev, [category]: false }));
    }
  };

  const handleExternalDragStart = (e, item, cat) => {
    e.dataTransfer.setData("item", JSON.stringify(item));
    e.dataTransfer.setData("category", cat);
  };

  const handleCanvasDrop = (e) => {
    e.preventDefault();
    const itemDataStr = e.dataTransfer.getData("item");
    if (!itemDataStr) return; 
    const canvasRect = e.currentTarget.getBoundingClientRect();
    const itemData = JSON.parse(itemDataStr); // 여기서 product_name, price가 포함됨
    const cat = e.dataTransfer.getData("category");
    const nextZ = maxZ + 1;
    setMaxZ(nextZ);
    const newItem = {
      ...itemData, 
      instanceId: Date.now(),
      x: e.clientX - canvasRect.left - 60,
      y: e.clientY - canvasRect.top - 60,
      scale: 0.8, 
      category: cat, 
      zIndex: nextZ 
    };
    setSelectedItems(prev => [...prev, newItem]);
  };

  const handleItemMouseDown = (e, instanceId) => {
    e.stopPropagation();
    const target = selectedItems.find(item => item.instanceId === instanceId);
    if (!target) return;
    setIsDragging(true); setDragTarget(instanceId);
    setOffset({ x: e.clientX - target.x, y: e.clientY - target.y });
    const nextZ = maxZ + 1; setMaxZ(nextZ);
    setSelectedItems(prev => prev.map(item => item.instanceId === instanceId ? { ...item, zIndex: nextZ } : item));
  };

  const handleCanvasMouseMove = (e) => {
    if (!isDragging || dragTarget === null) return;
    setSelectedItems(prev => prev.map(item => item.instanceId === dragTarget ? { ...item, x: e.clientX - offset.x, y: e.clientY - offset.y } : item));
  };

  if (viewMode === 'purchase') {
    return <PurchaseView selectedItems={selectedItems} onBack={() => setViewMode('collage')} bgPath={bgPath} />;
  }

  return (
    <div className="advanced-collage-layout dark-theme" onMouseUp={() => setIsDragging(false)}>
      <section className="left-canvas-area">
        <div className="canvas-header">
          <p className="instruction">드래그: 배치 / 휠: 크기 조절 / 우클릭: 삭제</p>
        </div>
        <div className="collage-canvas" onDragOver={(e) => e.preventDefault()} onDrop={handleCanvasDrop} onMouseMove={handleCanvasMouseMove} onMouseLeave={() => setIsDragging(false)}
          style={{ backgroundImage: bgPath ? `url(${bgPath})` : 'none', backgroundSize: 'cover', backgroundPosition: 'center', position: 'relative', overflow: 'hidden', border: '1px solid #333' }}>
          {selectedItems.map((item) => (
            <div key={item.instanceId} className="canvas-item" onMouseDown={(e) => handleItemMouseDown(e, item.instanceId)}
              onWheel={(e) => {
                e.preventDefault();
                const delta = e.deltaY > 0 ? -0.1 : 0.1;
                setSelectedItems(prev => prev.map(it => it.instanceId === item.instanceId ? { ...it, scale: Math.min(Math.max(it.scale + delta, 0.2), 3) } : it));
              }}
              onContextMenu={(e) => { e.preventDefault(); setSelectedItems(prev => prev.filter(it => it.instanceId !== item.instanceId)); }} 
              style={{ left: `${item.x}px`, top: `${item.y}px`, transform: `scale(${item.scale})`, position: 'absolute', zIndex: item.zIndex, cursor: 'move' }}>
              <img src={item.img_url} alt="" draggable="false" style={{ userSelect: 'none', width: '150px' }} />
            </div>
          ))}
        </div>
      </section>

      <section className="right-list-area">
        <h2 className="sidebar-title">{result} 스타일 추천</h2>
        {['outer', 'top', 'bottom', 'shoes', 'acc'].map(cat => (
          <div key={cat} className="cat-section">
            <div className="cat-header">
              <span className="cat-name">{cat.toUpperCase()}</span>
              {(!shuffleLoading[cat] && displayItems[cat]?.length > 0) && (
                <button className="shuffle-btn" onClick={() => handleShuffle(cat)}>셔플</button>
              )}
            </div>
            <div className="item-grid">
              {(() => {
                const items = displayItems[cat] || [];
                const totalSlots = Array.from({ length: 5 });
                return totalSlots.map((_, i) => {
                  const item = items[i];
                  if (item) {
                    return (
                      <div key={item.product_id} className={`item-card ${shuffleLoading[cat] ? 'shuffling' : ''}`} draggable onDragStart={(e) => handleExternalDragStart(e, item, cat)}>
                        <div className="img-box"><img src={item.img_url} alt="" onError={(e) => e.target.src = 'https://via.placeholder.com/150'} /></div>
                        <div className="item-info"><p className="price-text">{item.price?.toLocaleString()}원</p></div>
                      </div>
                    );
                  } else {
                    return (
                      <div key={`empty-${cat}-${i}`} className="item-card empty-slot">
                        <div className="img-box" /><div className="item-info"><p className="price-text">해당 상품 없음</p></div>
                      </div>
                    );
                  }
                });
              })()}
            </div>
          </div>
        ))}
        <div className="action-button-group">
          <div className="button-group">
            <button className="btn-secondary" onClick={onBackToMain}>메인으로</button>
            <button className="btn-secondary" onClick={() => setSelectedItems([])}>초기화</button>
            <button className="btn-secondary" onClick={onBackToResult}>이전으로</button>
          </div>
          <button className="buy-red-btn" onClick={() => {
            if (selectedItems.length === 0) alert("선택된 상품이 없습니다!");
            else setViewMode('purchase');
          }}>선택 조합 구매하기</button>
        </div>
      </section>
    </div>
  );
};

export default CollagePage;