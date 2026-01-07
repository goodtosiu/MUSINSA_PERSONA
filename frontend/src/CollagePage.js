import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './CollagePage.css';
import { personaBackMap } from './data'; 

const CollagePage = ({ result, products, currentOutfitId, onBackToMain, onBackToResult }) => {
  // [수정] 초기 데이터가 리스트로 올 경우를 대비해 분류 로직 추가
  const [displayItems, setDisplayItems] = useState({
    outer: [], top: [], bottom: [], shoes: [], acc: []
  });
  const [selectedItems, setSelectedItems] = useState([]);
  const [isDragging, setIsDragging] = useState(false);
  const [dragTarget, setDragTarget] = useState(null);
  const [offset, setOffset] = useState({ x: 0, y: 0 });
  const [maxZ, setMaxZ] = useState(10); 
  const [shuffleLoading, setShuffleLoading] = useState({
    outer: false, top: false, bottom: false, shoes: false, acc: false
  });

  // [중요 수정] 백엔드에서 온 리스트 형태의 products를 카테고리별 객체로 변환
  useEffect(() => {
    if (products && Array.isArray(products)) {
      const grouped = { outer: [], top: [], bottom: [], shoes: [], acc: [] };
      products.forEach(item => {
        if (grouped[item.category]) {
          grouped[item.category].push(item);
        }
      });
      setDisplayItems(grouped);
    } else if (products && typeof products === 'object') {
      // 이미 객체 형태라면 그대로 설정
      setDisplayItems(prev => ({ ...prev, ...products }));
    }
  }, [products]);

  const bgImageName = personaBackMap[result];
  const bgPath = bgImageName ? `/backgrounds/${bgImageName}` : null;

  // 셔플 핸들러 수정
  const handleShuffle = async (category) => {
    try {
      setShuffleLoading(prev => ({ ...prev, [category]: true }));
      // app.py의 /api/recommend 엔드포인트를 POST로 호출 (일관성 유지)
      const response = await axios.post(`http://127.0.0.1:5000/api/recommend`, {
        persona: result,
        prices: {} // 필요 시 여기에 현재 가격대 전달 가능
      });

      const newItems = response.data.items;
      if (newItems && Array.isArray(newItems)) {
        // 셔플된 결과 중 해당 카테고리만 업데이트
        const filtered = newItems.filter(it => it.category === category);
        setDisplayItems(prev => ({
          ...prev, 
          [category]: filtered.length > 0 ? filtered : prev[category]
        }));
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
    setIsDragging(true);
    setDragTarget(instanceId);
    setOffset({ x: e.clientX - target.x, y: e.clientY - target.y });
    const nextZ = maxZ + 1;
    setMaxZ(nextZ);
    setSelectedItems(prev => prev.map(item => 
      item.instanceId === instanceId ? { ...item, zIndex: nextZ } : item
    ));
  };

  const handleCanvasMouseMove = (e) => {
    if (!isDragging || dragTarget === null) return;
    const newX = e.clientX - offset.x;
    const newY = e.clientY - offset.y;
    setSelectedItems(prev => prev.map(item => 
      item.instanceId === dragTarget ? { ...item, x: newX, y: newY } : item
    ));
  };

  const handleMouseUp = () => {
    setIsDragging(false);
    setDragTarget(null);
  };

  const handleContextMenu = (e, instanceId) => {
    e.preventDefault();
    setSelectedItems(prev => prev.filter(item => item.instanceId !== instanceId));
  };

  const handleWheel = (e, instanceId) => {
    e.preventDefault();
    const delta = e.deltaY > 0 ? -0.1 : 0.1;
    setSelectedItems(prev => prev.map(item => 
      item.instanceId === instanceId 
      ? { ...item, scale: Math.min(Math.max(item.scale + delta, 0.2), 3) } 
      : item
    ));
  };

  return (
    <div className="advanced-collage-layout dark-theme" onMouseUp={handleMouseUp}>
      <section className="left-canvas-area">
        <div className="canvas-header">
          <p className="instruction">드래그: 배치 / 휠: 크기 조절 / 우클릭: 삭제</p>
        </div>
        <div 
          className="collage-canvas" 
          onDragOver={(e) => e.preventDefault()} 
          onDrop={handleCanvasDrop}
          onMouseMove={handleCanvasMouseMove}
          onMouseLeave={handleMouseUp}
          style={{
            backgroundImage: bgPath ? `url(${bgPath})` : 'none',
            backgroundSize: 'cover',
            backgroundPosition: 'center',
            backgroundColor: bgPath ? 'transparent' : '#111',
            position: 'relative',
            overflow: 'hidden',
            border: '1px solid #333'
          }}
        >
          {selectedItems.map((item) => (
            <div
              key={item.instanceId}
              className="canvas-item"
              onMouseDown={(e) => handleItemMouseDown(e, item.instanceId)}
              onWheel={(e) => handleWheel(e, item.instanceId)}
              onContextMenu={(e) => handleContextMenu(e, item.instanceId)} 
              style={{
                left: `${item.x}px`,
                top: `${item.y}px`,
                transform: `scale(${item.scale})`,
                position: 'absolute',
                zIndex: item.zIndex, 
                cursor: 'move'
              }}
            >
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
              {shuffleLoading[cat] ? (
                Array.from({ length: 4 }).map((_, i) => (
                  <div key={i} className="item-card skeleton" />
                ))
              ) : (
                displayItems[cat] && displayItems[cat].length > 0 ? (
                  displayItems[cat].map(item => (
                    <div 
                      key={item.product_id} 
                      className="item-card" 
                      draggable 
                      onDragStart={(e) => handleExternalDragStart(e, item, cat)}
                    >
                      <div className="img-box">
                        <img src={item.img_url} alt={item.product_name} onError={(e) => e.target.src = 'https://via.placeholder.com/150'} />
                      </div>
                      <div className="item-info">
                        <p className="price-text">{item.price?.toLocaleString()}원</p>
                      </div>
                    </div>
                  ))
                ) : (
                  <p className="empty-text">상품 정보가 없습니다.</p>
                )
              )}
            </div>
          </div>
        ))}
        <div className="action-button-group">
          <div className="button-group">
            <button className="btn-secondary" onClick={onBackToMain}>메인으로</button>
            <button className="btn-secondary" onClick={() => setSelectedItems([])}>초기화</button>
            <button className="btn-secondary" onClick={onBackToResult}>이전으로</button>
          </div>
          <button className="buy-red-btn" onClick={() => alert(`${result} 스타일 구매 페이지로 이동합니다!`)}>
            선택 조합 구매하기
          </button>
        </div>
      </section>
    </div>
  );
};

export default CollagePage;