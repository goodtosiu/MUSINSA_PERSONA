import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './CollagePage.css';

const CollagePage = ({ result, products, currentOutfitId, onBackToMain, onBackToResult }) => {
  const [displayItems, setDisplayItems] = useState(products);
  const [selectedItems, setSelectedItems] = useState([]);

  // 드래그 관련 상태
  const [isDragging, setIsDragging] = useState(false);
  const [dragTarget, setDragTarget] = useState(null);
  const [offset, setOffset] = useState({ x: 0, y: 0 });

  // 레이어(Z-Index)
  const [maxZ, setMaxZ] = useState(10); 
  
  // 버튼 호버 상태
  const [hoveredBtn, setHoveredBtn] = useState(null);

  // [NEW] 셔플 로딩 상태 관리 (카테고리별로 로딩 중인지 체크)
  const [shuffleLoading, setShuffleLoading] = useState({
    outer: false, top: false, bottom: false, shoes: false, acc: false
  });

  useEffect(() => {
    if (products) {
      setDisplayItems(products);
    }
  }, [products]);

  // 셔플 핸들러
  const handleShuffle = async (category) => {
    try {
      // 1. 로딩 상태 시작 (해당 카테고리만 true)
      setShuffleLoading(prev => ({ ...prev, [category]: true }));

      // 2. 서버 요청 (해당 카테고리만 누끼 따오라고 요청)
      const response = await axios.get(`http://127.0.0.1:5000/api/products`, {
        params: {
          persona: result,
          outfit_id: currentOutfitId,
          category: category, 
          _t: Date.now()
        }
      });

      const newItemsData = response.data.items;
      
      // 3. 데이터 업데이트
      if (newItemsData && newItemsData[category]) {
        setDisplayItems(prev => ({
          ...prev, 
          [category]: newItemsData[category]
        }));
      }
    } catch (error) {
      console.error("셔플 실패:", error);
      alert("데이터를 불러오지 못했습니다.");
    } finally {
      // 4. 로딩 종료
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
      item.instanceId === instanceId 
      ? { ...item, zIndex: nextZ } 
      : item
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

  const CAT_KO = { outer: "아우터", top: "상의", bottom: "바지", shoes: "신발", acc: "액세서리" };

  return (
    <div className="advanced-collage-layout dark-theme" onMouseUp={handleMouseUp}>
      {/* 왼쪽: 캔버스 영역 (상단 버튼과 하단 구매 버튼 삭제) */}
      <section className="left-canvas-area">
        <div className="canvas-header">
          {/* 가이드 문구만 남겨둠 */}
          <p className="instruction"> 드래그: 배치 / 휠: 크기 조절 / 우클릭: 삭제</p>
        </div>

        <div 
          className="collage-canvas white-bg" 
          onDragOver={(e) => e.preventDefault()} 
          onDrop={handleCanvasDrop}
          onMouseMove={handleCanvasMouseMove}
          onMouseLeave={handleMouseUp}
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
              <img src={item.img_url} alt="" draggable="false" style={{ userSelect: 'none' }} />
            </div>
          ))}
        </div>
      </section>

      {/* 오른쪽: 리스트 영역 (하단에 버튼들 추가) */}
      <section className="right-list-area">
        <h2 className="sidebar-title">STYLE PIECES</h2>
        {['outer', 'top', 'bottom', 'shoes', 'acc'].map(cat => (
          <div key={cat} className="cat-section">
            <div className="cat-header">
              <span className="cat-name">{cat.toUpperCase()}</span>
              {/* 버튼 표시 조건: 로딩 중이 아니고 & 데이터가 있을 때 */}
              {(!shuffleLoading[cat] && displayItems && displayItems[cat]?.length > 0) && (
                <button 
                  className="shuffle-btn"
                  onMouseEnter={() => setHoveredBtn(cat)}
                  onMouseLeave={() => setHoveredBtn(null)}
                  onClick={() => handleShuffle(cat)}
                  style={{
                    cursor: 'pointer',
                    backgroundColor: hoveredBtn === cat ? '#ff4d4d' : '#333', 
                    color: 'white',
                    border: '1px solid #555',
                    padding: '5px 10px',
                    borderRadius: '5px',
                    transition: 'background-color 0.2s'
                  }}
                >
                  셔플
                </button>
              )}
            </div>

            <div className="item-grid">
              {/* [렌더링 로직 분기] */}
              
              {/* Case 1: 로딩 중이면? -> 빈 화면 (기존 상품 지움) */}
              {shuffleLoading[cat] ? (
                <div className="empty-msg-box" style={{ minHeight: '150px' }}>
                  {/* 필요시 <p>새로운 스타일을 찾는 중...</p> */}
                </div>
              ) : (
                // Case 2: 로딩 끝났는데 데이터가 있으면? -> 상품 리스트 출력
                (displayItems && displayItems[cat] && displayItems[cat].length > 0) ? (
                  displayItems[cat].map(item => (
                    <div 
                      key={item.product_id} 
                      className="item-card" 
                      draggable 
                      onDragStart={(e) => handleExternalDragStart(e, item, cat)}
                    >
                      <div className="img-box">
                        <img src={item.img_url} alt={item.product_name} />
                      </div>
                      <div className="item-info">
                        <p className="price-text">{item.price?.toLocaleString()}원</p>
                      </div>
                    </div>
                  ))
                ) : (
                  // Case 3: 로딩 끝났는데 데이터가 0개면? -> "추천 안 함" 메시지
                  <div className="empty-msg-box" style={{ padding: '30px', color: '#888', textAlign: 'center', fontSize: '0.9rem' }}>
                    <p>🚫 해당 조합에서는<br/>추천되지 않는 항목입니다.</p>
                  </div>
                )
              )}
            </div>
          </div>
        ))}

        {/* --- 여기서부터 이동된 버튼들 --- */}
        <hr style={{ border: '0.5px solid #333', margin: '40px 0 20px 0' }} />
        
        <div className="action-button-group" style={{ display: 'flex', flexDirection: 'column', gap: '10px', padding: '0 20px 40px 20px' }}>
          {/* 상단에 있던 내비게이션 버튼들 */}
          <div className="button-group" style={{ display: 'flex', justifyContent: 'space-between', gap: '10px' }}>
            <button className="btn-secondary" onClick={onBackToMain} style={{ flex: 1 }}>메인으로</button>
            <button className="btn-secondary" onClick={() => setSelectedItems([])} style={{ flex: 1 }}>캔버스 초기화</button>
            <button className="btn-secondary" onClick={onBackToResult} style={{ flex: 1 }}>이전으로</button>
          </div>

          {/* 구매 버튼 */}
          <button 
            className="buy-red-btn" 
            onClick={() => alert("구매 페이지로 이동!")}
            style={{ width: '100%', marginTop: '10px' }}
          >
            선택 조합 구매하기
          </button>
        </div>
      </section>
    </div>
  );
};

export default CollagePage;