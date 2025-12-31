import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './CollagePage.css';

// [수정] App.js에서 전달받은 props 사용
const CollagePage = ({ result, products, currentOutfitId, onBackToMain }) => {
  // 초기 상태를 props로 받은 products로 설정
  const [displayItems, setDisplayItems] = useState(products);
  const [selectedItems, setSelectedItems] = useState([]);

  // 캔버스 내 아이템 이동을 위한 상태
  const [isDragging, setIsDragging] = useState(false);
  const [dragTarget, setDragTarget] = useState(null);
  const [offset, setOffset] = useState({ x: 0, y: 0 });

  // props인 products가 바뀔 경우 state 동기화 (선택 사항)
  useEffect(() => {
    if (products) {
      setDisplayItems(products);
    }
  }, [products]);

  // [수정] 셔플 핸들러: 서버에 outfit_id를 유지한 채 재요청
  const handleShuffle = async (category) => {
    try {
      // 서버 요청: outfit_id를 함께 보내서 "같은 스타일 내에서 다른 옷"을 가져옴
      const response = await axios.get(`http://127.0.0.1:5000/api/products`, {
        params: {
          persona: result,
          outfit_id: currentOutfitId
        }
      });

      const newItemsData = response.data.items;
      
      // 해당 카테고리만 업데이트 (전체를 다 바꾸고 싶으면 setDisplayItems(newItemsData) 하면 됨)
      if (newItemsData && newItemsData[category]) {
        setDisplayItems(prev => ({
          ...prev,
          [category]: newItemsData[category]
        }));
      }
    } catch (error) {
      console.error("셔플 실패:", error);
      alert("새로운 추천을 불러오지 못했습니다.");
    }
  };

  // 1. 외부 리스트에서 캔버스로 드래그 시작
  const handleExternalDragStart = (e, item, cat) => {
    e.dataTransfer.setData("item", JSON.stringify(item));
    e.dataTransfer.setData("category", cat);
  };

  // 2. 캔버스에 새로운 아이템 드롭
  const handleCanvasDrop = (e) => {
    e.preventDefault();
    const itemDataStr = e.dataTransfer.getData("item");
    if (!itemDataStr) return; 

    const canvasRect = e.currentTarget.getBoundingClientRect();
    const itemData = JSON.parse(itemDataStr);
    const cat = e.dataTransfer.getData("category");

    const newItem = {
      ...itemData,
      instanceId: Date.now(),
      x: e.clientX - canvasRect.left - 60,
      y: e.clientY - canvasRect.top - 60,
      scale: 0.8,
      category: cat
      // img_url은 itemData 안에 이미 들어있음 (서버에서 받은 URL)
    };
    setSelectedItems(prev => [...prev, newItem]);
  };

  // 3. 캔버스 내 아이템 이동 로직
  const handleItemMouseDown = (e, instanceId) => {
    e.stopPropagation();
    const target = selectedItems.find(item => item.instanceId === instanceId);
    if (!target) return;

    setIsDragging(true);
    setDragTarget(instanceId);
    setOffset({
      x: e.clientX - target.x,
      y: e.clientY - target.y
    });
  };

  const handleCanvasMouseMove = (e) => {
    if (!isDragging || dragTarget === null) return;

    const canvasRect = e.currentTarget.getBoundingClientRect();
    const newX = e.clientX - offset.x;
    const newY = e.clientY - offset.y;

    setSelectedItems(prev => prev.map(item => 
      item.instanceId === dragTarget 
      ? { ...item, x: newX, y: newY } 
      : item
    ));
  };

  const handleMouseUp = () => {
    setIsDragging(false);
    setDragTarget(null);
  };

  // 4. 우클릭 시 즉시 삭제
  const handleContextMenu = (e, instanceId) => {
    e.preventDefault();
    setSelectedItems(prev => prev.filter(item => item.instanceId !== instanceId));
  };

  // 5. 휠로 크기 조절
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
          <div className="button-group">
            {/* [수정] App.js에서 받은 함수 사용 */}
            <button className="btn-secondary" onClick={onBackToMain}>메인으로</button>
            <button className="btn-secondary" onClick={() => setSelectedItems([])}>캔버스 초기화</button>
          </div>
          <p className="instruction">💡 드래그하여 배치 / 휠로 크기 조절 / 우클릭 즉시 삭제</p>
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
                zIndex: dragTarget === item.instanceId ? 100 : 1,
                cursor: 'move'
              }}
            >
              {/* [수정] item.img_url 그대로 사용 (서버가 처리된 URL 줌) */}
              <img 
                src={item.img_url} 
                alt="" 
                draggable="false" 
                style={{ userSelect: 'none' }}
              />
            </div>
          ))}
        </div>
        
        <button className="buy-red-btn" onClick={() => alert("구매 페이지로 이동!")}>선택 조합 구매하기</button>
      </section>

      <section className="right-list-area">
        <h2 className="sidebar-title">STYLE PIECES</h2>
        {['outer', 'top', 'bottom', 'shoes', 'acc'].map(cat => (
          <div key={cat} className="cat-section">
            <div className="cat-header">
              <span className="cat-name">{cat.toUpperCase()}</span>
              {/* [수정] 셔플 버튼 클릭 시 서버 요청 */}
              <button className="shuffle-btn" onClick={() => handleShuffle(cat)}>셔플 🔄</button>
            </div>
            <div className="item-grid">
              {/* displayItems가 없거나 비어있을 경우 대비 */}
              {displayItems && displayItems[cat] ? (
                displayItems[cat].map(item => (
                  <div 
                    key={item.product_id} 
                    className="item-card" 
                    draggable 
                    onDragStart={(e) => handleExternalDragStart(e, item, cat)}
                  >
                    <div className="img-box">
                      {/* [수정] item.img_url 사용 */}
                      <img src={item.img_url} alt={item.product_name} />
                    </div>
                    <div className="item-info">
                      <p className="price-text">{item.price?.toLocaleString()}원</p>
                    </div>
                  </div>
                ))
              ) : (
                <div className="empty-msg">아이템이 없습니다.</div>
              )}
            </div>
          </div>
        ))}
      </section>
    </div>
  );
};

export default CollagePage;