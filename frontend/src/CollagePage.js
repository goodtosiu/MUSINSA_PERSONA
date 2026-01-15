import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './CollagePage.css';
import { personaBackMap } from './data'; 

// [수정] props에 onNavigateToPurchase 추가
const CollagePage = ({ result, products, currentOutfitId, onBackToMain, onBackToResult, prices, onNavigateToPurchase }) => {
  const [displayItems, setDisplayItems] = useState({
    outer: [], top: [], bottom: [], shoes: [], acc: []
  });
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
    const itemData = JSON.parse(itemDataStr);
    const cat = e.dataTransfer.getData("category");
    const nextZ = maxZ + 1;
    setMaxZ(nextZ);
    const newItem = {
      ...itemData, instanceId: Date.now(),
      x: e.clientX - canvasRect.left - 60,
      y: e.clientY - canvasRect.top - 60,
      scale: 0.8, category: cat, zIndex: nextZ 
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
                      // 1. 전체 카드(.item-card)의 draggable 속성을 제거합니다.
                      <div key={item.product_id} className={`item-card ${shuffleLoading[cat] ? 'shuffling' : ''}`}>
                        <div className="img-box">
                          <img 
                            src={item.img_url} 
                            alt="" 
                            // 2. 이미지 태그에만 드래그 속성과 이벤트를 부여합니다.
                            draggable 
                            onDragStart={(e) => handleExternalDragStart(e, item, cat)}
                            onError={(e) => e.target.src = 'https://via.placeholder.com/150'} 
                            style={{ cursor: 'grab' }} // 드래그 가능함을 시각적으로 표시
                          />
                        </div>
                        <div className="item-info">
                          <p className="price-text">{item.price?.toLocaleString()}원</p>
                        </div>
                      </div>
                    );
                  } else {
                    return (
                      <div key={`empty-${cat}-${i}`} className="item-card empty-slot">
                        <div className="img-box" />
                        <div className="item-info">
                          <p className="price-text">해당 상품 없음</p>
                          </div>
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
          {/* [수정] alert 제거 및 상위 컴포넌트로 데이터 전달 */}
          <button 
            className="buy-red-btn" 
            onClick={() => onNavigateToPurchase(selectedItems)}
          >
            선택 조합 구매하기
          </button>
        </div>
      </section>
    </div>
  );
};

export default CollagePage;