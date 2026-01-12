import React from 'react';
import './PurchasePage.css';

const PurchasePage = ({ selectedItems, onBack, bgPath, onBackToMain }) => {
  // 가격 합산
  const totalPrice = selectedItems.reduce((sum, item) => {
    const p = typeof item.price === 'number' ? item.price : parseInt(item.price) || 0;
    return sum + p;
  }, 0);

  return (
    <div className="advanced-collage-layout dark-theme">
      {/* 왼쪽: 캔버스 (CollagePage.css 스타일 적용됨) */}
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

      {/* 오른쪽: 결제 및 상품 리스트 영역 (PurchasePage.css 적용) */}
      <section className="right-list-area">
        <div className="purchase-content-top">
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

        {/* 로고 및 버튼 영역 */}
        <div className="purchase-content-bottom">
          <div className="center-logo-group">
            <p>LOOK</p>
            <p>×</p>
            <p>MBTI</p>
          </div>

          <div className="action-button-group">
            <div className="button-group">
              <button className="btn-secondary" onClick={onBackToMain}>메인으로</button>
              <button className="btn-secondary" onClick={() => alert("사용 가능한 쿠폰이 없습니다.")}>쿠폰 사용</button>
              <button className="btn-secondary" onClick={onBack}>이전으로</button>
            </div>
            <button className="buy-red-btn" onClick={() => alert("결제 페이지로 이동합니다.")}>
              {totalPrice.toLocaleString()}원 결제하기
            </button>
          </div>
        </div>
      </section>
    </div>
  );
};

export default PurchasePage;