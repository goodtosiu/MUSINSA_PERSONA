import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './CollagePage.css';

const CollagePage = () => {
  const [fullData, setFullData] = useState(null);
  const [displayItems, setDisplayItems] = useState({ outer: [], top: [], bottom: [], shoes: [], acc: [] });
  const [selectedItems, setSelectedItems] = useState([]);
  const [loading, setLoading] = useState(true);

  // 캔버스 내 아이템 이동을 위한 상태
  const [isDragging, setIsDragging] = useState(false);
  const [dragTarget, setDragTarget] = useState(null);
  const [offset, setOffset] = useState({ x: 0, y: 0 });

  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await axios.get('http://localhost:5000/api/products?persona=아메카지');
        setFullData(response.data);
        const initialDisplay = {};
        ['outer', 'top', 'bottom', 'shoes', 'acc'].forEach(cat => {
          initialDisplay[cat] = (response.data[cat] || []).sort(() => 0.5 - Math.random()).slice(0, 5);
        });
        setDisplayItems(initialDisplay);
        setLoading(false);
      } catch (error) {
        console.error("로딩 실패", error);
        setLoading(false);
      }
    };
    fetchData();
  }, []);

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

  // 4. 우클릭 시 즉시 삭제 (confirm 메시지 제거)
  const handleContextMenu = (e, instanceId) => {
    e.preventDefault(); // 브라우저 우클릭 메뉴 차단
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

  if (loading) return <div className="loading-dark">분석 중...</div>;

  return (
    <div className="advanced-collage-layout dark-theme" onMouseUp={handleMouseUp}>
      <section className="left-canvas-area">
        <div className="canvas-header">
          <div className="button-group">
            <button className="btn-secondary" onClick={() => window.location.href="/"}>메인으로</button>
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
              <img 
                src={`http://localhost:5000/api/remove-bg?url=${encodeURIComponent(item.img_url)}&category=${item.category}`} 
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
              <button className="shuffle-btn" onClick={() => {
                const newFive = fullData[cat].sort(() => 0.5 - Math.random()).slice(0, 5);
                setDisplayItems(prev => ({ ...prev, [cat]: newFive }));
              }}>셔플 🔄</button>
            </div>
            <div className="item-grid">
              {displayItems[cat]?.map(item => (
                <div 
                  key={item.product_id} 
                  className="item-card" 
                  draggable 
                  onDragStart={(e) => handleExternalDragStart(e, item, cat)}
                >
                  <div className="img-box">
                    <img src={`http://localhost:5000/api/remove-bg?url=${encodeURIComponent(item.img_url)}&category=${cat}`} alt="" />
                  </div>
                  <div className="item-info">
                    <p className="price-text">{item.price?.toLocaleString()}원</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </section>
    </div>
  );
};

export default CollagePage;