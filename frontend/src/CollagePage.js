import React, { useState, useRef } from 'react';
import './App.css';

function CollagePage({ result, products, onBackToMain }) {
  const [placedItems, setPlacedItems] = useState([]);
  const FLASK_URL = "http://localhost:5000";
  const scrollRef = useRef({}); // 슬라이더 제어를 위한 ref 추가

  // 휠로 사이즈 조절
  const handleWheel = (e, id) => {
    e.preventDefault();
    const scaleAmount = e.deltaY > 0 ? -0.1 : 0.1;
    setPlacedItems(prev => prev.map(item =>
      item.id === id ? { ...item, scale: Math.max(0.2, item.scale + scaleAmount) } : item
    ));
  };

  // 드래그 시작 핸들러
  const onDragStart = (e, imgUrl, moveId = null) => {
    e.dataTransfer.setData("imgUrl", imgUrl);
    if (moveId) e.dataTransfer.setData("moveId", moveId);
    const img = new Image();
    img.src = 'data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7';
    e.dataTransfer.setDragImage(img, 0, 0);
  };

  // 드롭 핸들러
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

  // 슬라이더 스크롤 함수
  const handleScroll = (category, direction) => {
    const container = scrollRef.current[category];
    if (container) {
      const scrollAmount = 200;
      container.scrollLeft += direction === 'left' ? -scrollAmount : scrollAmount;
    }
  };

  return (
    <div className="collage-container">
      <div className="canvas-wrapper">
        {/* 1. 힌트를 캔버스 밖(위)으로 추출 */}
        {placedItems.length === 0 && (
        <div className="canvas-hint">
          이미지를 드래그하여 코디해보세요<br/>
          (휠: 크기조절, 우클릭: 삭제)
        </div>
        )}

        {/* 2. 실제 캔버스 영역 */}
        <div
          className="canvas-area"
          onDragOver={(e) => e.preventDefault()}
          onDrop={onDrop}
        >
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
      </div>

      {/* 사이드바 영역: 이미지와 동일한 레이아웃으로 수정 */}
      <div className="product-sidebar">
        <div className="category-scroll-area">
          {[
            { ko: "악세서리", en: "ACC" },
            { ko: "아우터", en: "OUTER" },
            { ko: "상의", en: "TOP" },
            { ko: "하의", en: "BOTTOM" },
            { ko: "신발", en: "SHOES" }
          ].map((cat) => (
            <div key={cat.en} className="category-section">
              <h4 className="category-name">{cat.en}</h4>
              <div className="slider-container">
                <button className="nav-btn prev" onClick={() => handleScroll(cat.en, 'left')}>‹</button>
                <div
                  className="img-horizontal-scroll"
                  ref={(el) => (scrollRef.current[cat.en] = el)}
                >
                  {/* [기준 상품] */}
                  {products.targets && products.targets[cat.ko] && (
                    <div className="img-wrapper target-highlight">
                      <img
                        src={`${FLASK_URL}/api/remove-bg?url=${encodeURIComponent(products.targets[cat.ko])}`}
                        alt="target"
                        className="draggable-img"
                        draggable
                        onDragStart={(e) => onDragStart(e, products.targets[cat.ko])}
                      />
                    </div>
                  )}

                  {/* [추천 상품들] */}
                  {products[cat.ko]?.map((url, idx) => (
                    <div key={idx} className="img-wrapper">
                      <img
                        src={`${FLASK_URL}/api/remove-bg?url=${encodeURIComponent(url)}`}
                        alt="recommend"
                        className="draggable-img"
                        draggable
                        onDragStart={(e) => onDragStart(e, url)}
                      />
                    </div>
                  ))}
                </div>
                <button className="nav-btn next" onClick={() => handleScroll(cat.en, 'right')}>›</button>
              </div>
            </div>
          ))}
        </div>

        {/* 하단 버튼 영역: 이미지 디자인에 맞춰 수정 */}
        <div className="sidebar-action-group">
          <button className="decision-btn" onClick={() => alert("스타일이 저장되었습니다!")}>
            아웃핏 결정하기
          </button>
          <div className="sub-btn-row">
            <button className="secondary-action-btn" onClick={() => setPlacedItems([])}>
              캔버스 초기화
            </button>
            <span className="divider">|</span>
            <button className="secondary-action-btn" onClick={onBackToMain}>
              메인으로
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default CollagePage;