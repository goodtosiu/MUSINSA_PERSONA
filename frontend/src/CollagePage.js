import React, { useState } from 'react';
import './App.css';

function CollagePage({ result, products, onBackToMain }) {
  const [placedItems, setPlacedItems] = useState([]);
  const FLASK_URL = "http://localhost:5000";

  // 휠로 사이즈 조절
  const handleWheel = (e, id) => {
    e.preventDefault();
    const scaleAmount = e.deltaY > 0 ? -0.1 : 0.1;
    setPlacedItems(prev => prev.map(item => 
      item.id === id ? { ...item, scale: Math.max(0.2, item.scale + scaleAmount) } : item
    ));
  };

  const onDragStart = (e, imgUrl, moveId = null) => {
    e.dataTransfer.setData("imgUrl", imgUrl);
    if (moveId) e.dataTransfer.setData("moveId", moveId);
    
    const img = new Image();
    img.src = 'data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7'; 
    e.dataTransfer.setDragImage(img, 0, 0);
  };

  const onDrop = (e) => {
    e.preventDefault();
    const imgUrl = e.dataTransfer.getData("imgUrl");
    const moveId = e.dataTransfer.getData("moveId");
    const rect = e.currentTarget.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    if (moveId) {
      setPlacedItems(prev => prev.map(item => 
        item.id === parseInt(moveId) ? { ...item, x, y } : item
      ));
    } else {
      setPlacedItems(prev => [...prev, { id: Date.now(), url: imgUrl, x, y, scale: 1 }]);
    }
  };

return (
    <div className="collage-container">
      {/* 캔버스 영역: CSS에서 설정한 클래스 적용 */}
      <div 
        className="canvas-area" 
        onDragOver={(e) => e.preventDefault()} 
        onDrop={onDrop}
      >
        <div className="canvas-hint">
          {placedItems.length === 0 && (
            <>
              이미지를 드래그하여 코디해보세요<br/>
              (휠: 크기조절, 우클릭: 삭제)
            </>
          )}
        </div>
        {placedItems.map((item) => (
          <img
            key={item.id}
            src={`${FLASK_URL}/api/remove-bg?url=${encodeURIComponent(item.url)}`}
            alt="placed"
            className="placed-img"
            style={{ 
              left: `${item.x}px`, 
              top: `${item.y}px`,
              transform: `translate(-50%, -50%) scale(${item.scale})`,
              cursor: 'move',
              position: 'absolute'
            }}
            draggable
            onDragStart={(e) => onDragStart(e, item.url, item.id)}
            onWheel={(e) => handleWheel(e, item.id)}
            onContextMenu={(e) => {
              e.preventDefault();
              setPlacedItems(prev => prev.filter(i => i.id !== item.id));
            }}
          />
        ))}
      </div>

      {/* 사이드바 영역: 기존 로직 그대로 유지 */}
      <div className="product-sidebar">
<h3 className="sidebar-title">{result} 스타일 추천</h3>
        
        <div className="category-scroll-area">
          {["상의", "바지", "아우터", "신발"].map((category) => (
            <div key={category} className="category-section">
              <h4 className="category-name">{category}</h4>
              <div className="img-grid">
                {/* [기준 상품] */}
                {products.targets && products.targets[category] && (
                  <div className="img-wrapper target-highlight">
                    <img
                      src={`${FLASK_URL}/api/remove-bg?url=${encodeURIComponent(products.targets[category])}`}
                      alt="target"
                      className="draggable-img"
                      draggable
                      onDragStart={(e) => onDragStart(e, products.targets[category])}
                    />
                    <div className="target-badge">기준</div>
                  </div>
                )}

                {/* [추천 상품들] */}
                {products[category]?.map((url, idx) => (
                  <div key={idx} className="img-wrapper">
                    <img
                      src={`${FLASK_URL}/api/remove-bg?url=${encodeURIComponent(url)}`}
                      alt="recommend"
                      className="draggable-img"
                      draggable
                      onDragStart={(e) => onDragStart(e, url)}
                      style={{ backgroundColor: 'transparent' }}
                    />
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>

        {/* 하단 버튼 영역 */}
        <div className="sidebar-action-group">
          <button className="checkout-btn" onClick={() => alert("준비 중인 기능입니다.")}>
            선택한 조합으로 구매하기
          </button>
          <div className="sub-btn-row">
            <button className="action-btn" onClick={() => setPlacedItems([])}>캔버스 초기화</button>
            <button className="action-btn" onClick={onBackToMain}>메인으로</button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default CollagePage;