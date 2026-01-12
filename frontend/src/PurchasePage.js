import React from 'react';
import './PurchasePage.css';

const PurchasePage = ({ selectedItems, onBack, bgPath, onBackToMain }) => {
  // 전체 합계 금액 계산
  const totalPrice = selectedItems.reduce((sum, item) => {
    const p = typeof item.price === 'number' ? item.price : parseInt(item.price) || 0;
    return sum + p;
  }, 0);

  return (
    <div className="advanced-collage-layout dark-theme">
      {/* 왼쪽 영역: 캔버스 상태 유지 */}
      <section className="left-canvas-area">
        <div className="canvas-header">
           <span className="badge">마이 아웃핏</span>
        </div>
        <div className="collage-canvas" 
             style={{ backgroundImage: bgPath ? `url(${bgPath})` : 'none' }}>
          {selectedItems.map((item) => (
            <div key={item.instanceId} className="canvas-item"
                 style={{ 
                   left: `${item.x}px`, 
                   top: `${item.y}px`, 
                   transform: `scale(${item.scale})`,
                   zIndex: item.zIndex 
                 }}>
              <img src={item.img_url} alt="" draggable="false" />
            </div>
          ))}
        </div>
      </section>

      {/* 오른쪽 영역: 순수 클래스 기반 구조 (인라인 스타일 제거) */}
      <section className="right-list-area">
        <div className="purchase-container">
          <h2 className="sidebar-title">선택 상품</h2>
          <div className="purchase-list">
            {selectedItems.map((item) => (
              <div key={item.instanceId} className="purchase-item-row">
                <div className="item-thumb">
                  <img src={item.img_url} alt={item.product_name} />
                </div>
                <div className="item-details">
                  <p className="product-name">{item.product_name}</p>
                  <p className="product-price">{item.price?.toLocaleString()}원</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* 로고 영역 */}
        <div className="center-logo-group">
          <p>LOOK</p>
          <p>×</p>
          <p>MBTI</p>
        </div>
      </section>
    </div>
  );
};

export default PurchasePage;